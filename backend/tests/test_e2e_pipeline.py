from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import websockets

from backend.core.hardware import find_binary
from backend.core.paths import BASE_DIR, from_relative_posix


def _ffprobe_json(mp4_path: Path) -> dict:
    ffprobe = find_binary("ffprobe")
    assert ffprobe, "ffprobe binary must exist"
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, f"ffprobe failed for {mp4_path}: {proc.stderr}"
    return json.loads(proc.stdout)


@pytest.mark.asyncio
async def test_full_end_to_end_two_videos() -> None:
    port = 8765
    base_url = f"http://127.0.0.1:{port}"
    ws_url = f"ws://127.0.0.1:{port}/ws/progress"

    log_file = BASE_DIR / "temp" / "e2e_uvicorn.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fp = log_file.open("w", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(BASE_DIR),
        env=env,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
    )

    try:
        # 1. Wait for server startup
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            healthy = False
            for _ in range(40):
                try:
                    r = await client.get("/api/health")
                    if r.status_code == 200:
                        healthy = True
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.5)
            assert healthy, "Backend server failed to become healthy within 20s"

            # 2. Check built React SPA & API endpoints
            root_resp = await client.get("/")
            assert root_resp.status_code == 200
            assert "ShortsFactory" in root_resp.text

            sys_resp = await client.get("/api/system/info")
            assert sys_resp.status_code == 200
            sys_json = sys_resp.json()
            assert sys_json["hardware"]["ffmpeg_path"]
            assert "Montserrat-ExtraBold.ttf" in sys_json["fonts"]

            voices_resp = await client.get("/api/voices")
            assert voices_resp.status_code == 200
            assert "ru" in voices_resp.json()["voices"]
            assert "en" in voices_resp.json()["voices"]

            assets_resp = await client.get("/api/assets")
            assert assets_resp.status_code == 200

            # 3. Connect WebSocket & trigger 2 end-to-end batches (RU Gameplay + EN AI Slideshow)
            ws_events: list[dict] = []
            async with websockets.connect(ws_url) as ws:
                first_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10.0))
                assert first_msg["type"] == "snapshot"
                ws_events.append(first_msg)

                b1_resp = await client.post(
                    "/api/batches",
                    json={
                        "niche": "reddit",
                        "language": "ru",
                        "voice": "ru-RU-DmitryNeural",
                        "tts_engine": "edge",
                        "tts_rate": "+15%",
                        "visual_mode": "gameplay",
                        "subtitle_color": "#FFE600",
                        "custom_topic": "",
                        "count": 1,
                    },
                )
                assert b1_resp.status_code == 201, b1_resp.text
                batch1 = b1_resp.json()

                b2_resp = await client.post(
                    "/api/batches",
                    json={
                        "niche": "scary",
                        "language": "en",
                        "voice": "en-US-ChristopherNeural",
                        "tts_engine": "edge",
                        "tts_rate": "+15%",
                        "visual_mode": "ai_slideshow",
                        "subtitle_color": "#39FF50",
                        "custom_topic": "",
                        "count": 1,
                    },
                )
                assert b2_resp.status_code == 201, b2_resp.text
                batch2 = b2_resp.json()

                # Poll batches & drain WebSocket events until both complete
                deadline = time.monotonic() + 900.0
                final_batches: dict[str, dict] = {}
                while time.monotonic() < deadline:
                    try:
                        while True:
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            ws_events.append(json.loads(raw))
                    except asyncio.TimeoutError:
                        pass

                    for bid in (batch1["id"], batch2["id"]):
                        res = await client.get(f"/api/batches/{bid}")
                        assert res.status_code == 200
                        bdata = res.json()
                        final_batches[bid] = bdata

                    statuses = [b["status"] for b in final_batches.values()]
                    if all(s in {"completed", "failed", "cancelled"} for s in statuses):
                        break
                    await asyncio.sleep(1.5)

                for bid, bdata in final_batches.items():
                    assert bdata["status"] == "completed", f"Batch {bid} ended with {bdata}"
                    assert bdata["completed_count"] == 1
                    assert bdata["failed_count"] == 0

                assert any(e.get("type") == "job_updated" for e in ws_events)

            # 4. Inspect produced files via disk + ffprobe + HTTP stream
            videos_resp = await client.get("/api/videos")
            assert videos_resp.status_code == 200
            all_videos = videos_resp.json()
            by_id = {v["id"]: v for v in all_videos}

            produced_jobs = [
                final_batches[batch1["id"]]["jobs"][0],
                final_batches[batch2["id"]]["jobs"][0],
            ]

            for job in produced_jobs:
                assert job["id"] in by_id
                mp4_path = from_relative_posix(job["output_video_path"])
                txt_path = from_relative_posix(job["output_meta_path"])
                assert mp4_path.is_file(), f"Missing MP4: {mp4_path}"
                assert txt_path.is_file(), f"Missing TXT: {txt_path}"
                assert mp4_path.stat().st_size > 500_000

                txt_content = txt_path.read_text(encoding="utf-8")
                assert "TITLE:" in txt_content
                assert "DESCRIPTION:" in txt_content
                assert "TAGS:" in txt_content
                assert "FULL SCRIPT:" in txt_content

                probe = _ffprobe_json(mp4_path)
                v_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
                a_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
                assert len(v_streams) == 1
                assert len(a_streams) == 1

                vs = v_streams[0]
                assert vs["width"] == 1080
                assert vs["height"] == 1920
                assert vs["codec_name"] == "h264"
                assert vs["pix_fmt"] == "yuv420p"
                assert vs["r_frame_rate"] == "60/1"

                aus = a_streams[0]
                assert aus["codec_name"] == "aac"
                assert str(aus["sample_rate"]) == "48000"

                dur = float(probe["format"]["duration"])
                assert dur >= 30.0, f"Expected full Short >=30s, got {dur:.2f}s"

                print(
                    f"[E2E VERIFIED] {mp4_path.name}: {vs['width']}x{vs['height']} "
                    f"@ {vs['r_frame_rate']} {vs['codec_name']}/{aus['codec_name']} "
                    f"dur={dur:.2f}s size={mp4_path.stat().st_size}B"
                )

                # Verify streaming endpoint
                stream_resp = await client.get(f"/api/videos/{job['id']}/stream")
                assert stream_resp.status_code == 200
                assert "video/mp4" in stream_resp.headers.get("content-type", "")
                assert len(stream_resp.content) == mp4_path.stat().st_size
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        log_fp.close()
