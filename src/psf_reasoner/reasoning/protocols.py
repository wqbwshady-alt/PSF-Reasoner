"""Framework-neutral reasoning interfaces."""

from typing import Protocol

from psf_reasoner.reasoning.results import ForwardResult, ReverseResult
from psf_reasoner.schemas.consistency import ConsistencyCheck
from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest


class ForwardReasoner(Protocol):
    def reason(
        self,
        request: AnalysisRequest,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> ForwardResult: ...


class ReverseReasoner(Protocol):
    def reason(
        self,
        request: AnalysisRequest,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> ReverseResult: ...


class ConsistencyChecker(Protocol):
    def check(
        self,
        forward: ForwardResult,
        reverse: ReverseResult,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> tuple[ConsistencyCheck, ...]: ...
