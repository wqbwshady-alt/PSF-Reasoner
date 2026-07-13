"""Interfaces for replaceable physical calculators."""

from typing import Protocol

from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest


class PhysicalEvidenceProvider(Protocol):
    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]: ...


class CompositeEvidenceProvider:
    def __init__(self, *providers: PhysicalEvidenceProvider) -> None:
        self._providers = providers

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        return tuple(evidence for provider in self._providers for evidence in provider.collect(request))
