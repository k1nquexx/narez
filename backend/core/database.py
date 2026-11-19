from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from backend.core.config import get_initial_db_settings
from backend.core.paths import DATA_DIR, DB_PATH


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _connect(db_path: Path | None = None) -> aiosqlite.Connection:
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(target))
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    return conn


async def init_db(db_path: Path | None = None) -> None:
    """Create SQLite schema and seed default settings if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = await _connect(db_path)
    try:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                niche TEXT NOT NULL,
                language TEXT NOT NULL,
                voice TEXT NOT NULL,
                tts_engine TEXT NOT NULL,
                tts_rate TEXT NOT NULL,
                visual_mode TEXT NOT NULL,
                subtitle_color TEXT NOT NULL,
                custom_topic TEXT NOT NULL DEFAULT '',
                total_count INTEGER NOT NULL,
                completed_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                index_in_batch INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                progress INTEGER NOT NULL DEFAULT 0,
                stage_label TEXT NOT NULL DEFAULT 'В очереди',
                title TEXT NOT NULL DEFAULT '',
                hook TEXT NOT NULL DEFAULT '',
                script_text TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                image_prompts_json TEXT NOT NULL DEFAULT '[]',
                output_video_path TEXT NOT NULL DEFAULT '',
                output_meta_path TEXT NOT NULL DEFAULT '',
                duration_sec REAL NOT NULL DEFAULT 0.0,
                file_size_bytes INTEGER NOT NULL DEFAULT 0,
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_batch_id ON jobs(batch_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            """
        )

        defaults = get_initial_db_settings()
        for key, value in defaults.items():
            await conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        await conn.commit()
    finally:
        await conn.close()


async def get_all_settings(db_path: Path | None = None) -> dict[str, str]:
    conn = await _connect(db_path)
    try:
        async with conn.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}
    finally:
        await conn.close()


async def update_settings(updates: dict[str, str], db_path: Path | None = None) -> dict[str, str]:
    conn = await _connect(db_path)
    try:
        for key, value in updates.items():
            await conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )
        await conn.commit()
    finally:
        await conn.close()
    return await get_all_settings(db_path)


