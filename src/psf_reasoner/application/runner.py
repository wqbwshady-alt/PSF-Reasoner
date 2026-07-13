"""Execution and persistence facade used by CLI and API.

AnalysisRunner converts domain-level exceptions into application-level
exceptions so that delivery adapters never depend on physical-layer or
infrastructure-layer error types.
"""

from typing import Protocol

from psf_reasoner.application.ports import (
    ExecutionBackend,
    ReportLookupError,
    ReportNotFoundError,
    ReportRepository,
    StructureInputError,
)
from psf_reasoner.application.service import AnalysisService
from psf_reasoner.physical.structure import StructureAnalysisError
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.report import PSFReport


class AnalysisRunnerProtocol(Protocol):
    def run(self, request: AnalysisRequest) -> PSFReport: ...

    def get_report(self, report_id: str) -> PSFReport: ...


class AnalysisRunner:
    def __init__(
        self,
        service: AnalysisService,
        execution: ExecutionBackend,
        reports: ReportRepository,
    ) -> None:
        self._service = service
        self._execution = execution
        self._reports = reports

    def run(self, request: AnalysisRequest) -> PSFReport:
        try:
            report = self._execution.execute(request, self._service.analyze)
        except StructureAnalysisError as error:
            raise StructureInputError(str(error)) from error
        self._reports.save(report)
        return report

    def get_report(self, report_id: str) -> PSFReport:
        try:
            return self._reports.get(report_id)
        except ReportNotFoundError as error:
            raise ReportLookupError(str(error)) from error
