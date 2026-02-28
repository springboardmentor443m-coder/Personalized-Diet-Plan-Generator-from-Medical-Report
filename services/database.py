"""SQLite database layer — sessions, documents, and task queue."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id                 TEXT PRIMARY KEY,
    created_at         TEXT NOT NULL,
    aggregation_status TEXT DEFAULT 'pending',
    result_json        TEXT,
    diet_plan_json     TEXT,
    safety_json        TEXT,
    diet_meta_json     TEXT,
    processing_time    REAL
);

CREATE TABLE IF NOT EXISTS documents (
    id                 TEXT PRIMARY KEY,
    session_id         TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    original_filename  TEXT,
    doc_type           TEXT,
    user_declared_type TEXT,
    report_datetime    TEXT,
    status             TEXT DEFAULT 'pending',
    error              TEXT,
    file_hash          TEXT,
    file_path          TEXT,
    processing_time    REAL,
    result_json        TEXT,
    created_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash    ON documents(file_hash);

CREATE TABLE IF NOT EXISTS task_queue (
    id           TEXT PRIMARY KEY,
    task_type    TEXT NOT NULL,
    status       TEXT DEFAULT 'queued',
    progress     TEXT,
    session_id   TEXT,
    input_json   TEXT,
    result_json  TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    completed_at TEXT
);
"""


def _get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        logger.info("Database ready: %s", DATABASE_PATH)
    finally:
        conn.close()


# --- Session CRUD ---

def create_session() -> str:
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute("INSERT INTO sessions (id, created_at) VALUES (?, ?)", (session_id, now))
        conn.commit()
    finally:
        conn.close()
    return session_id


def get_session(session_id: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_session(session_id: str, **kwargs: Any) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [session_id]
    conn = _get_connection()
    try:
        conn.execute(f"UPDATE sessions SET {cols} WHERE id = ?", vals)
        conn.commit()
    finally:
        conn.close()


def save_session_result(session_id: str, result_json: dict) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE sessions SET result_json = ? WHERE id = ?",
            (json.dumps(result_json, default=str), session_id),
        )
        conn.commit()
    finally:
        conn.close()


def save_diet_result(
    session_id: str,
    diet_plan: dict | None,
    safety: dict | None,
    diet_meta: dict | None,
) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE sessions SET diet_plan_json = ?, safety_json = ?, diet_meta_json = ? WHERE id = ?",
            (
                json.dumps(diet_plan, default=str) if diet_plan else None,
                json.dumps(safety, default=str) if safety else None,
                json.dumps(diet_meta, default=str) if diet_meta else None,
                session_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# --- Document CRUD ---

def register_document(
    session_id: str,
    doc_id: str,
    original_filename: str,
    user_declared_type: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO documents
               (id, session_id, original_filename, user_declared_type, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (doc_id, session_id, original_filename, user_declared_type, now),
        )
        conn.commit()
    finally:
        conn.close()


def update_document(doc_id: str, **kwargs: Any) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [doc_id]
    conn = _get_connection()
    try:
        conn.execute(f"UPDATE documents SET {cols} WHERE id = ?", vals)
        conn.commit()
    finally:
        conn.close()


def save_document_result(doc_id: str, result: dict) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE documents SET result_json = ? WHERE id = ?",
            (json.dumps(result, default=str), doc_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_documents_for_session(session_id: str) -> list[dict]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM documents WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_duplicate_hash(session_id: str, file_hash: str) -> bool:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM documents WHERE session_id = ? AND file_hash = ?",
            (session_id, file_hash),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# --- Task Queue CRUD ---

def create_task(task_type: str, input_data: dict | None = None) -> str:
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO task_queue (id, task_type, status, input_json, created_at) VALUES (?, ?, 'queued', ?, ?)",
            (task_id, task_type, json.dumps(input_data, default=str) if input_data else None, now),
        )
        conn.commit()
    finally:
        conn.close()
    return task_id


def get_task(task_id: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM task_queue WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("input_json", "result_json"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    finally:
        conn.close()


def update_task(task_id: str, **kwargs: Any) -> None:
    if not kwargs:
        return
    for k, v in kwargs.items():
        if isinstance(v, dict):
            kwargs[k] = json.dumps(v, default=str)
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [task_id]
    conn = _get_connection()
    try:
        conn.execute(f"UPDATE task_queue SET {cols} WHERE id = ?", vals)
        conn.commit()
    finally:
        conn.close()


# --- Cleanup ---

def cleanup_old_sessions(ttl_hours: int = 72) -> int:
    """Delete sessions and associated files older than ttl_hours."""
    import shutil
    from config.settings import UPLOAD_DIR

    conn = _get_connection()
    try:
        cutoff = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            "SELECT id FROM sessions WHERE datetime(created_at) < datetime(?, '-' || ? || ' hours')",
            (cutoff, ttl_hours),
        ).fetchall()

        deleted = 0
        for row in rows:
            sid = row["id"]
            session_dir = UPLOAD_DIR / sid
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            deleted += 1

        conn.execute(
            """DELETE FROM task_queue
               WHERE datetime(created_at) < datetime(?, '-' || ? || ' hours')
                 AND status IN ('complete', 'failed')""",
            (cutoff, ttl_hours),
        )
        conn.commit()
        if deleted:
            logger.info("Cleaned up %d expired session(s)", deleted)
        return deleted
    finally:
        conn.close()
