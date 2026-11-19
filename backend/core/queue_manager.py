from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import WebSocket

from backend.core import database
from backend.core.hardware import cleanup_vram
from backend.core.paths import TEMP_DIR, next_daily_output_paths, to_relative_posix
from backend.services.renderer import pick_random_music, render_final_video
from backend.services.script_gen import GeneratedScript, generate_script
from backend.services.subtitles import (
    generate_ass_subtitles,
    transcribe_words,
    unload_whisper_model,
)
from backend.services.tts_engine import synthesize_speech
from backend.services.visuals import (
    generate_ai_slideshow,
    generate_hook_card,
    prepare_gameplay_background,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage active WebSocket clients for live batch/job progress updates."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        targets = list(self._connections)
        if not targets:
            return
        payload = {"type": event_type, "data": data}
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                self._connections.discard(ws)


def _format_companion_txt(
    *,
    script: GeneratedScript,
    duration_sec: float,
    encoder_used: str,
    voice_used: str,
    visual_mode: str,
    visual_detail: str,
) -> str:
    hashtags = " ".join(f"#{t.lstrip('#')}" for t in script.tags if t.strip())
    lines = [
        f"TITLE:\n{script.title}",
        "",
        f"DESCRIPTION:\n{script.description}",
        "",
        f"TAGS:\n{hashtags}",
        "",
        "METADATA:",
        f"- Niche: {script.niche}",
        f"- Language: {script.language}",
        f"- Voice: {voice_used}",
        f"- Visual Mode: {visual_mode} ({visual_detail})",
        f"- Encoder: {encoder_used}",
        f"- Resolution: 1080x1920 @ 60fps",
        f"- Duration: {duration_sec:.2f}s",
        f"- Script Source: {script.source}",
        "",
        "FULL SCRIPT:",
        script.full_narration,
        "",
    ]
    return "\n".join(lines)


class QueueManager:
    """Sequential background worker that processes video generation batches safely."""

    def __init__(self, ws_manager: ConnectionManager) -> None:
        self.ws_manager = ws_manager
        self._queue: asyncio.Queue[tuple[str, str]] | None = None
        self._worker_task: asyncio.Task[None] | None = None
        self._cancelled_batches: set[str] = set()
        self._output_lock: asyncio.Lock | None = None
        self._running = False

    async def start(self) -> None:
        if self._worker_task is not None and not self._worker_task.done():
            return
        self._queue = asyncio.Queue()
        self._output_lock = asyncio.Lock()
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop(), name="shorts-queue-worker")
        logger.info("QueueManager worker started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        self._queue = None
        self._output_lock = None
        unload_whisper_model()
        cleanup_vram()
        logger.info("QueueManager worker stopped")

    async def enqueue_batch(self, batch_id: str, job_ids: list[str]) -> None:
        await self.start()
        assert self._queue is not None
        for job_id in job_ids:
            await self._queue.put((batch_id, job_id))

    async def cancel_batch(self, batch_id: str) -> dict[str, Any] | None:
        self._cancelled_batches.add(batch_id)
        batch = await database.get_batch(batch_id)
        if not batch:
            return None

        for job in batch["jobs"]:
            if job["status"] == "queued":
                updated = await database.update_job(
                    job["id"],
                    status="cancelled",
                    stage_label="Отменено",
                )
                if updated:
                    await self.ws_manager.broadcast("job_updated", updated)

        updated_batch = await database.recompute_batch_status(batch_id)
        if updated_batch:
            await self.ws_manager.broadcast("batch_updated", updated_batch)
        return updated_batch

    async def _emit_progress(
        self,
        *,
        batch_id: str,
        job_id: str,
        status: str,
        progress: int,
        stage_label: str,
        **extra: Any,
    ) -> None:
        updated_job = await database.update_job(
            job_id,
            status=status,
            progress=progress,
            stage_label=stage_label,
            **extra,
        )
        if updated_job:
            await self.ws_manager.broadcast("job_updated", updated_job)
        updated_batch = await database.recompute_batch_status(batch_id)
        if updated_batch:
            await self.ws_manager.broadcast("batch_updated", updated_batch)

    async def _worker_loop(self) -> None:
        assert self._queue is not None
        while self._running:
            try:
                batch_id, job_id = await self._queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._process_job(batch_id, job_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Unhandled error processing job %s: %s", job_id, exc)
            finally:
                self._queue.task_done()

    async def _process_job(self, batch_id: str, job_id: str) -> None:
        batch = await database.get_batch(batch_id)
        job = await database.get_job(job_id)
        if not batch or not job:
            return
        if batch_id in self._cancelled_batches or job["status"] != "queued":
            return

        work_dir = TEMP_DIR / f"job_{job_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            settings = await database.get_all_settings()
            previous_titles = [
                j["title"] for j in batch["jobs"] if j.get("title") and j["id"] != job_id
            ]

            # 1. Script generation
            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="scripting",
                progress=12,
                stage_label="Генерация сценария",
            )
            script = await generate_script(
                niche=batch["niche"],
                language=batch["language"],
                custom_topic=batch.get("custom_topic", ""),
                api_key=settings.get("llm_api_key", ""),
                base_url=settings.get("llm_base_url", "https://openrouter.ai/api/v1"),
                model=settings.get("llm_model", "deepseek/deepseek-chat"),
                previous_titles=previous_titles,
            )
            if batch_id in self._cancelled_batches:
                await self._emit_progress(
                    batch_id=batch_id,
                    job_id=job_id,
                    status="cancelled",
                    progress=0,
                    stage_label="Отменено",
                )
                return

            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="tts",
                progress=25,
                stage_label="Озвучка текста (TTS)",
                title=script.title,
                hook=script.hook,
                script_text=script.full_narration,
                description=script.description,
                tags=script.tags,
                image_prompts=script.image_prompts,
            )

            # 2. TTS Synthesis + silence removal
            voice_mp3 = work_dir / "voice.mp3"
            tts_res = await synthesize_speech(
                text=script.full_narration,
                output_mp3=voice_mp3,
                language=batch["language"],
                voice=batch["voice"],
                rate=batch["tts_rate"],
                engine=batch["tts_engine"],
                trim_silence=True,
            )
            if batch_id in self._cancelled_batches:
                await self._emit_progress(
                    batch_id=batch_id,
                    job_id=job_id,
                    status="cancelled",
                    progress=0,
                    stage_label="Отменено",
                )
                return

            # 3. Subtitles via faster-whisper
            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="subtitles",
                progress=45,
                stage_label="Таймкоды слов (Whisper)",
            )
            whisper_model = settings.get("whisper_model", "auto")
            words = await asyncio.to_thread(
                transcribe_words,
                voice_mp3,
                batch["language"],
                script.full_narration,
                whisper_model,
            )
            ass_path = work_dir / "subtitles.ass"
            await asyncio.to_thread(
                generate_ass_subtitles,
                words,
                ass_path,
                batch["subtitle_color"],
            )
            if batch_id in self._cancelled_batches:
                await self._emit_progress(
                    batch_id=batch_id,
                    job_id=job_id,
                    status="cancelled",
                    progress=0,
                    stage_label="Отменено",
                )
                return

            # 4. Visuals (Hook card + Gameplay or AI Slideshow)
            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="visuals",
                progress=65,
                stage_label="Подготовка визуала",
            )
            hook_png = work_dir / "hook_card.png"
            await asyncio.to_thread(
                generate_hook_card,
                title=script.title,
                subreddit_or_tag=script.subreddit_or_tag,
                author=script.author,
                niche=batch["niche"],
                output_png=hook_png,
            )

            bg_mp4 = work_dir / "background.mp4"
            bg_duration = tts_res.final_duration + 0.8
            visual_detail = "gameplay"
            if batch["visual_mode"] == "ai_slideshow":
                # Free Whisper VRAM before loading SDXL-Turbo on GPU
                unload_whisper_model()
                cleanup_vram()
                sdxl_model = settings.get("sdxl_model", "stabilityai/sdxl-turbo")
                _, visual_detail = await asyncio.to_thread(
                    generate_ai_slideshow,
                    image_prompts=script.image_prompts,
                    duration=bg_duration,
                    output_video=bg_mp4,
                    work_dir=work_dir / "slides",
                    sdxl_model=sdxl_model,
                    niche=batch["niche"],
                )
            else:
                await asyncio.to_thread(
                    prepare_gameplay_background,
                    duration=bg_duration,
                    output_video=bg_mp4,
                    niche=batch["niche"],
                )

            if batch_id in self._cancelled_batches:
                await self._emit_progress(
                    batch_id=batch_id,
                    job_id=job_id,
                    status="cancelled",
                    progress=0,
                    stage_label="Отменено",
                )
                return

            # 5. Final FFmpeg render
            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="rendering",
                progress=82,
                stage_label="Финальный рендер MP4",
            )

            try:
                music_vol = float(settings.get("music_volume", "0.20"))
            except ValueError:
                music_vol = 0.20
            music_path = pick_random_music()

            assert self._output_lock is not None
            async with self._output_lock:
                out_mp4, out_txt = next_daily_output_paths()
                # Reserve path while rendering
                out_mp4.touch(exist_ok=True)

            render_res = await asyncio.to_thread(
                render_final_video,
                bg_video=bg_mp4,
                voice_audio=voice_mp3,
                ass_subtitles=ass_path,
                hook_card_png=hook_png,
                output_mp4=out_mp4,
                music_path=music_path,
                music_volume=music_vol,
            )

            txt_content = _format_companion_txt(
                script=script,
                duration_sec=render_res.duration_sec,
                encoder_used=render_res.encoder_used,
                voice_used=tts_res.voice_used,
                visual_mode=batch["visual_mode"],
                visual_detail=visual_detail,
            )
            out_txt.write_text(txt_content, encoding="utf-8", newline="\n")

            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="completed",
                progress=100,
                stage_label="Готово",
                output_video_path=to_relative_posix(out_mp4),
                output_meta_path=to_relative_posix(out_txt),
                duration_sec=round(render_res.duration_sec, 2),
                file_size_bytes=render_res.file_size_bytes,
                encoder_used=render_res.encoder_used,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            await self._emit_progress(
                batch_id=batch_id,
                job_id=job_id,
                status="failed",
                progress=0,
                stage_label="Ошибка",
                error_message=str(exc)[:800],
            )
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            cleanup_vram()
