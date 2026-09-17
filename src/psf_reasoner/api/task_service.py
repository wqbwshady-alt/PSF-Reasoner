"""Background-task execution for V3 analyses (lightweight, local).

Analysis runs (structure parsing, V2 evidence, V3 orchestration,
optionally FoldX / cloud / LLM calls) are submitted to a small thread
pool instead of occupying request threads.  Task state is persisted in
the shared SQLite store, so a restart cleanly fails stale ``running``
tasks.  This is intentionally local: no external queue infrastructure
is required, and multi-instance dispatch is out of scope.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from psf_reasoner.api.v3_service import build_v3_payload
from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.infrastructure.task_repository import (
    TASK_STATUS_FAILED,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCEEDED,
    TaskRecord,
    TaskRepository,
    serialize_request,
)
from psf_reasoner.infrastructure.v3_repository import V3ReportRepository
from psf_reasoner.schemas.inputs import AnalysisRequest

logger = logging.getLogger(__name__)

DEFAULT_MAX_QUEUE = 8
DEFAULT_MAX_WORKERS = 2
DEFAULT_TIMEOUT_SECONDS = 600.0
DEFAULT_WATCHDOG_INTERVAL = 30.0


class TaskService:
    """Owns the worker pool and watchdog for background analyses."""

    def __init__(
        self,
        store: TaskRepository,
        runner: AnalysisRunnerProtocol,
        upload_dir: Path,
        v3_store: V3ReportRepository,
        *,
        max_queue: int = DEFAULT_MAX_QUEUE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        watchdog_interval: float = DEFAULT_WATCHDOG_INTERVAL,
    ) -> None:
        self._store = store
        self._runner = runner
        self._upload_dir = upload_dir
        self._v3_store = v3_store
        self._max_queue = max_queue
        self._max_workers = max_workers
        self._timeout_seconds = timeout_seconds
        self._watchdog_interval = watchdog_interval
        self._executor: ThreadPoolExecutor | None = None
        self._watchdog_stop = threading.Event()
        self._watchdog_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the worker pool; fail stale running tasks from prior runs."""
        self._store.mark_stale_running(max_running_seconds=self._timeout_seconds)
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="psf-task")
        self._watchdog_stop.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="psf-task-watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()

    def shutdown(self) -> None:
        """Stop the watchdog and wait briefly for in-flight work."""
        self._watchdog_stop.set()
        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=5.0)
            self._watchdog_thread = None
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=False)
            self._executor = None

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit(self, request: AnalysisRequest, *, stage: str = "queued") -> str:
        """Admit a JSON analysis request; returns the task id (202 semantics).

        Raises ``HTTPException`` 429 when the queue is at capacity.
        """
        self._ensure_started()
        if self._store.count_active() >= self._max_queue:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"analysis queue is full (limit {self._max_queue}); retry later",
            )
        task_id = f"task-{uuid4().hex[:12]}"
        self._store.create(
            TaskRecord(
                task_id=task_id,
                status=TASK_STATUS_QUEUED,
                stage=stage,
                progress=0.0,
                report_id=None,
                error=None,
                request_json=serialize_request(request),
            )
        )
        self._executor.submit(self._run_task, task_id, request)
        return task_id

    def get_view(self, task_id: str) -> dict:
        """Public JSON view of a task (404 for unknown ids)."""
        from psf_reasoner.infrastructure.task_repository import TaskNotFoundError

        try:
            record = self._store.get(task_id)
        except TaskNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found") from error
        return {
            "task_id": record.task_id,
            "status": record.status,
            "stage": record.stage,
            "progress": record.progress,
            "report_id": record.report_id,
            "error": record.error,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def list_views(self, limit: int = 20) -> list[dict]:
        return [
            {
                "task_id": r.task_id,
                "status": r.status,
                "stage": r.stage,
                "progress": r.progress,
                "report_id": r.report_id,
                "updated_at": r.updated_at,
            }
            for r in self._store.list_recent(limit=limit)
        ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_started(self) -> None:
        if self._executor is None:
            self.start()

    def _run_task(self, task_id: str, request: AnalysisRequest) -> None:
        self._store.update(task_id, status=TASK_STATUS_RUNNING, stage="v2_analysis", progress=0.1)

        def progress(stage: str, fraction: float) -> None:
            self._store.update(task_id, status=TASK_STATUS_RUNNING, stage=stage, progress=fraction)

        try:
            payload = build_v3_payload(
                self._runner,
                request,
                self._upload_dir,
                self._v3_store,
                progress=progress,
            )
            self._store.update(
                task_id,
                status=TASK_STATUS_SUCCEEDED,
                stage="export_ready",
                progress=1.0,
                report_id=payload["report_id"],
            )
        except Exception as exc:
            logger.warning("background analysis %s failed: %s", task_id, type(exc).__name__)
            self._store.update(
                task_id,
                status=TASK_STATUS_FAILED,
                stage="failed",
                progress=1.0,
                error=self._sanitize_error(exc),
            )

    def _sanitize_error(self, exc: Exception) -> str:
        """Error text for the task record: type + message, no server paths."""
        text = f"{type(exc).__name__}: {exc}"[:500]
        for secret in (str(self._upload_dir), str(self._upload_dir.resolve())):
            text = text.replace(secret, "<upload_dir>")
        return text

    def _watchdog_loop(self) -> None:
        """Periodically fail running tasks that outlive the timeout.

        Python threads cannot be killed, so an over-long analysis keeps
        running in the background but stops being reported as active.
        """
        while not self._watchdog_stop.wait(self._watchdog_interval):
            try:
                marked = self._store.mark_stale_running(max_running_seconds=self._timeout_seconds)
                if marked:
                    logger.warning("marked %d stale running task(s) as failed", marked)
            except Exception as exc:  # keep the watchdog alive no matter what
                logger.debug("task watchdog pass failed: %s", exc)
