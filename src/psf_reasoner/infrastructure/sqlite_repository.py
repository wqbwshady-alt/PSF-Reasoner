"""SQLite-backed report repository — survives process restarts."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock

from psf_reasoner.application.ports import ReportNotFoundError
from psf_reasoner.schemas.report import PSFReport

_DEFAULT_DB_PATH = ".psf_reasoner/reports.db"


class SqliteReportRepository:
    """Store and retrieve PSFReports in a local SQLite database.

    Each report is stored as a single row with its ``report_id`` as the
    primary key and the full Pydantic model serialised to JSON in a text
    column.  The repository is thread-safe via an ``RLock`` but is
    intended for single-process use.
    """

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._lock = RLock()
        self._init_db()

    # ------------------------------------------------------------------
    # Public API (implements ReportRepository protocol)
    # ------------------------------------------------------------------

    def save(self, report: PSFReport) -> None:
        serialised = report.model_dump_json()
        with self._lock, self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reports(report_id, generated_at, mode, payload) "
                "VALUES (?, ?, ?, ?)",
                (
                    report.report_id,
                    report.generated_at.isoformat(),
                    report.mode.value,
                    serialised,
                ),
            )

    def get(self, report_id: str) -> PSFReport:
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT payload FROM reports WHERE report_id = ?", (report_id,)
            ).fetchone()
        if row is None:
            raise ReportNotFoundError(report_id)
        return PSFReport.model_validate_json(row[0])

    def list_ids(self) -> tuple[str, ...]:
        """Return all stored report IDs, most recent first."""
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                "SELECT report_id FROM reports ORDER BY generated_at DESC"
            ).fetchall()
        return tuple(row[0] for row in rows)

    def delete(self, report_id: str) -> bool:
        """Delete a report.  Returns ``True`` if it existed."""
        with self._lock, self._connection() as conn:
            cursor = conn.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._lock, self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM reports").fetchone()
        return int(row[0]) if row else 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS reports ("
                "  report_id    TEXT PRIMARY KEY,"
                "  generated_at TEXT NOT NULL,"
                "  mode         TEXT NOT NULL,"
                "  payload      TEXT NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reports_generated_at "
                "ON reports(generated_at DESC)"
            )

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
