"""Inline execution adapter — runs work synchronously in the caller process."""

from psf_reasoner.application.ports import AnalysisHandler
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.report import PSFReport


class InlineExecutionBackend:
    """Run work synchronously in the caller process."""

    def execute(self, request: AnalysisRequest, handler: AnalysisHandler) -> PSFReport:
        return handler(request)
