"""Ensemble and multi-conformation input schemas (V3 P5a).

Supports uploading multiple PDB conformations, NMR models, or MD snapshots
for ensemble-aware analysis without requiring automated MD.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EnsembleKind(StrEnum):
    """Type of ensemble data."""

    CRYSTAL_PAIR = "crystal_pair"          # WT + mutant crystal structures
    NMR_ENSEMBLE = "nmr_ensemble"          # NMR model ensemble
    MULTI_PDB = "multi_pdb"                # Multiple PDB entries
    MD_SNAPSHOTS = "md_snapshots"           # User-provided MD frames
    RELAXED_MODELS = "relaxed_models"       # Multiple relaxed conformations


@dataclass
class EnsembleMember:
    """One member of a conformational ensemble."""

    member_id: str
    source_path: str      # PDB/mmCIF file path
    model_index: int = 0  # which model in the file
    label: str = ""       # "WT_frame_0", "mutant_relaxed_3", etc.
    role: str = ""        # "reference", "mutant", "replica"


@dataclass
class EnsembleInput:
    """Multi-conformation ensemble input specification."""

    ensemble_id: str
    kind: EnsembleKind
    members: list[EnsembleMember] = field(default_factory=list)
    description: str = ""
    reference_member_id: str = ""  # which member is the canonical reference


@dataclass
class EnsembleDistanceStats:
    """Distance distribution statistics across an ensemble."""

    residue_label: str
    ligand_atom: str
    distances: list[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    contact_fraction: float = 0.0  # fraction of ensemble members within 4Å


@dataclass
class EnsembleContactOccupancy:
    """Contact occupancy across an ensemble.

    A contact is considered 'occupied' if at least one heavy-atom pair
    is within the cutoff distance.  Occupancy is the fraction of ensemble
    members where the contact is present.
    """

    residue_label: str
    ligand_label: str
    cutoff_angstrom: float
    occupancy: float          # 0.0–1.0
    n_present: int
    n_total: int
    mean_distance: float
    distance_std: float


@dataclass
class EnsembleAnalysis:
    """Complete ensemble-level analysis output."""

    ensemble_id: str
    kind: EnsembleKind
    n_members: int
    distance_distributions: list[EnsembleDistanceStats] = field(default_factory=list)
    contact_occupancies: list[EnsembleContactOccupancy] = field(default_factory=list)
    rmsd_between_members: list[dict] = field(default_factory=list)
    convergence_warning: str = ""
    notes: list[str] = field(default_factory=list)
