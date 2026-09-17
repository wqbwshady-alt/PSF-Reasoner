"""V3 prediction task and benchmark system definitions (P0).

Establishes the first calibrated prediction target and the protein
systems for the pilot benchmark, before any training begins.
"""

from enum import StrEnum

from psf_reasoner.schemas.common import ScientificModel


class PredictionTask(StrEnum):
    """The specific physical quantity V3 aims to predict (P0 definition).

    We start with ONE task to keep scope manageable.  Drug resistance
    is downstream — it depends on catalytic activity retention, protein
    expression, cellular context, and drug exposure, none of which are
    captured by the current physical evidence layer.
    """

    BINDING_AFFINITY_CHANGE = "binding_affinity_change"
    # Future tasks:
    # CATALYTIC_ACTIVITY_CHANGE = "catalytic_activity_change"
    # RESISTANCE_FOLD_CHANGE = "resistance_fold_change"


class TargetLabel(StrEnum):
    """Standardised experimental quantities for binding affinity change."""

    DDG_BINDING = "ddG_binding"  # ΔΔG in kcal/mol
    LOG_KD_FOLD_CHANGE = "log_Kd_fold_change"  # log10(Kd_mutant / Kd_WT)
    LOG_KI_FOLD_CHANGE = "log_Ki_fold_change"  # log10(Ki_mutant / Ki_WT)


class BenchmarkSystem(StrEnum):
    """Pilot benchmark protein systems for V3 calibration (P0).

    These three systems were chosen because:
    - Each has well-characterised resistance mutations with published ΔΔG or Ki data
    - Multiple high-resolution WT and mutant structures exist in the PDB
    - They cover different protein families and chemical mechanisms
    - They are small enough for rapid iteration during development
    """

    HIV_PROTEASE = "HIV-1_protease"
    DHFR = "human_DHFR"
    BETA_LACTAMASE = "TEM-1_beta-lactamase"


class BenchmarkSampleSpec(ScientificModel):
    """Schema for one labelled benchmark sample (P0 contract).

    Every sample in the pilot benchmark must satisfy this schema before
    entering the training pipeline.
    """

    sample_id: str
    protein: str
    organism: str
    uniprot_accession: str | None = None

    # Structure references
    wt_pdb_id: str
    mutant_pdb_id: str | None = None  # None if mutant is modelled
    mutant_modelled: bool = False

    # Mutation
    mutation_notation: str  # e.g. "V82A"
    mutation_chain: str

    # Ligand
    ligand_identifier: str  # 3-letter PDB code

    # Experimental label
    target_label: TargetLabel
    experimental_value: float
    experimental_unit: str
    experimental_condition: str  # pH, temperature, buffer, etc.

    # Data provenance
    literature_source: str  # PMID or DOI
    data_quality: str = "curated"  # curated | reported | inferred
    notes: str | None = None

    # Split key — ensures protein-level splitting for evaluation
    split_group: str  # e.g. "HIV-1_protease", "DHFR", ...


# ---------------------------------------------------------------------------
# P0 completion criteria for the benchmark
# ---------------------------------------------------------------------------

BENCHMARK_PILOT_MINIMUM = 100  # minimum samples for pilot
BENCHMARK_PILOT_TARGET = 300  # target for pilot completion
BENCHMARK_EXPANDED_TARGET = 1000  # long-term target
