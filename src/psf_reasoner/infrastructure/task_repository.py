"""SQLite-backed background-task store (shared migration version 2).

Task state lives in the same database as V2/V3 reports so the whole
workbench shares one storage system and one migration chain.  Status
values: ``queued | running | succeeded | failed``; the stage tracks
fine-grained progress inside ``running``.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from psf_reasoner.infrastructure.sqlite_migrations import ensure_schema

_DEFAULT_DB_PATH = ".psf_reasoner/reports.db"
# The migration version this repository requires.
SCHEMA_VERSION = 2

TASK_STATUS_QUEUED = "queued"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCEEDED = "succeeded"
TASK_STATUS_FAILED = "failed"


class TaskNotFoundError(LookupError):
    """Raised when a task does not exist in the repository."""


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    status: str
    stage: str
    progress: float
    report_id: str | None
    error: str | None
    request_json: str
    created_at: str = ""
    updated_at: str = ""

    def with_timestamps(self) -> TaskRecord:
        """Return a copy with created/updated timestamps filled (if absent)."""
        now = datetime.now(UTC).isoformat()
        return TaskRecord(
            task_id=self.task_id,
            status=self.status,
            stage=self.stage,
            progress=self.progress,
            report_id=self.report_id,
            error=self.error,
            request_json=self.request_json,
            created_at=self.created_at or now,
            updated_at=self.updated_at or now,
        )


class TaskRepository:
    """Thread-safe SQLite store for background analysis tasks.

    The schema initialises lazily (no import-time side effects) and
    shares the ``schema_meta`` migration ledger with the other
    repositories in this database.
    """

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._lock = RLock()
        self._initialised = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, record: TaskRecord) -> None:
        record = record.with_timestamps()
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO tasks"
                    "(task_id, status, stage, progress, report_id, error, request_json, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        record.task_id,
                        record.status,
                        record.stage,
                        record.progress,
                        record.report_id,
                        record.error,
                        record.request_json,
                        record.created_at,
                        record.updated_at,
                    ),
                )

    def get(self, task_id: str) -> TaskRecord:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT task_id, status, stage, progress, report_id, error, request_json, "
                    "created_at, updated_at FROM tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        return TaskRecord(*row)

    def update(self, task_id: str, **fields) -> None:
        """Update status/stage/progress/report_id/error; refreshes updated_at."""
        allowed = {"status", "stage", "progress", "report_id", "error"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unsupported task fields: {sorted(unknown)}")
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = [fields[name] for name in fields]
        values.append(datetime.now(UTC).isoformat())
        values.append(task_id)
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute(
                    f"UPDATE tasks SET {assignments}, updated_at = ? WHERE task_id = ?",
                    values,
                )
        if cursor.rowcount == 0:
            raise TaskNotFoundError(task_id)

    def list_recent(self, limit: int = 20) -> tuple[TaskRecord, ...]:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT task_id, status, stage, progress, report_id, error, request_json, "
                    "created_at, updated_at FROM tasks ORDER BY updated_at DESC LIMIT ?",
                    (max(1, min(limit, 100)),),
                ).fetchall()
        return tuple(TaskRecord(*row) for row in rows)

    def mark_stale_running(self, max_running_seconds: float) -> int:
        """Mark running tasks not updated within *max_running_seconds* as failed.

        Used at startup: a task left ``running`` across a restart cannot
        complete, so it is failed with an explanatory message.
        """
        cutoff = datetime.fromtimestamp(time.time() - max_running_seconds, tz=UTC).isoformat()
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute(
                    "UPDATE tasks SET status = ?, stage = ?, error = ?, updated_at = ? "
                    "WHERE status = ? AND updated_at < ?",
                    (
                        TASK_STATUS_FAILED,
                        "failed",
                        "server restarted during analysis",
                        datetime.now(UTC).isoformat(),
                        TASK_STATUS_RUNNING,
                        cutoff,
                    ),
                )
        return cursor.rowcount

    def prune_old_finished(self, max_age_seconds: float) -> int:
        """Remove finished tasks older than *max_age_seconds*."""
        cutoff = datetime.fromtimestamp(time.time() - max_age_seconds, tz=UTC).isoformat()
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE status IN (?, ?) AND updated_at < ?",
                    (TASK_STATUS_SUCCEEDED, TASK_STATUS_FAILED, cutoff),
                )
        return cursor.rowcount

    def count_active(self) -> int:
        """Queued + running task count (queue admission control)."""
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status IN (?, ?)",
                    (TASK_STATUS_QUEUED, TASK_STATUS_RUNNING),
                ).fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        if self._initialised:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            ensure_schema(conn, SCHEMA_VERSION)
        self._initialised = True

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def serialize_request(request) -> str:
    """Serialize an AnalysisRequest for storage (contains paths, not structure text)."""
    return json.dumps(request.model_dump(mode="json"), ensure_ascii=False, default=str)
