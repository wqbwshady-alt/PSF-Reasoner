"""In-memory report repository — thread-safe, process-local storage."""

from threading import RLock

from psf_reasoner.application.ports import ReportNotFoundError
from psf_reasoner.schemas.report import PSFReport


class InMemoryReportRepository:
    """Thread-safe in-memory store."""

    def __init__(self) -> None:
        self._reports: dict[str, PSFReport] = {}
        self._lock = RLock()

    def save(self, report: PSFReport) -> None:
        with self._lock:
            self._reports[report.report_id] = report

    def get(self, report_id: str) -> PSFReport:
        with self._lock:
            try:
                return self._reports[report_id]
            except KeyError as error:
                raise ReportNotFoundError(report_id) from error
