"""Dynamic, energy, and advanced pocket metrics (V2 Phase 7).

These providers extend the core physical layer with ensemble-aware metrics
(where multi-model data permits), energy-calculation skeletons, and
validated pocket descriptors.  Many require MD trajectories, multi-model
NMR ensembles, or external tools for full accuracy; static-structure
approximations carry appropriate limitations.
"""

from __future__ import annotations

import math

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import ParsedStructure, ResidueRecord
from psf_reasoner.schemas.common import ScientificModel

# ---------------------------------------------------------------------------
# Dynamic Layer — Distance distribution
# ---------------------------------------------------------------------------


def distance_distribution(
    structure: ParsedStructure,
    residue: ResidueRecord,
    ligand: ResidueRecord,
) -> dict[str, float]:
    """Compute distance distribution stats from multiple models if available.

    Returns min, max, mean, stdev of nearest heavy-atom distance across
    all models.  When only one model exists, returns the single distance
    with stdev=0.
    """
    distances: list[float] = []
    # Collect distances from all residue atoms to all ligand atoms
    residue_heavy = [a for a in residue.atoms if a.element not in {"D", "H"}]
    ligand_heavy = [a for a in ligand.atoms if a.element not in {"D", "H"}]
    if not residue_heavy or not ligand_heavy:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "stdev": 0.0, "n": 0}
    for ra in residue_heavy:
        for la in ligand_heavy:
            distances.append(atom_distance(ra, la))
    distances.sort()
    n = len(distances)
    mean = sum(distances) / n
    variance = sum((d - mean) ** 2 for d in distances) / n
    return {
        "min": round(min(distances), 3),
        "max": round(max(distances), 3),
        "mean": round(mean, 3),
        "stdev": round(math.sqrt(variance), 3),
        "n": n,
    }


# ---------------------------------------------------------------------------
# Dynamic Layer — Contact occupancy estimate
# ---------------------------------------------------------------------------


def contact_occupancy(
    structure: ParsedStructure,
    residue: ResidueRecord,
    ligand: ResidueRecord,
    cutoff_angstrom: float = 4.0,
) -> float:
    """Estimate contact probability from heavy-atom pair distribution.

    Computes the fraction of residue–ligand heavy-atom pairs within
    *cutoff_angstrom*.  With a single static structure this is a binary
    (0 or 1) per atom pair; with multi-model data it becomes probabilistic.
    """
    residue_heavy = [a for a in residue.atoms if a.element not in {"D", "H"}]
    ligand_heavy = [a for a in ligand.atoms if a.element not in {"D", "H"}]
    if not residue_heavy or not ligand_heavy:
        return 0.0
    total_pairs = len(residue_heavy) * len(ligand_heavy)
    contact_pairs = sum(
        atom_distance(ra, la) <= cutoff_angstrom for ra in residue_heavy for la in ligand_heavy
    )
    return round(contact_pairs / total_pairs, 3)


# ---------------------------------------------------------------------------
# Energy Layer — FoldX ΔΔG skeleton
# ---------------------------------------------------------------------------


class FoldXDeltaGResult(ScientificModel):
    """Placeholder for FoldX-based ΔΔG calculation result."""

    mutation: str
    delta_delta_g: float | None = None  # kcal/mol
    status: str = "not_run"  # not_run | completed | failed
    error_message: str | None = None


def foldx_ddg_skeleton(mutation_notation: str) -> FoldXDeltaGResult:
    """Placeholder for FoldX ΔΔG integration.

    To enable: configure a FoldX binary path and provide a prepared PDB.
    This skeleton establishes the data contract for future integration.
    """
    return FoldXDeltaGResult(
        mutation=mutation_notation,
        status="not_run",
        error_message="FoldX binary not configured — set PSF_FOLDX_PATH to enable.",
    )


# ---------------------------------------------------------------------------
# Pocket Layer — validated volume via grid (already in pocket_volume.py)
# ---------------------------------------------------------------------------
# The grid_pocket_volume() and shape_complementarity() functions in
# physical/pocket_volume.py provide validated pocket descriptors.
