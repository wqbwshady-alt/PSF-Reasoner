"""Unified MutationLigandPair data schema (V3 calibration pipeline).

This is the canonical data object for training calibrated models.
Every sample must satisfy this schema before entering any training set.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AssayType(StrEnum):
    KI = "Ki"
    KD = "Kd"
    DELTA_G = "DeltaG"
    IC50 = "IC50"
    OTHER = "other"


class EffectDirection(StrEnum):
    AFFINITY_DECREASE = "affinity_decrease"
    APPROX_NEUTRAL = "approximately_neutral"
    AFFINITY_INCREASE = "affinity_increase"
    UNKNOWN = "unknown"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class DataQuality(StrEnum):
    CURATED = "curated"        # manually verified
    REPORTED = "reported"       # from literature, not re-verified
    INFERRED = "inferred"       # derived from related data
    UNVERIFIED = "unverified"   # from automated import


@dataclass
class UnitNormalization:
    """Record of unit conversion for auditability."""

    original_value: float
    original_unit: str
    converted_value: float
    converted_unit: str
    conversion_method: str = ""


@dataclass
class MutationLigandPair:
    """One labeled mutation–ligand pair for calibration training.

    This is the central data object.  Every field that is not yet known
    should be explicitly set to None rather than omitted.
    """

    # -- Identity ----------------------------------------------------------
    sample_id: str = ""
    protein_accession: str = ""       # UniProt accession
    protein_name: str = ""
    organism: str = ""
    mutation_notation: str = ""        # e.g. "V82A"
    wt_residue: str = ""
    mutant_residue: str = ""
    uniprot_position: int | None = None
    pdb_position: int | None = None
    pdb_chain: str = ""

    # -- Ligand ------------------------------------------------------------
    ligand_id: str = ""               # 3-letter PDB code
    ligand_name: str = ""
    ligand_role: str = ""             # "inhibitor", "substrate", "cofactor"

    # -- Experimental label ------------------------------------------------
    assay_type: AssayType = AssayType.OTHER
    wt_value: float | None = None
    mutant_value: float | None = None
    value_unit: str = ""              # "nM", "µM", "kcal/mol", etc.
    temperature_kelvin: float | None = None
    delta_delta_g: float | None = None  # kcal/mol, computed if possible
    effect_direction: EffectDirection = EffectDirection.UNKNOWN

    # -- Structures --------------------------------------------------------
    wt_pdb: str = ""
    mutant_pdb: str = ""
    background_mutations: list[str] = field(default_factory=list)

    # -- Experimental context ----------------------------------------------
    experimental_method: str = ""
    ph: float | None = None
    buffer_conditions: str = ""

    # -- Provenance --------------------------------------------------------
    pmid: str = ""
    doi: str = ""
    data_source: str = ""             # "BindingDB", "ProTherm", "manual", etc.
    data_quality: DataQuality = DataQuality.UNVERIFIED
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_notes: str = ""
    rejection_reason: str = ""

    # -- PSF computed features (populated after structure analysis) --------
    volume_delta: float | None = None
    polarity_change: str = ""
    contact_count_delta: int | None = None
    hbond_donor_gained: bool = False
    hbond_acceptor_gained: bool = False
    aromatic_added: bool = False
    nearest_ligand_distance: float | None = None
    is_catalytic_site: bool = False
    is_ligand_contact: bool = False
    sasa_delta: float | None = None
    relative_sasa_delta: float | None = None
    network_degree_delta: int | None = None
    qc_grade: str = ""

    # -- Feature completeness flags ----------------------------------------
    has_structure_pair: bool = False
    has_computed_features: bool = False
    has_direct_literature: bool = False

    # -- Split key -----------------------------------
    split_group: str = ""  # protein_accession for protein-level split

    def validate_basic(self) -> list[str]:
        """Return list of basic validation errors (empty = valid)."""
        errors = []
        if not self.protein_accession:
            errors.append("missing protein_accession")
        if not self.mutation_notation:
            errors.append("missing mutation_notation")
        if not self.ligand_id:
            errors.append("missing ligand_id")
        if self.assay_type == AssayType.OTHER:
            errors.append("assay_type not specified")
        if self.wt_value is None and self.mutant_value is None:
            errors.append("no experimental values")
        if not self.pmid and not self.doi:
            errors.append("no literature source")
        if self.wt_residue and self.mutant_residue and self.wt_residue == self.mutant_residue:
            errors.append(f"WT and mutant residue are identical: {self.wt_residue}")
        return errors

    def is_paired(self) -> bool:
        """Check if this sample has both WT and mutant values."""
        return self.wt_value is not None and self.mutant_value is not None

    def to_flat_dict(self) -> dict:
        """Export to a flat dict for CSV/JSON review."""
        return {
            "sample_id": self.sample_id,
            "protein": self.protein_name,
            "accession": self.protein_accession,
            "mutation": self.mutation_notation,
            "wt_residue": self.wt_residue,
            "mutant_residue": self.mutant_residue,
            "uniprot_pos": self.uniprot_position,
            "pdb_pos": self.pdb_position,
            "chain": self.pdb_chain,
            "ligand": self.ligand_id,
            "ligand_name": self.ligand_name,
            "assay": self.assay_type.value,
            "wt_value": self.wt_value,
            "mutant_value": self.mutant_value,
            "unit": self.value_unit,
            "ddG": self.delta_delta_g,
            "effect": self.effect_direction.value,
            "wt_pdb": self.wt_pdb,
            "mutant_pdb": self.mutant_pdb,
            "bg_mutations": ";".join(self.background_mutations),
            "method": self.experimental_method,
            "pmid": self.pmid,
            "doi": self.doi,
            "source": self.data_source,
            "quality": self.data_quality.value,
            "review": self.review_status.value,
            "review_notes": self.review_notes,
            "split_group": self.split_group,
        }
