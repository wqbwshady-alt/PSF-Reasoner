"""Cloud Run service — wraps scientific computation tools behind a REST API.

POST /compute/{tool}  →  runs the tool in a subprocess  →  returns PhysicalEvidence[]

Supported tools:
  - fpocket: pocket detection, volume, druggability score
  - apbs:    Poisson-Boltzmann electrostatic potential (future)
  - gromacs: MM-GBSA binding free energy (future)
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schemas (subset of PSF-Reasoner PhysicalEvidence, kept standalone so the
# cloud service has zero dependency on the local PSF-Reasoner package)
# ---------------------------------------------------------------------------


class CloudComputeRequest(BaseModel):
    structure_path: str = Field(..., description="Path to PDB/mmCIF file")
    params: dict = Field(default_factory=dict)


class CloudEvidenceItem(BaseModel):
    id: str
    title: str
    description: str
    evidence_type: str
    status: str = "computed"
    measurement: dict = Field(default_factory=dict)
    confidence: float = 0.90
    provenance: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="PSF Cloud Compute", version="0.1.0")


FPOCKET_AVAILABLE = shutil.which("fpocket") is not None


@app.get("/health")
def health() -> dict:
    tools = []
    if FPOCKET_AVAILABLE:
        tools.append("fpocket")
    return {"status": "ok", "tools": tools}


# ---------------------------------------------------------------------------
# FPocket
# ---------------------------------------------------------------------------


@app.post("/compute/fpocket")
def compute_fpocket(req: CloudComputeRequest) -> list[CloudEvidenceItem]:
    """Run FPocket on the supplied structure."""

    if not FPOCKET_AVAILABLE:
        raise HTTPException(501, "fpocket is not installed on this instance")

    input_path = Path(req.structure_path)
    if not input_path.is_file():
        raise HTTPException(404, f"structure not found: {input_path}")

    work_dir = Path(tempfile.mkdtemp(prefix="fpocket_"))
    run_id = uuid.uuid4().hex[:12]

    try:
        result = subprocess.run(
            ["fpocket", "-f", str(input_path), "-o", str(work_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(422, f"fpocket failed: {result.stderr}")

        pockets = _parse_fpocket_output(work_dir, input_path.stem)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "fpocket timed out after 120s")
    finally:
        _rmtree_safe(work_dir)

    return [CloudEvidenceItem(
        id=f"cloud-fpocket-{run_id}",
        title="FPocket cavity analysis",
        description=f"Detected {pockets.get('num_pockets', 0)} pockets. "
        f"Largest pocket volume: {pockets.get('max_volume', 0):.1f} A3. "
        f"Druggability score: {pockets.get('max_druggability_score', 0):.2f}.",
        evidence_type="pocket_geometry",
        status="computed",
        measurement={
            "name": "pocket_volume",
            "value": pockets.get("max_volume", 0),
            "unit": "angstrom3",
        },
        confidence=0.92,
        provenance=[{
            "kind": "computation",
            "source": "FPocket (Cloud Run)",
            "method": "Voronoi-based cavity detection",
            "parameters": {"input": str(input_path)},
        }],
        limitations=[
            "FPocket uses a fixed probe radius; very shallow pockets may be missed.",
            "Druggability score is a heuristic, not a quantitative affinity measure.",
        ],
    )]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_fpocket_output(work_dir: Path, stem: str) -> dict:
    """Parse FPocket *_info.txt output."""
    info_files = sorted(work_dir.rglob(f"{stem}_out/*_info.txt"))
    pockets_data = _parse_pocket_info(info_files)
    num_pockets = len(pockets_data)
    volumes = [p.get("volume", 0) for p in pockets_data]
    scores = [p.get("druggability_score", 0) for p in pockets_data]
    return {
        "num_pockets": num_pockets,
        "max_volume": max(volumes) if volumes else 0,
        "max_druggability_score": max(scores) if scores else 0,
        "pockets": pockets_data,
    }


def _parse_pocket_info(info_files: list[Path]) -> list[dict]:
    pockets = []
    for info_file in info_files:
        pocket = {}
        try:
            text = info_file.read_text()
            for line in text.splitlines():
                line = line.strip()
                if "Volume" in line:
                    parts = line.split()
                    try:
                        pocket["volume"] = float(parts[-1])
                    except (ValueError, IndexError):
                        pocket["volume"] = 0.0
                elif "Druggability Score" in line:
                    parts = line.split(":")
                    try:
                        pocket["druggability_score"] = float(parts[-1].strip())
                    except (ValueError, IndexError):
                        pocket["druggability_score"] = 0.0
                elif "Score" in line and "Druggability" not in line:
                    parts = line.split(":")
                    try:
                        pocket["score"] = float(parts[-1].strip())
                    except (ValueError, IndexError):
                        pocket["score"] = 0.0
            if pocket:
                pockets.append(pocket)
        except Exception:
            continue
    return pockets


def _rmtree_safe(path: Path) -> None:
    import shutil

    try:
        shutil.rmtree(path)
    except Exception:
        pass
