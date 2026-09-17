"""SQLite-backed V3 analysis payload repository.

Stores the combined V3 payload (V2 report + structural context + causal
graph + literature) in the SAME SQLite database file used by
SqliteReportRepository (``.psf_reasoner/reports.db``) so both kinds of
report share one storage system.  Schema changes go through a versioned
migration table (``schema_meta``) rather than ad-hoc ALTERs.

The schema is initialised lazily on first use so that constructing the
repository (and importing the API module) has no filesystem side
effects.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

_DEFAULT_DB_PATH = ".psf_reasoner/reports.db"
SCHEMA_VERSION = 1

_MIGRATIONS: tuple[tuple[str, ...], ...] = (
    # version 1
    (
        "CREATE TABLE IF NOT EXISTS v3_reports ("
        "  report_id    TEXT PRIMARY KEY,"
        "  generated_at TEXT NOT NULL,"
        "  payload      TEXT NOT NULL"
        ")",
        "CREATE INDEX IF NOT EXISTS idx_v3_reports_generated_at ON v3_reports(generated_at DESC)",
    ),
)


class V3ReportNotFoundError(LookupError):
    """Raised when a V3 report does not exist in the repository."""


class V3ReportRepository:
    """Thread-safe SQLite store for V3 payloads.

    Shares the database file with :class:`SqliteReportRepository`.
    Connections are opened per operation under an ``RLock`` and the
    database runs in WAL mode, so multiple processes may read while one
    writes.
    """

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._lock = RLock()
        self._initialised = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, payload: dict) -> None:
        """Store a V3 payload keyed by its ``report_id``."""
        report_id = payload["report_id"]
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO v3_reports(report_id, generated_at, payload) "
                    "VALUES (?, ?, ?)",
                    (
                        report_id,
                        datetime.now(UTC).isoformat(),
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )

    def get(self, report_id: str) -> dict:
        """Return the stored payload; raises ``V3ReportNotFoundError``."""
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT payload FROM v3_reports WHERE report_id = ?", (report_id,)
                ).fetchone()
        if row is None:
            raise V3ReportNotFoundError(report_id)
        return json.loads(row[0])

    def delete(self, report_id: str) -> bool:
        """Delete a report.  Returns ``True`` if it existed."""
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute("DELETE FROM v3_reports WHERE report_id = ?", (report_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                row = conn.execute("SELECT COUNT(*) FROM v3_reports").fetchone()
            return int(row[0]) if row else 0

    def list_ids(self) -> tuple[str, ...]:
        """Return all stored report IDs, most recent first."""
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT report_id FROM v3_reports ORDER BY generated_at DESC"
                ).fetchall()
            return tuple(row[0] for row in rows)

    def prune_old(self, max_age_seconds: float) -> int:
        """Remove reports older than *max_age_seconds*.  Returns removed count."""
        cutoff = time.time() - max_age_seconds
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM v3_reports WHERE generated_at < ?",
                    (datetime.fromtimestamp(cutoff, tz=UTC).isoformat(),),
                )
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        if self._initialised:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
            version = int(row[0]) if row else 0
            for target in range(version + 1, SCHEMA_VERSION + 1):
                for statement in _MIGRATIONS[target - 1]:
                    conn.execute(statement)
                conn.execute(
                    "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
                    (str(target),),
                )
        self._initialised = True

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
