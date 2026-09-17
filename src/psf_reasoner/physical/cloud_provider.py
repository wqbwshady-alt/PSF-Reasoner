"""Cloud compute evidence — protocol + provider.

Defines the CloudComputeAdapter protocol that infrastructure adapters
implement.  CloudEvidenceProvider slots into the existing composite
pipeline so cloud results augment local evidence.
"""

from __future__ import annotations

import logging
from typing import Protocol

from psf_reasoner.component_status import ComponentStatus, component_registry
from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest, StructureInput

logger = logging.getLogger(__name__)


class CloudComputeAdapter(Protocol):
    """Send a structure to a remote compute service, get PhysicalEvidence back."""

    def fpocket(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]: ...
    def coulomb(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]: ...


class CloudEvidenceProvider:
    """Collects evidence from cloud compute services.

    Cloud evidence augments local evidence and is never required: a
    failing tool is logged (with the reason, never with structure
    contents) and skipped rather than aborting the analysis.
    """

    def __init__(self, adapter: CloudComputeAdapter | None = None) -> None:
        self._adapter = adapter

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if self._adapter is None:
            return ()

        items: list[PhysicalEvidence] = []

        for tool in ("fpocket", "coulomb"):
            items.extend(self._collect_tool(tool, request.structure))
            if request.mutant_structure is not None:
                items.extend(self._collect_tool(tool, request.mutant_structure))

        return tuple(items)

    def _collect_tool(self, tool: str, structure: StructureInput) -> tuple[PhysicalEvidence, ...]:
        call = getattr(self._adapter, tool)
        try:
            return tuple(call(structure))
        except Exception as exc:
            logger.warning("cloud %s unavailable for this structure: %s", tool, exc)
            component_registry.set(
                ComponentStatus(
                    "cloud_adapter",
                    enabled=True,
                    available=False,
                    implementation="disabled",
                    detail=f"{tool} failed: {type(exc).__name__}",
                )
            )
            return ()
