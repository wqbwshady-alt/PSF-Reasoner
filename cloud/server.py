"""Cloud Run service — scientific computation tools behind a REST API.

POST /compute/{tool}  →  FPocket/Coulomb  →  PhysicalEvidence[]

Security posture (see SECURITY.md):
- /health is public; /compute/* requires X-API-Key == PSF_CLOUD_SECRET
  and fails closed (503) when no secret is configured.
- Request bodies are capped at MAX_BODY_BYTES and pdb_data at
  MAX_PDB_DATA_CHARS; structure text is gemmi-validated before use.
- A per-client-IP token bucket rate-limits compute requests.  Each
  instance keeps its own counters, so this is defense in depth behind
  a load balancer, not a hard global limit.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import gemmi
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

CLOUD_API_SECRET = os.environ.get("PSF_CLOUD_SECRET")
MAX_BODY_BYTES = 50 * 1024 * 1024
MAX_PDB_DATA_CHARS = 18_000_000


class CloudComputeRequest(BaseModel):
    pdb_data: str = Field(max_length=MAX_PDB_DATA_CHARS)
    params: dict = Field(default_factory=dict)


class CloudEvidenceItem(BaseModel):
    id: str  # noqa: A003
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


app = FastAPI(title="PSF Cloud Compute", version="0.4.0")
FPOCKET_AVAILABLE = shutil.which("fpocket") is not None


def _verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require a matching API key; fail closed when no secret is configured."""
    if not CLOUD_API_SECRET:
        raise HTTPException(
            503, "PSF_CLOUD_SECRET not configured — compute endpoints are disabled"
        )
    if x_api_key != CLOUD_API_SECRET:
        raise HTTPException(401, "unauthorized")


class _BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than MAX_BODY_BYTES before they are read."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)


