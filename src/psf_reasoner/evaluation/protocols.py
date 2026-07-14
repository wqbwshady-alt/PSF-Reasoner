"""Evaluation protocols — benchmark case schema and dataset contracts.

The ``BenchmarkCase`` model separates functional outcome (Ki/Kd/IC50) from
mechanism label (expert-curated structural mechanism).  Experimental affinity
data does NOT automatically prove any particular structural mechanism.
"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from psf_reasoner.schemas.common import ScientificModel


class ExpectedInteractionChange(ScientificModel):
    """Maps a mechanism label to expected changes in interaction counts.

    Bridges the gap between natural-language mechanism labels
    (e.g. \"loss of hydrophobic packing\") and programmable comparison
    against observed PSF/PLIP interaction deltas.
    """

    interaction_type: str  # "hydrogen_bond", "hydrophobic_contact", etc.
    expected_direction: str  # "increase", "decrease", "unchanged"
    confidence: float = 0.8


class BenchmarkCase(ScientificModel):
    """A single benchmark case capturing both functional outcome and mechanism label.

    Functional outcome and mechanism label are **separate** fields.
    A mutation's effect on binding affinity (Ki/Kd/IC50/fold-change) does not
    automatically identify the structural mechanism — multiple distinct
    mechanisms can produce the same functional direction.
    """

    # --- Identity ---
    case_id: str
    protein_family: str
    protein_uniprot: str | None = None

    # --- WT structure ---
    wt_pdb_id: str
    wt_chain: str
    wt_mutation_background: list[str] = Field(default_factory=list)

    # --- Mutant structure ---
    mutant_pdb_id: str | None = None
    mutant_source: str = "unknown"  # "experimental" | "modelled" | "unknown"
    mutation_notation: str
    mutation_chain: str

    # --- Ligand ---
    ligand_identifier: str
    ligand_chain: str | None = None

    # --- Functional outcome (experimental) ---
    assay_type: str  # e.g. "IC50", "Ki", "Kd", "fold_change"
    assay_conditions: str  # pH, temperature, buffer
    wt_value: float | None = None
    wt_unit: str
    mutant_value: float | None = None
    mutant_unit: str  # must match wt_unit
    fold_change: float | None = None  # computed or reported
    direction: str  # "increase" | "decrease" | "unchanged"
    phenotype: str  # e.g. "drug_resistance", "activity_loss"

    # --- Literature provenance ---
    pmid: str
    doi: str | None = None
    source_table_or_figure: str  # e.g. "Table 2, row 3"
    notes: str = ""

    # --- Mechanism label (separate from functional outcome) ---
    mechanism_label: str | None = None
    mechanism_evidence: str = "none"
    # "literature" | "structural_analysis" | "expert_review" | "none"
    mechanism_source: str | None = None  # e.g. "PMID:12345678, Figure 4"
    mechanism_review_status: str = "unreviewed"
    # "unreviewed" | "single_reviewer" | "consensus"
    mechanism_confidence: float = 0.0  # curator's confidence in this label

    # --- Exclusion flags ---
    excluded_from_calibration: bool = False
    exclusion_reason: str | None = None

    # --- Expected interaction changes (mechanism → interaction bridge) ---
    # TODO: populate from literature/structural analysis for each case
    expected_interaction_changes: tuple[ExpectedInteractionChange, ...] = ()

    # --- Split assignment (set by benchmark freeze) ---
    split: str = "development"  # "development" | "held_out"


class BenchmarkDataset(ScientificModel):
    """A frozen, versioned benchmark dataset."""

    benchmark_id: str
    version: str
    description: str = ""
    frozen_date: date | None = None
    split_strategy: str = "mutation-level"
    split_note: str = ""
    cases: tuple[BenchmarkCase, ...] = ()

    @property
    def development_set(self) -> tuple[BenchmarkCase, ...]:
        return tuple(c for c in self.cases if c.split == "development")

    @property
    def held_out_set(self) -> tuple[BenchmarkCase, ...]:
        return tuple(c for c in self.cases if c.split == "held_out")

    @property
    def calibration_ready(self) -> tuple[BenchmarkCase, ...]:
        return tuple(
            c for c in self.cases
            if not c.excluded_from_calibration and c.mechanism_label is not None
        )
