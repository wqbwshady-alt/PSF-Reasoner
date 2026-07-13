"""Cloud compute adapter — offloads heavy science to Cloud Run.

Implements the CloudComputeAdapter protocol from physical/cloud_provider.py.
Local PSF-Reasoner stays lightweight: parse, classify, reason.
Heavy computation runs on Google Cloud Run and returns PhysicalEvidence.
"""

from __future__ import annotations

import os
from pathlib import Path

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

    def coulomb(self, structure: StructureInput) -> tuple[PhysicalEvidence, ...]:
        return self._call("coulomb", structure)

    def _call(
        self, tool: str, structure: StructureInput, params: dict | None = None
    ) -> tuple[PhysicalEvidence, ...]:
        if not self._base_url:
            return ()

        # Read structure and convert to PDB for cloud consumption
        path = Path(structure.path)
        raw = path.read_text()
        pdb_data = _to_pdb(raw)

        body: dict = {"pdb_data": pdb_data}
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


def _to_pdb(text: str) -> str:
    """Convert CIF/mmCIF to minimal PDB if needed; strip ANISOU."""
    stripped = text.lstrip()
    if not stripped.startswith(("data_", "DATA_", "loop_", "LOOP_", "#")):
        return text  # already PDB

    import gemmi

    structure = gemmi.read_structure_string(text)
    pdb = structure.make_minimal_pdb()
    lines = [line for line in pdb.splitlines() if not line.startswith("ANISOU")]
    if lines and not lines[-1].startswith("END"):
        lines.append("END")
    return "\n".join(lines)
