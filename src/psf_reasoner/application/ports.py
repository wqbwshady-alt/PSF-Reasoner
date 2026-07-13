"""Application-layer ports — stable interfaces that infrastructure adapters implement.

Domain and delivery code depend on these protocols, never on concrete
infrastructure implementations.  This keeps the core independent of
execution, persistence, and external service choices.
"""

from collections.abc import Callable
from typing import Protocol

from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.report import PSFReport

# ---------------------------------------------------------------------------
# Execution port
# ---------------------------------------------------------------------------

AnalysisHandler = Callable[[AnalysisRequest], PSFReport]


class ExecutionBackend(Protocol):
    """Run an analysis handler synchronously or asynchronously."""

    def execute(self, request: AnalysisRequest, handler: AnalysisHandler) -> PSFReport: ...


# ---------------------------------------------------------------------------
# Report persistence port
# ---------------------------------------------------------------------------


class ReportNotFoundError(LookupError):
    """Raised when a requested report does not exist in the repository."""


class ReportRepository(Protocol):
    """Store and retrieve completed analysis reports."""

    def save(self, report: PSFReport) -> None: ...

    def get(self, report_id: str) -> PSFReport: ...


# ---------------------------------------------------------------------------
# Application exceptions (delivery adapters depend *only* on these)
# ---------------------------------------------------------------------------


class AnalysisError(Exception):
    """Base for errors crossing the application boundary."""


class StructureInputError(AnalysisError):
    """The supplied structure file cannot be parsed or resolved."""


class ReportLookupError(AnalysisError):
    """A requested report was not found."""
