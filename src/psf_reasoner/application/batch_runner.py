"""Batch execution — run multiple analysis cases sequentially."""

from __future__ import annotations

import time

from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.schemas.batch import (
    BatchCase,
    BatchJobResult,
    BatchManifest,
    BatchResult,
)


class BatchRunner:
    """Run a batch of analysis cases sequentially with progress tracking.

    Failed jobs do not abort the batch — errors are collected in the result.
    """

    def __init__(self, runner: AnalysisRunnerProtocol) -> None:
        self._runner = runner

    def run(self, manifest: BatchManifest) -> BatchResult:
        jobs: list[BatchJobResult] = []
        succeeded = 0
        failed = 0

        for case in manifest.cases:
            started = time.monotonic()
            try:
                request = case.to_request()
                report = self._runner.run(request)
                elapsed = round(time.monotonic() - started, 3)
                jobs.append(
                    BatchJobResult(
                        case_id=case.case_id,
                        report_id=report.report_id,
                        status="success",
                        elapsed_seconds=elapsed,
                    )
                )
                succeeded += 1
            except Exception as exc:
                elapsed = round(time.monotonic() - started, 3)
                jobs.append(
                    BatchJobResult(
                        case_id=case.case_id,
                        status="error",
                        error=str(exc),
                        elapsed_seconds=elapsed,
                    )
                )
                failed += 1

        return BatchResult(
            batch_id=manifest.batch_id,
            jobs=tuple(jobs),
            total=len(manifest.cases),
            succeeded=succeeded,
            failed=failed,
        )
