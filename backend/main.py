from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.core import database
from backend.core.hardware import detect_hardware
from backend.core.paths import (
    BACKGROUNDS_DIR,
    FONTS_DIR,
    FRONTEND_DIST_DIR,
    MUSIC_DIR,
    OUTPUT_DIR,
    ensure_directories,
    from_relative_posix,
    safe_asset_path,
)
from backend.core.queue_manager import ConnectionManager, QueueManager
from backend.scripts.ensure_assets import ensure_fonts
from backend.services.renderer import list_music_tracks
from backend.services.script_gen import NICHE_INFO
from backend.services.tts_engine import VOICES, get_default_voice
from backend.services.visuals import list_gameplay_backgrounds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ws_manager = ConnectionManager()
queue_manager = QueueManager(ws_manager)

ALLOWED_BG_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
ALLOWED_MUSIC_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}

SUBTITLE_COLOR_PRESETS = [
    {"name": "Viral Yellow", "hex": "#FFE600"},
    {"name": "Neon Green", "hex": "#39FF50"},
    {"name": "Electric Cyan", "hex": "#00E5FF"},
    {"name": "Crimson Red", "hex": "#FF3B30"},
    {"name": "Pure White", "hex": "#FFFFFF"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_directories()
    try:
        ensure_fonts()
    except Exception as exc:
        logger.warning("Font check warning during startup: %s", exc)
    await database.init_db()
    await queue_manager.start()
    yield
    await queue_manager.stop()


app = FastAPI(
    title="ShortsFactory API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateBatchRequest(BaseModel):
    niche: Literal["reddit", "scary", "psychology", "motivation"] = "reddit"
    language: Literal["ru", "en"] = "ru"
    voice: str = ""
    tts_engine: Literal["edge", "silero"] = "edge"
    tts_rate: str = "+15%"
    visual_mode: Literal["gameplay", "ai_slideshow"] = "gameplay"
    subtitle_color: str = "#FFE600"
    custom_topic: str = Field(default="", max_length=200)
    count: int = Field(default=1, ge=1, le=20)


class UpdateSettingsRequest(BaseModel):
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    whisper_model: str | None = None
    tts_default_rate: str | None = None
    music_volume: float | None = Field(default=None, ge=0.0, le=1.0)
    subtitle_highlight_color: str | None = None
    sdxl_model: str | None = None


def _mask_key(raw: str) -> str:
    clean = raw.strip()
    if not clean:
        return ""
    if len(clean) <= 8:
        return "••••" + clean[-2:]
    return clean[:4] + "••••" + clean[-4:]


def _asset_item(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
    }


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system/info")
async def system_info() -> dict[str, Any]:
    hw = detect_hardware().to_dict()
    fonts = sorted(p.name for p in FONTS_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".ttf", ".otf"})
    videos = await database.list_completed_videos(limit=500)
    return {
        "hardware": hw,
        "fonts": fonts,
        "assets": {
            "backgrounds_count": len(list_gameplay_backgrounds()),
            "music_count": len(list_music_tracks()),
            "completed_videos_count": len(videos),
        },
        "whisper_models": ["auto", "tiny", "base", "small", "medium"],
    }


@app.get("/api/voices")
async def get_voices() -> dict[str, Any]:
    hw = detect_hardware()
    return {
        "voices": VOICES,
        "niches": NICHE_INFO,
        "subtitle_colors": SUBTITLE_COLOR_PRESETS,
        "silero_available": hw.torch_available,
    }


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    raw = await database.get_all_settings()
    api_key = raw.get("llm_api_key", "")
    return {
        "llm_api_key_set": bool(api_key.strip()),
        "llm_api_key_masked": _mask_key(api_key),
        "llm_base_url": raw.get("llm_base_url", "https://openrouter.ai/api/v1"),
        "llm_model": raw.get("llm_model", "deepseek/deepseek-chat"),
        "whisper_model": raw.get("whisper_model", "auto"),
        "tts_default_rate": raw.get("tts_default_rate", "+15%"),
        "music_volume": float(raw.get("music_volume", "0.20")),
        "subtitle_highlight_color": raw.get("subtitle_highlight_color", "#FFE600"),
        "sdxl_model": raw.get("sdxl_model", "stabilityai/sdxl-turbo"),
    }


@app.put("/api/settings")
async def put_settings(payload: UpdateSettingsRequest) -> dict[str, Any]:
    updates: dict[str, str] = {}
    if payload.llm_api_key is not None:
        updates["llm_api_key"] = payload.llm_api_key.strip()
    if payload.llm_base_url is not None:
        updates["llm_base_url"] = payload.llm_base_url.strip()
    if payload.llm_model is not None:
        updates["llm_model"] = payload.llm_model.strip()
    if payload.whisper_model is not None:
        updates["whisper_model"] = payload.whisper_model.strip()
    if payload.tts_default_rate is not None:
        updates["tts_default_rate"] = payload.tts_default_rate.strip()
    if payload.music_volume is not None:
        updates["music_volume"] = f"{payload.music_volume:.2f}"
    if payload.subtitle_highlight_color is not None:
        updates["subtitle_highlight_color"] = payload.subtitle_highlight_color.strip()
    if payload.sdxl_model is not None:
        updates["sdxl_model"] = payload.sdxl_model.strip()

    if updates:
        await database.update_settings(updates)
    return await get_settings()


@app.post("/api/batches", status_code=201)
async def create_batch(req: CreateBatchRequest) -> dict[str, Any]:
    voice = req.voice.strip() or get_default_voice(req.language)
    batch, jobs = await database.create_batch(
        niche=req.niche,
        language=req.language,
        voice=voice,
        tts_engine=req.tts_engine,
        tts_rate=req.tts_rate,
        visual_mode=req.visual_mode,
        subtitle_color=req.subtitle_color,
        custom_topic=req.custom_topic.strip(),
        total_count=req.count,
    )
    await queue_manager.enqueue_batch(batch["id"], [j["id"] for j in jobs])
    await ws_manager.broadcast("batch_updated", batch)
    return batch


@app.get("/api/batches")
async def list_batches(limit: int = 25) -> list[dict[str, Any]]:
    return await database.list_batches(limit=min(max(limit, 1), 100))


@app.get("/api/batches/{batch_id}")
async def get_batch(batch_id: str) -> dict[str, Any]:
    batch = await database.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@app.post("/api/batches/{batch_id}/cancel")
async def cancel_batch(batch_id: str) -> dict[str, Any]:
    batch = await queue_manager.cancel_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@app.get("/api/videos")
async def list_videos(limit: int = 100) -> list[dict[str, Any]]:
    rows = await database.list_completed_videos(limit=min(max(limit, 1), 300))
    result: list[dict[str, Any]] = []
    for row in rows:
        video_path = from_relative_posix(row["output_video_path"]) if row.get("output_video_path") else None
        row["file_exists"] = bool(video_path and video_path.is_file())
        row["stream_url"] = f"/api/videos/{row['id']}/stream"
        row["download_url"] = f"/api/videos/{row['id']}/download"
        row["meta_url"] = f"/api/videos/{row['id']}/meta"
        result.append(row)
    return result


async def _get_video_job_or_404(job_id: str) -> dict[str, Any]:
    job = await database.get_job(job_id)
    if not job or job["status"] != "completed" or not job.get("output_video_path"):
        raise HTTPException(status_code=404, detail="Completed video not found")
    return job


@app.get("/api/videos/{job_id}/stream")
async def stream_video(job_id: str) -> FileResponse:
    job = await _get_video_job_or_404(job_id)
    video_path = from_relative_posix(job["output_video_path"])
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file missing on disk")
    return FileResponse(path=video_path, media_type="video/mp4")


@app.get("/api/videos/{job_id}/download")
async def download_video(job_id: str) -> FileResponse:
    job = await _get_video_job_or_404(job_id)
    video_path = from_relative_posix(job["output_video_path"])
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file missing on disk")
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=video_path.name,
    )


@app.get("/api/videos/{job_id}/meta")
async def download_video_meta(job_id: str) -> PlainTextResponse:
    job = await _get_video_job_or_404(job_id)
    meta_rel = job.get("output_meta_path") or ""
    if meta_rel:
        meta_path = from_relative_posix(meta_rel)
        if meta_path.is_file():
            content = meta_path.read_text(encoding="utf-8")
            return PlainTextResponse(
                content=content,
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{meta_path.name}"'},
            )
    raise HTTPException(status_code=404, detail="Metadata text file missing on disk")


@app.delete("/api/videos/{job_id}")
async def delete_video(job_id: str) -> dict[str, Any]:
    job = await database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    for key in ("output_video_path", "output_meta_path"):
        rel = job.get(key) or ""
        if rel:
            target = from_relative_posix(rel)
            try:
                if target.is_file() and target.resolve().is_relative_to(OUTPUT_DIR.resolve()):
                    target.unlink()
            except OSError as exc:
                logger.warning("Could not delete file %s: %s", target, exc)

    deleted = await database.delete_job(job_id)
    await database.recompute_batch_status(job["batch_id"])
    return {"deleted": deleted, "id": job_id}


def _resolve_asset_category(category: str) -> tuple[Path, set[str]]:
    if category == "backgrounds":
        return BACKGROUNDS_DIR, ALLOWED_BG_EXTS
    if category == "music":
        return MUSIC_DIR, ALLOWED_MUSIC_EXTS
    raise HTTPException(status_code=400, detail="Category must be 'backgrounds' or 'music'")


@app.get("/api/assets")
async def list_assets() -> dict[str, Any]:
    return {
        "backgrounds": [_asset_item(p) for p in list_gameplay_backgrounds()],
        "music": [_asset_item(p) for p in list_music_tracks()],
    }


@app.post("/api/assets/{category}", status_code=201)
async def upload_asset(category: str, file: UploadFile = File(...)) -> dict[str, Any]:
    target_dir, allowed_exts = _resolve_asset_category(category)
    raw_name = Path(file.filename or "").name
    if not raw_name:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(raw_name).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension {ext!r}. Allowed: {', '.join(sorted(allowed_exts))}",
        )

    try:
        dest = safe_asset_path(target_dir, raw_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    target_dir.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    return _asset_item(dest)


@app.delete("/api/assets/{category}/{filename}")
async def delete_asset(category: str, filename: str) -> dict[str, Any]:
    target_dir, _ = _resolve_asset_category(category)
    try:
        target = safe_asset_path(target_dir, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not target.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    target.unlink()
    return {"deleted": True, "filename": filename}


@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        # Send immediate initial state snapshot
        batches = await database.list_batches(limit=15)
        await websocket.send_json({"type": "snapshot", "data": {"batches": batches}})
        while True:
            # Keep socket alive; client pings or messages are ignored cleanly
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


# Serve built React SPA if present
if (FRONTEND_DIST_DIR / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")),
        name="frontend-assets",
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path.startswith(("api/", "ws/")):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.is_file():
        if full_path:
            candidate = (FRONTEND_DIST_DIR / full_path).resolve()
            if candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST_DIR.resolve()):
                return FileResponse(candidate)
        return HTMLResponse(index_file.read_text(encoding="utf-8"))

    return HTMLResponse(
        "<h1>ShortsFactory Backend Running</h1>"
        "<p>Frontend build not found at <code>frontend/dist/index.html</code>.</p>",
        status_code=200,
    )
