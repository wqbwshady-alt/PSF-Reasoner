"""Background-task storage tests (SQLite, shared migration chain)."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from psf_reasoner.infrastructure.task_repository import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCEEDED,
    TaskNotFoundError,
    TaskRecord,
    TaskRepository,
)


def _record(task_id: str = "task-aaaaaaaaaaaa", **overrides) -> TaskRecord:
    fields = {
        "task_id": task_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0.0,
        "report_id": None,
        "error": None,
        "request_json": "{}",
    }
    fields.update(overrides)
    return TaskRecord(**fields)


class TestTaskRepository:
    def test_create_and_get(self, tmp_path: Path) -> None:
        repo = TaskRepository(tmp_path / "reports.db")
        repo.create(_record())
        fetched = repo.get("task-aaaaaaaaaaaa")
        assert fetched.status == "queued"
        assert fetched.progress == 0.0

    def test_survives_recreation(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        TaskRepository(db).create(_record())
        assert TaskRepository(db).get("task-aaaaaaaaaaaa").status == "queued"

    def test_update_status_and_progress(self, tmp_path: Path) -> None:
        repo = TaskRepository(tmp_path / "reports.db")
        repo.create(_record())
        repo.update("task-aaaaaaaaaaaa", status=TASK_STATUS_RUNNING, stage="v2_analysis", progress=0.4)
        fetched = repo.get("task-aaaaaaaaaaaa")
        assert fetched.status == "running"
        assert fetched.stage == "v2_analysis"
        assert fetched.progress == 0.4

    def test_finish_success_with_report(self, tmp_path: Path) -> None:
        repo = TaskRepository(tmp_path / "reports.db")
        repo.create(_record())
        repo.update(
            "task-aaaaaaaaaaaa",
            status=TASK_STATUS_SUCCEEDED,
            stage="export_ready",
            progress=1.0,
            report_id="report-381a78f31d53",
        )
        fetched = repo.get("task-aaaaaaaaaaaa")
        assert fetched.status == "succeeded"
        assert fetched.report_id == "report-381a78f31d53"

    def test_fail_records_sanitized_error(self, tmp_path: Path) -> None:
        repo = TaskRepository(tmp_path / "reports.db")
        repo.create(_record())
        repo.update("task-aaaaaaaaaaaa", status=TASK_STATUS_FAILED, error="ValueError: boom")
        assert repo.get("task-aaaaaaaaaaaa").status == "failed"
        assert repo.get("task-aaaaaaaaaaaa").error == "ValueError: boom"

    def test_missing_task_raises(self, tmp_path: Path) -> None:
        with pytest.raises(TaskNotFoundError):
            TaskRepository(tmp_path / "reports.db").get("task-missing")

    def test_list_recent(self, tmp_path: Path) -> None:
        repo = TaskRepository(tmp_path / "reports.db")
        repo.create(_record("task-000000000001"))
        repo.create(_record("task-000000000002"))
        ids = [t.task_id for t in repo.list_recent(limit=10)]
        assert "task-000000000001" in ids
        assert "task-000000000002" in ids

    def test_mark_stale_running_as_failed(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        repo = TaskRepository(db)
        repo.create(_record(status=TASK_STATUS_RUNNING))
        # Age the task past the stale threshold.
        cutoff = time.time() - 7200
        aged = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(cutoff))
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
                (aged, "task-aaaaaaaaaaaa"),
            )
        marked = repo.mark_stale_running(max_running_seconds=3600)
        assert marked == 1
        fetched = repo.get("task-aaaaaaaaaaaa")
        assert fetched.status == "failed"
        assert fetched.error == "server restarted during analysis"

    def test_prune_old_finished(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        repo = TaskRepository(db)
        repo.create(_record("task-000000000001", status=TASK_STATUS_SUCCEEDED))
        repo.create(_record("task-000000000002"))
        cutoff = time.time() - 48 * 3600
        aged = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(cutoff))
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "UPDATE tasks SET updated_at = ? WHERE task_id = 'task-000000000001'",
                (aged,),
            )
        assert repo.prune_old_finished(max_age_seconds=3600) == 1
        with pytest.raises(TaskNotFoundError):
            repo.get("task-000000000001")
        assert repo.get("task-000000000002").status == "queued"

    def test_schema_version_two_recorded(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        TaskRepository(db).create(_record())
        TaskRepository(db)  # idempotent re-open
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
        assert row and int(row[0]) >= 2