class _RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client-IP token bucket over /compute/*.

    Defense in depth: Cloud Run scales to multiple instances, each with
    its own counters, so this bounds abuse per instance rather than
    globally.  See SECURITY.md.
    """

    def __init__(self, app, *, capacity: int, refill_per_second: float) -> None:
        super().__init__(app)
        self._capacity = capacity
        self._refill = refill_per_second
        self._buckets: dict[str, tuple[float, float]] = {}

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/compute/"):
            return await call_next(request)
        client = _client_ip(request)
        now = time.monotonic()
        tokens, last = self._buckets.get(client, (float(self._capacity), now))
        tokens = min(self._capacity, tokens + (now - last) * self._refill)
        if tokens < 1.0:
            self._buckets[client] = (tokens, now)
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        self._buckets[client] = (tokens - 1.0, now)
        return await call_next(request)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Cloud Run injects this header; take the left-most (client) address.
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


app.add_middleware(_BodyLimitMiddleware)
app.add_middleware(
    _RateLimitMiddleware,
    capacity=int(os.environ.get("PSF_RATE_LIMIT_BURST", "30")),
    refill_per_second=float(os.environ.get("PSF_RATE_LIMIT_RPS", "5")),
)


@app.get("/health")
def health() -> dict:
    tools = []
    if FPOCKET_AVAILABLE:
        tools.append("fpocket")
    tools.append("coulomb")
    return {"status": "ok", "tools": tools}


# ============================================================================
# FPocket
# ============================================================================


@app.post("/compute/fpocket", dependencies=[Depends(_verify_api_key)])
def compute_fpocket(req: CloudComputeRequest) -> list[CloudEvidenceItem]:
    if not FPOCKET_AVAILABLE:
        raise HTTPException(501, "fpocket not installed")

    work_dir = Path(tempfile.mkdtemp(prefix="fpocket_"))
    run_id = uuid.uuid4().hex[:12]
    pdb_path = _resolve_pdb(req, work_dir)

    try:
        result = subprocess.run(
            ["fpocket", "-f", str(pdb_path), "-o", str(work_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(422, f"fpocket failed: {result.stderr[:500]}")
        pockets = _parse_fpocket_output(work_dir, pdb_path.stem)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "fpocket timed out")
    finally:
        _rmtree_safe(work_dir)

    return [
        _make_evidence(
            run_id=f"cloud_fpocket-{run_id}",
            title="FPocket cavity analysis",
            description=(
                f"Detected {pockets['num_pockets']} pockets. "
                f"Largest volume: {pockets['max_volume']:.1f} A3. "
                f"Druggability: {pockets['max_druggability_score']:.2f}."
            ),
            evidence_type="pocket_geometry",
            measurement={"name": "pocket_volume", "value": pockets["max_volume"], "unit": "angstrom3"},
            confidence=0.92,
            provenance=[
                {"kind": "computation", "source": "FPocket (Cloud Run)", "method": "Voronoi cavity detection"}
            ],
            limits=["Fixed probe radius; shallow pockets may be missed.", "Druggability score is heuristic."],
        )
    ]


# ============================================================================
# Coulombic electrostatics
# ============================================================================

# AMBER ff99 partial charges
_BB = {"N": -0.4157, "H": 0.2719, "CA": 0.0337, "HA": 0.0823, "C": 0.5973, "O": -0.5679}
_SC: dict[str, dict[str, float]] = {
    "ALA": {"CB": -0.1825},
    "ARG": {
        "CB": -0.1943,
        "CG": -0.0358,
        "CD": 0.0486,
        "NE": -0.5295,
        "CZ": 0.8076,
        "NH1": -0.8627,
        "NH2": -0.8627,
    },
    "ASN": {"CB": -0.2081, "CG": 0.7137, "OD1": -0.5932, "ND2": -0.9191},
    "ASP": {"CB": -0.2169, "CG": 0.8002, "OD1": -0.8105, "OD2": -0.8105},
    "CYS": {"CB": -0.2904, "SG": -0.3031},
    "GLN": {"CB": -0.2030, "CG": -0.0031, "CD": 0.6320, "OE1": -0.5679, "NE2": -0.9407},
    "GLU": {"CB": -0.2117, "CG": 0.0352, "CD": 0.7928, "OE1": -0.8105, "OE2": -0.8105},
    "GLY": {},
    "HIS": {"CB": -0.1513, "CG": -0.0399, "ND1": -0.5058, "CD2": -0.1335, "CE1": 0.2223, "NE2": -0.5435},
    "ILE": {"CB": 0.0183, "CG1": -0.0769, "CG2": -0.1049, "CD1": -0.1488},
    "LEU": {"CB": -0.2088, "CG": 0.0603, "CD1": -0.1114, "CD2": -0.1114},
    "LYS": {"CB": -0.2009, "CG": -0.0022, "CD": -0.0628, "CE": 0.1244, "NZ": -0.3853},
    "MET": {"CB": -0.1748, "CG": 0.1010, "SD": -0.3013, "CE": -0.0491},
    "PHE": {
        "CB": -0.1994,
        "CG": 0.0645,
        "CD1": -0.1437,
        "CE1": -0.0912,
        "CZ": -0.1066,
        "CD2": -0.1437,
        "CE2": -0.0912,
    },
    "PRO": {"CB": -0.1433, "CG": -0.0453, "CD": -0.0171},
    "SER": {"CB": 0.0159, "OG": -0.5778},
    "THR": {"CB": 0.2039, "OG1": -0.5839, "CG2": -0.2091},
    "TRP": {
        "CB": -0.1973,
        "CG": 0.0823,
        "CD1": -0.0490,
        "NE1": -0.4389,
        "CE2": 0.0358,
        "CD2": -0.1672,
        "CE3": -0.1013,
        "CZ3": -0.0847,
        "CH2": -0.0833,
        "CZ2": -0.1351,
    },
    "TYR": {
        "CB": -0.1962,
        "CG": 0.0923,
        "CD1": -0.1482,
        "CE1": -0.1041,
        "CZ": 0.1215,
        "OH": -0.5563,
        "CD2": -0.1482,
        "CE2": -0.1041,
    },
    "VAL": {"CB": 0.0390, "CG1": -0.1106, "CG2": -0.1106},
}
_STANDARD_RESIDUES = frozenset(_SC) | {"HOH", "WAT", "DOD", "NA", "CL", "MG", "CA", "ZN", "MN", "K"}
_LIG_CHARGE = {
    "O": -0.45,
    "N": -0.30,
    "S": -0.20,
    "C": 0.05,
    "P": 0.15,
    "F": -0.20,
    "CL": -0.20,
    "BR": -0.15,
    "I": -0.10,
}


@app.post("/compute/coulomb", dependencies=[Depends(_verify_api_key)])
def compute_coulomb(req: CloudComputeRequest) -> list[CloudEvidenceItem]:
    """Coulombic ligand-protein electrostatic interaction energy (AMBER charges)."""
    run_id = uuid.uuid4().hex[:12]
    work_dir = Path(tempfile.mkdtemp(prefix="coulomb_"))
    pdb_path = _resolve_pdb(req, work_dir)

    try:
        structure = gemmi.read_structure(str(pdb_path))
        model = structure[0]

        ligand_atoms, protein_atoms = [], []
        for chain in model:
            for residue in chain:
                is_lig = residue.name.upper() not in _STANDARD_RESIDUES
                for atom in residue:
                    if atom.element.name.upper() in {"H", "D"}:
                        continue
                    pos = atom.pos
                    entry = (pos.x, pos.y, pos.z, atom.element.name.upper(), residue.name, atom.name.strip())
                    if is_lig:
                        ligand_atoms.append(entry)
                    else:
                        q = _BB.get(atom.name.strip()) or _SC.get(residue.name, {}).get(atom.name.strip())
                        protein_atoms.append((*entry, q))

        total_e = 0.0
        n_pairs = 0
        for lx, ly, lz, lelem, lres, latom in ligand_atoms:
            lq = _LIG_CHARGE.get(lelem, 0.0)
            for px, py, pz, pelem, pres, patom, pq in protein_atoms:
                if pq is None:
                    continue
                r = math.sqrt((lx - px) ** 2 + (ly - py) ** 2 + (lz - pz) ** 2)
                if r < 1.5 or r > 12.0:
                    continue
                total_e += 332.0637 * lq * pq / (4.0 * r * r)  # kcal/mol
                n_pairs += 1
        energy_kj = total_e * 4.184
    finally:
        _rmtree_safe(work_dir)

    return [
        _make_evidence(
            run_id=f"cloud_coulomb-{run_id}",
            title="Coulombic ligand-protein interaction energy",
            description=(
                f"Electrostatic energy: {energy_kj:.1f} kJ/mol ({total_e:.1f} kcal/mol) "
                f"over {n_pairs} atom pairs. AMBER ff99 charges, ε=4r. "
                "Negative = favorable."
            ),
            evidence_type="energy_component",
            measurement={"name": "coulomb_energy", "value": round(energy_kj, 1), "unit": "kJ_per_mol"},
            confidence=0.82,
            provenance=[
                {"kind": "computation", "source": "Coulomb (Cloud Run)", "method": "AMBER ff99, ε=4r"}
            ],
            limits=[
                "Ligand charges from element type.",
                "ε=4r is crude implicit solvent.",
                "Single structure only.",
            ],
        )
    ]


# ============================================================================
# Helpers
# ============================================================================


def _resolve_pdb(req: CloudComputeRequest, work_dir: Path) -> Path:
    """Write *req.pdb_data* to a work-directory PDB file, converting CIF→PDB.

    The data is gemmi-validated first so garbage never reaches the
    compute engines (fpocket's parser included).  Error messages never
    contain server paths or input content.
    """
    pdb_path = work_dir / "input.pdb"
    raw = req.pdb_data
    if raw.lstrip().startswith(("data_", "DATA_", "loop_", "LOOP_", "#")):
        try:
            struct = gemmi.read_structure_string(raw)
        except Exception as exc:
            raise HTTPException(
                422, f"structure data cannot be parsed: {type(exc).__name__}"
            ) from exc
        _require_atoms(struct)
        raw = struct.make_minimal_pdb()
        lines = [l for l in raw.splitlines() if not l.startswith("ANISOU")]
        if lines and not lines[-1].startswith("END"):
            lines.append("END")
        raw = "\n".join(lines)
    else:
        try:
            struct = gemmi.read_structure_string(raw)
        except Exception as exc:
            raise HTTPException(
                422, f"structure data cannot be parsed: {type(exc).__name__}"
            ) from exc
        _require_atoms(struct)
    pdb_path.write_text(raw)
    return pdb_path


def _require_atoms(structure) -> None:
    """Reject structures gemmi accepts leniently but that contain no atoms."""
    atom_count = sum(
        1
        for model in structure
        for chain in model
        for residue in chain
        for _ in residue
    )
    if atom_count == 0:
        raise HTTPException(422, "structure data contains no atoms")


def _make_evidence(
    run_id, title, description, evidence_type, measurement, confidence, provenance, limits
) -> CloudEvidenceItem:
    return CloudEvidenceItem(
        id=run_id,
        title=title,
        description=description,
        evidence_type=evidence_type,
        measurement=measurement,
        confidence=confidence,
        provenance=provenance,
        limitations=limits,
    )


def _parse_fpocket_output(work_dir: Path, stem: str) -> dict:
    info_files = sorted(work_dir.rglob(f"{stem}_out/*_info.txt"))
    pockets_data = _parse_pocket_info(info_files)
    n = len(pockets_data)
    vols = [p.get("volume", 0) for p in pockets_data]
    scores = [p.get("druggability_score", 0) for p in pockets_data]
    return {
        "num_pockets": n,
        "max_volume": max(vols) if vols else 0,
        "max_druggability_score": max(scores) if scores else 0,
        "pockets": pockets_data,
    }


def _parse_pocket_info(info_files: list[Path]) -> list[dict]:
    pockets = []
    for f in info_files:
        pkt = {}
        try:
            for line in f.read_text().splitlines():
                line = line.strip()
                if "Volume" in line:
                    try:
                        pkt["volume"] = float(line.split()[-1])
                    except Exception:
                        pass
                elif "Druggability Score" in line:
                    try:
                        pkt["druggability_score"] = float(line.split(":")[-1].strip())
                    except Exception:
                        pass
            if pkt:
                pockets.append(pkt)
        except Exception:
            continue
    return pockets


def _rmtree_safe(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except Exception:
        pass