async def create_batch(
    *,
    niche: str,
    language: str,
    voice: str,
    tts_engine: str,
    tts_rate: str,
    visual_mode: str,
    subtitle_color: str,
    custom_topic: str,
    total_count: int,
    db_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    batch_id = uuid.uuid4().hex[:12]
    created_at = utc_now_iso()
    conn = await _connect(db_path)
    try:
        await conn.execute(
            """
            INSERT INTO batches (
                id, niche, language, voice, tts_engine, tts_rate,
                visual_mode, subtitle_color, custom_topic, total_count,
                completed_count, failed_count, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'queued', ?)
            """,
            (
                batch_id,
                niche,
                language,
                voice,
                tts_engine,
                tts_rate,
                visual_mode,
                subtitle_color,
                custom_topic,
                total_count,
                created_at,
            ),
        )

        jobs: list[dict[str, Any]] = []
        for idx in range(1, total_count + 1):
            job_id = uuid.uuid4().hex[:12]
            await conn.execute(
                """
                INSERT INTO jobs (
                    id, batch_id, index_in_batch, status, progress,
                    stage_label, created_at
                ) VALUES (?, ?, ?, 'queued', 0, 'В очереди', ?)
                """,
                (job_id, batch_id, idx, created_at),
            )
            jobs.append(
                {
                    "id": job_id,
                    "batch_id": batch_id,
                    "index_in_batch": idx,
                    "status": "queued",
                    "progress": 0,
                    "stage_label": "В очереди",
                    "created_at": created_at,
                }
            )
        await conn.commit()
    finally:
        await conn.close()

    batch = await get_batch(batch_id, db_path)
    assert batch is not None
    return batch, jobs


def _row_to_job(row: aiosqlite.Row) -> dict[str, Any]:
    item = dict(row)
    try:
        item["tags"] = json.loads(item.get("tags_json") or "[]")
    except json.JSONDecodeError:
        item["tags"] = []
    try:
        item["image_prompts"] = json.loads(item.get("image_prompts_json") or "[]")
    except json.JSONDecodeError:
        item["image_prompts"] = []
    return item


async def get_batch(batch_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = await _connect(db_path)
    try:
        async with conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            batch = dict(row)
        async with conn.execute(
            "SELECT * FROM jobs WHERE batch_id = ? ORDER BY index_in_batch ASC",
            (batch_id,),
        ) as jcur:
            job_rows = await jcur.fetchall()
            batch["jobs"] = [_row_to_job(r) for r in job_rows]
        return batch
    finally:
        await conn.close()


async def list_batches(limit: int = 30, db_path: Path | None = None) -> list[dict[str, Any]]:
    conn = await _connect(db_path)
    try:
        async with conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            batches = [dict(r) for r in rows]

        for batch in batches:
            async with conn.execute(
                "SELECT * FROM jobs WHERE batch_id = ? ORDER BY index_in_batch ASC",
                (batch["id"],),
            ) as jcur:
                job_rows = await jcur.fetchall()
                batch["jobs"] = [_row_to_job(r) for r in job_rows]
        return batches
    finally:
        await conn.close()


async def update_batch(
    batch_id: str,
    db_path: Path | None = None,
    **fields: Any,
) -> dict[str, Any] | None:
    if not fields:
        return await get_batch(batch_id, db_path)
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [batch_id]
    conn = await _connect(db_path)
    try:
        await conn.execute(f"UPDATE batches SET {cols} WHERE id = ?", vals)
        await conn.commit()
    finally:
        await conn.close()
    return await get_batch(batch_id, db_path)


async def recompute_batch_status(batch_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = await _connect(db_path)
    try:
        async with conn.execute(
            "SELECT status FROM jobs WHERE batch_id = ?",
            (batch_id,),
        ) as cur:
            statuses = [row["status"] for row in await cur.fetchall()]

        total = len(statuses)
        completed = sum(1 for s in statuses if s == "completed")
        failed = sum(1 for s in statuses if s == "failed")
        cancelled = sum(1 for s in statuses if s == "cancelled")
        active = sum(
            1 for s in statuses if s in {"scripting", "tts", "subtitles", "visuals", "rendering"}
        )
        queued = sum(1 for s in statuses if s == "queued")

        if active > 0:
            batch_status = "running"
        elif queued > 0:
            batch_status = "running" if (completed + failed) > 0 else "queued"
        elif total > 0 and cancelled == total:
            batch_status = "cancelled"
        elif total > 0 and failed == total:
            batch_status = "failed"
        elif cancelled > 0:
            batch_status = "cancelled"
        else:
            batch_status = "completed"

        await conn.execute(
            """
            UPDATE batches
            SET completed_count = ?, failed_count = ?, status = ?
            WHERE id = ?
            """,
            (completed, failed, batch_status, batch_id),
        )
        await conn.commit()
    finally:
        await conn.close()
    return await get_batch(batch_id, db_path)


async def get_job(job_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    conn = await _connect(db_path)
    try:
        async with conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cur:
            row = await cur.fetchone()
            return _row_to_job(row) if row else None
    finally:
        await conn.close()


async def update_job(
    job_id: str,
    db_path: Path | None = None,
    **fields: Any,
) -> dict[str, Any] | None:
    if not fields:
        return await get_job(job_id, db_path)
    payload: dict[str, Any] = {}
    for k, v in fields.items():
        if k == "tags":
            payload["tags_json"] = json.dumps(v, ensure_ascii=False)
        elif k == "image_prompts":
            payload["image_prompts_json"] = json.dumps(v, ensure_ascii=False)
        else:
            payload[k] = v

    cols = ", ".join(f"{k} = ?" for k in payload)
    vals = list(payload.values()) + [job_id]
    conn = await _connect(db_path)
    try:
        await conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", vals)
        await conn.commit()
    finally:
        await conn.close()
    return await get_job(job_id, db_path)


async def list_completed_videos(limit: int = 100, db_path: Path | None = None) -> list[dict[str, Any]]:
    conn = await _connect(db_path)
    try:
        async with conn.execute(
            """
            SELECT j.*, b.niche, b.language, b.voice, b.visual_mode, b.subtitle_color
            FROM jobs j
            JOIN batches b ON j.batch_id = b.id
            WHERE j.status = 'completed'
            ORDER BY j.completed_at DESC, j.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [_row_to_job(r) for r in rows]
    finally:
        await conn.close()


async def delete_job(job_id: str, db_path: Path | None = None) -> bool:
    conn = await _connect(db_path)
    try:
        cur = await conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()
