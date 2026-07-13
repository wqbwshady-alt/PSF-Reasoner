"""Cloud compute adapter — offloads heavy science to Cloud Run.

Implements the CloudComputeAdapter protocol from physical/cloud_provider.py.
Local PSF-Reasoner stays lightweight: parse, classify, reason.
Heavy computation runs on Google Cloud Run and returns PhysicalEvidence.
"""

from __future__ import annotations

import os

import httpx

from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.inputs import StructureInput

_DEFAULT_CLOUD_URL_ENV = "PSF_CLOUD_URL"


class HttpCloudAdapter:
    """Calls a Cloud Run service wrapping FPocket / APBS / GROMACS.

    The cloud service accepts POST /compute/{tool} and returns
    PhysicalEvidence[] as JSON.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 300.0) -> None:
        self._base_url = (base_url or os.environ.get(_DEFAULT_CLOUD_URL_ENV, "")).rstrip("/")
        self._timeout = timeout

    def fpocket(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]:
        return self._call("fpocket", structure)

    def apbs_electrostatics(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]:
        return self._call("apbs", structure)

    def gromacs_mmgbsa(
        self, reference: StructureInput, mutant: StructureInput
    ) -> tuple[PhysicalEvidence, ...]:
        return self._call("gromacs-mmgbsa", reference, params={"mutant_path": mutant.path})

    def _call(
        self, tool: str, structure: StructureInput, params: dict | None = None
    ) -> tuple[PhysicalEvidence, ...]:
        if not self._base_url:
            return ()

        body: dict = {"structure_path": structure.path}
        if params:
            body["params"] = params

        response = httpx.post(
            f"{self._base_url}/compute/{tool}",
            json=body,
            timeout=self._timeout,
        )
        response.raise_for_status()
        items = response.json()
        return tuple(PhysicalEvidence.model_validate(item) for item in items)
