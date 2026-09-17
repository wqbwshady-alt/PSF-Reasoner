"""Background-task API tests: async submission, polling, restart recovery."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.infrastructure.task_repository import (
    TASK_STATUS_QUEUED,
    TaskRecord,
    TaskRepository,
)

REPO_ROOT = Path(__file__).parent.parent

_V82A_PAYLOAD = {
    "structure": {"path": str(REPO_ROOT / "examples/data/1sdt.cif"), "format": "mmcif"},
    "mutant_structure": {"path": str(REPO_ROOT / "examples/data/1sdv.cif"), "format": "mmcif"},
    "ligand": {"identifier": "MK1"},
    "mutation": {"notation": "V82A", "chain": "A"},
}


def _make_app(tmp_path: Path):
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    from psf_reasoner.bootstrap import create_default_runner
    from psf_reasoner.infrastructure.v3_repository import V3ReportRepository

    return create_app(
        create_default_runner(),
        upload_dir=upload_dir,
        v3_store=V3ReportRepository(tmp_path / "reports.db"),
        task_store=TaskRepository(tmp_path / "reports.db"),
    )


def _poll(client: TestClient, task_id: str, timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        view = client.get(f"/tasks/{task_id}").json()
        if view["status"] in ("succeeded", "failed"):
            return view
        time.sleep(0.1)
    raise AssertionError(f"task {task_id} did not finish within {timeout}s: {view}")


def test_async_json_analysis_succeeds_and_exports(tmp_path: Path) -> None:
    with TestClient(_make_app(tmp_path)) as client:
        resp = client.post("/v3/analyze/async", json=_V82A_PAYLOAD)
        assert resp.status_code == 202, resp.text
        task_id = resp.json()["task_id"]
        assert task_id.startswith("task-")

        view = _poll(client, task_id)
        assert view["status"] == "succeeded"
        assert view["stage"] == "export_ready"
        assert view["progress"] == 1.0
        report_id = view["report_id"]
        assert report_id and report_id.startswith("report-")

        # The report is exportable through the regular endpoints.
        exported = client.get(f"/export/{report_id}", params={"format": "json"})
        assert exported.status_code == 200

        # And listed in the recent-tasks view.
        tasks = client.get("/tasks").json()
        assert any(t["task_id"] == task_id for t in tasks["tasks"])


def test_async_upload_analysis_succeeds(tmp_path: Path) -> None:
    with TestClient(_make_app(tmp_path)) as client:
        with (
            open(REPO_ROOT / "examples/data/1sdt.cif", "rb") as f1,
            open(REPO_ROOT / "examples/data/1sdv.cif", "rb") as f2,
        ):
            resp = client.post(
                "/v3/analyze-upload/async",
                files={
                    "reference_file": ("1sdt.cif", f1, "chemical/x-cif"),
                    "mutant_file": ("1sdv.cif", f2, "chemical/x-cif"),
                },
                data={"ligand": "MK1", "mutation": "V82A", "chain": "A"},
            )
        assert resp.status_code == 202, resp.text
        view = _poll(client, resp.json()["task_id"])
        assert view["status"] == "succeeded"


def test_failed_task_keeps_sanitized_error(tmp_path: Path) -> None:
    payload = {
        "structure": {"path": str(tmp_path / "definitely-missing.cif"), "format": "mmcif"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A", "chain": "A"},
    }
    with TestClient(_make_app(tmp_path)) as client:
        task_id = client.post("/v3/analyze/async", json=payload).json()["task_id"]
        view = _poll(client, task_id)
        assert view["status"] == "failed"
        assert view["error"], "failed tasks must carry an error message"
        assert str(tmp_path) not in view["error"], "error must not leak server paths"


def test_queue_cap_rejects_excess_submissions(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    # Pre-fill the store with queued tasks up to the cap.
    store = TaskRepository(tmp_path / "reports.db")
    for i in range(8):
        store.create(
            TaskRecord(
                task_id=f"task-{i:012d}",
                status=TASK_STATUS_QUEUED,
                stage="queued",
                progress=0.0,
                report_id=None,
                error=None,
                request_json="{}",
            )
        )
    with TestClient(app) as client:
        resp = client.post("/v3/analyze/async", json=_V82A_PAYLOAD)
        assert resp.status_code == 429
        assert "queue" in resp.json()["detail"].lower()


def test_restart_marks_stale_running_as_failed(tmp_path: Path) -> None:
    db = tmp_path / "reports.db"
    store = TaskRepository(db)
    store.create(
        TaskRecord(
            task_id="task-stale00001",
            status="running",
            stage="v2_analysis",
            progress=0.3,
            report_id=None,
            error=None,
            request_json="{}",
        )
    )
    cutoff = time.time() - 7200
    aged = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(cutoff))
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "UPDATE tasks SET updated_at = ? WHERE task_id = 'task-stale00001'",
            (aged,),
        )

    with TestClient(_make_app(tmp_path)) as client:
        view = client.get("/tasks/task-stale00001").json()
        assert view["status"] == "failed"
        assert view["error"] == "server restarted during analysis"


def test_sync_endpoints_still_work(tmp_path: Path) -> None:
    """The synchronous endpoints remain as compatibility interfaces."""
    with TestClient(_make_app(tmp_path)) as client:
        resp = client.post("/v3/analyze", json=_V82A_PAYLOAD)
        assert resp.status_code == 200, resp.text


def test_unknown_task_404(tmp_path: Path) -> None:
    with TestClient(_make_app(tmp_path)) as client:
        assert client.get("/tasks/task-000000000000").status_code == 404
