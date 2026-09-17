"""Single versioned migration registry for the shared SQLite storage.

Every repository that stores data in ``.psf_reasoner/reports.db`` (V3
reports, background tasks, …) shares one ``schema_meta`` version chain
and applies migrations through :func:`ensure_schema`.  Migrations are
append-only and idempotent; never edit a released version.
"""

from __future__ import annotations

import sqlite3

# Highest migration version defined in this registry.
CURRENT_SCHEMA_VERSION = 2

_MIGRATIONS: dict[int, tuple[str, ...]] = {
    # version 1 — V3 analysis payloads
    1: (
        "CREATE TABLE IF NOT EXISTS v3_reports ("
        "  report_id    TEXT PRIMARY KEY,"
        "  generated_at TEXT NOT NULL,"
        "  payload      TEXT NOT NULL"
        ")",
        "CREATE INDEX IF NOT EXISTS idx_v3_reports_generated_at ON v3_reports(generated_at DESC)",
    ),
    # version 2 — background analysis tasks
    2: (
        "CREATE TABLE IF NOT EXISTS tasks ("
        "  task_id      TEXT PRIMARY KEY,"
        "  status       TEXT NOT NULL,"
        "  stage        TEXT NOT NULL,"
        "  progress     REAL NOT NULL,"
        "  report_id    TEXT,"
        "  error        TEXT,"
        "  request_json TEXT NOT NULL,"
        "  created_at   TEXT NOT NULL,"
        "  updated_at   TEXT NOT NULL"
        ")",
        "CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at DESC)",
    ),
}


def ensure_schema(conn: sqlite3.Connection, required_version: int) -> None:
    """Bring *conn*'s schema up to *required_version* (idempotent).

    Uses the shared ``schema_meta`` table as the version ledger.  Callers
    must hold whatever lock protects their connection; this function
    performs no locking itself.
    """
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
    version = int(row[0]) if row else 0
    for target in range(version + 1, required_version + 1):
        statements = _MIGRATIONS.get(target)
        if statements is None:
            raise ValueError(f"no migration defined for schema version {target}")
        for statement in statements:
            conn.execute(statement)
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
            (str(target),),
        )
