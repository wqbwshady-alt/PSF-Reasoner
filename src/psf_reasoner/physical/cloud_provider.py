"""Cloud compute evidence — protocol + provider.

Defines the CloudComputeAdapter protocol that infrastructure adapters
implement.  CloudEvidenceProvider slots into the existing composite
pipeline so cloud results augment local evidence.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Protocol

from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest, StructureInput


class CloudComputeAdapter(Protocol):
    """Send a structure to a remote compute service, get PhysicalEvidence back."""

    def fpocket(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]: ...
    def coulomb(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]: ...


class CloudEvidenceProvider:
    """Collects evidence from cloud compute services."""

    def __init__(self, adapter: CloudComputeAdapter | None = None) -> None:
        self._adapter = adapter

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if self._adapter is None:
            return ()

        items: list[PhysicalEvidence] = []

        with suppress(Exception):
            items.extend(self._adapter.fpocket(request.structure))
        with suppress(Exception):
            items.extend(self._adapter.coulomb(request.structure))

        if request.mutant_structure is not None:
            with suppress(Exception):
                items.extend(self._adapter.fpocket(request.mutant_structure))
            with suppress(Exception):
                items.extend(self._adapter.coulomb(request.mutant_structure))

        return tuple(items)
