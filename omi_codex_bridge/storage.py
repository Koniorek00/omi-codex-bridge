from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from .models import utc_now_iso


class BridgeStorage:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT NOT NULL,
                    source TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dedupe_key TEXT UNIQUE,
                    session_id TEXT,
                    transcript_context TEXT,
                    command_json TEXT,
                    exit_code INTEGER,
                    output_path TEXT,
                    last_message_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS uid_sightings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);
                CREATE INDEX IF NOT EXISTS idx_uid_sightings_uid ON uid_sightings(uid, created_at DESC);
                """
            )
            self._connection.commit()

    def reset(self) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM events")
            self._connection.execute("DELETE FROM jobs")
            self._connection.execute("DELETE FROM uid_sightings")
            self._connection.commit()

    def create_job(
        self,
        uid: str,
        source: str,
        prompt: str,
        workspace: str,
        dedupe_key: str | None = None,
        session_id: str | None = None,
        transcript_context: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        now = utc_now_iso()
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO jobs(
                    uid, source, prompt, workspace, status, dedupe_key, session_id,
                    transcript_context, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                """,
                (uid, source, prompt, workspace, dedupe_key, session_id, transcript_context, now, now),
            )
            inserted = cursor.rowcount == 1
            if inserted:
                job_id = int(cursor.lastrowid)
            elif dedupe_key:
                row = self._connection.execute("SELECT id FROM jobs WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
                job_id = int(row["id"])
            else:
                row = self._connection.execute("SELECT last_insert_rowid() AS id").fetchone()
                job_id = int(row["id"])
            self._connection.commit()
        job = self.get_job(f"job-{job_id}")
        if inserted and job:
            self.add_event(job["id"], "job.created", "Job queued from Omi.")
            self.record_uid(uid, source)
        return job, inserted

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        numeric_id = self._numeric_id(job_id)
        with self._lock:
            row = self._connection.execute("SELECT * FROM jobs WHERE id = ?", (numeric_id,)).fetchone()
        return self._job_row_to_api(row) if row else None

    def list_jobs(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with self._lock:
            if status:
                rows = self._connection.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, safe_limit),
                ).fetchall()
            else:
                rows = self._connection.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
        return [self._job_row_to_api(row) for row in rows]

    def status_counts(self) -> dict[str, int]:
        with self._lock:
            rows = self._connection.execute("SELECT status, COUNT(*) AS count FROM jobs GROUP BY status").fetchall()
        return {row["status"]: int(row["count"]) for row in rows}

    def first_job_with_status(self, status: str = "pending") -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY id ASC LIMIT 1",
                (status,),
            ).fetchone()
        return self._job_row_to_api(row) if row else None

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        if job["status"] == "running":
            raise ValueError("Running jobs cannot be cancelled yet; wait for completion or stop the Codex process manually.")
        if job["status"] == "cancelled":
            return job
        updated = self.update_job(job_id, status="cancelled", finished_at=utc_now_iso())
        self.add_event(job_id, "job.cancelled", "Job cancelled before execution.")
        return updated

    def retry_job(self, job_id: str, source: str = "omi-chat-tool-retry") -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        if job["status"] == "running":
            raise ValueError("Running jobs cannot be retried until they finish.")
        new_job, _ = self.create_job(job["uid"], source, job["prompt"], job["workspace"])
        self.add_event(job_id, "job.retried", f"Retry queued as {new_job['id']}.")
        return new_job

    def update_job(self, job_id: str, **fields: Any) -> dict[str, Any]:
        numeric_id = self._numeric_id(job_id)
        if not fields:
            job = self.get_job(job_id)
            if not job:
                raise KeyError(job_id)
            return job
        fields["updated_at"] = utc_now_iso()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = [json.dumps(value) if key == "command_json" else value for key, value in fields.items()]
        values.append(numeric_id)
        with self._lock:
            self._connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", tuple(values))
            self._connection.commit()
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        return job

    def add_event(self, job_id: str | None, kind: str, message: str) -> dict[str, Any]:
        numeric_id = self._numeric_id(job_id) if job_id else None
        now = utc_now_iso()
        with self._lock:
            cursor = self._connection.execute(
                "INSERT INTO events(job_id, kind, message, created_at) VALUES (?, ?, ?, ?)",
                (numeric_id, kind, message, now),
            )
            self._connection.commit()
            event_id = int(cursor.lastrowid)
        return {"id": event_id, "job_id": job_id, "kind": kind, "message": message, "created_at": now}

    def record_uid(self, uid: str | None, source: str) -> dict[str, Any] | None:
        clean_uid = " ".join((uid or "").split())[:160]
        clean_source = " ".join((source or "unknown").split())[:120]
        if not clean_uid:
            return None
        now = utc_now_iso()
        with self._lock:
            cursor = self._connection.execute(
                "INSERT INTO uid_sightings(uid, source, created_at) VALUES (?, ?, ?)",
                (clean_uid, clean_source, now),
            )
            self._connection.commit()
            sighting_id = int(cursor.lastrowid)
        return {"id": sighting_id, "uid": clean_uid, "source": clean_source, "created_at": now}

    def list_known_uids(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT uid, MAX(created_at) AS last_seen, COUNT(*) AS seen_count, GROUP_CONCAT(DISTINCT source) AS sources
                FROM (
                    SELECT uid, source, created_at FROM uid_sightings
                    UNION ALL
                    SELECT uid, source, created_at FROM jobs
                )
                WHERE uid IS NOT NULL AND TRIM(uid) != ''
                GROUP BY uid
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "uid": row["uid"],
                "last_seen": row["last_seen"],
                "seen_count": int(row["seen_count"]),
                "sources": sorted(source for source in (row["sources"] or "").split(",") if source),
            }
            for row in rows
        ]

    def list_events(self, job_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 300))
        with self._lock:
            if job_id:
                rows = self._connection.execute(
                    "SELECT * FROM events WHERE job_id = ? ORDER BY id DESC LIMIT ?",
                    (self._numeric_id(job_id), safe_limit),
                ).fetchall()
            else:
                rows = self._connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
        return [self._event_row_to_api(row) for row in rows]

    @staticmethod
    def _numeric_id(job_id: str | None) -> int:
        if job_id is None:
            raise ValueError("Missing job id")
        return int(job_id[4:] if job_id.startswith("job-") else job_id)

    @staticmethod
    def _job_row_to_api(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": f"job-{row['id']}",
            "uid": row["uid"],
            "source": row["source"],
            "prompt": row["prompt"],
            "workspace": row["workspace"],
            "status": row["status"],
            "session_id": row["session_id"],
            "transcript_context": row["transcript_context"],
            "command": json.loads(row["command_json"]) if row["command_json"] else None,
            "exit_code": row["exit_code"],
            "output_path": row["output_path"],
            "last_message_path": row["last_message_path"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
        }

    @staticmethod
    def _event_row_to_api(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "job_id": f"job-{row['job_id']}" if row["job_id"] else None,
            "kind": row["kind"],
            "message": row["message"],
            "created_at": row["created_at"],
        }
