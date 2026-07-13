"""Cloud compute evidence — protocol + provider.

Defines the CloudComputeAdapter protocol that infrastructure adapters
implement.  CloudEvidenceProvider slots into the existing composite
pipeline so cloud results augment local evidence.
"""

from __future__ import annotations

from typing import Protocol

from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest, StructureInput


class CloudComputeAdapter(Protocol):
    """Send a structure to a remote compute service, get PhysicalEvidence back.

    Infrastructure adapters (HTTP Cloud Run, local subprocess, etc.)
    implement this protocol.
    """

    def fpocket(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]: ...

    def apbs_electrostatics(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]: ...

    def gromacs_mmgbsa(
        self, reference: StructureInput, mutant: StructureInput
    ) -> tuple[PhysicalEvidence, ...]: ...


class CloudEvidenceProvider:
    """Collects evidence from cloud compute services.

    Registered in the composite provider after local computation so
    cloud results augment (not replace) local evidence.  When no adapter
    is configured the provider is a graceful no-op.
    """

    def __init__(self, adapter: CloudComputeAdapter | None = None) -> None:
        self._adapter = adapter

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if self._adapter is None:
            return ()

        items: list[PhysicalEvidence] = []

        try:
            fpocket_results = self._adapter.fpocket(request.structure)
            items.extend(fpocket_results)
        except Exception:
            pass

        if request.mutant_structure is not None:
            try:
                mutant_results = self._adapter.fpocket(request.mutant_structure)
                items.extend(mutant_results)
            except Exception:
                pass

        return tuple(items)
