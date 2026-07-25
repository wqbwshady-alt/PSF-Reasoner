"""Benchmark dataset schema and pilot benchmark dataset (V3 P4).

The pilot benchmark provides curated, labeled mutation cases for training
and evaluating calibrated prediction models.  Each sample has:
- Structural references (WT and mutant PDB files)
- Experimental label (ΔΔG, Ki fold-change, or resistance classification)
- Split key for protein-level cross-validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class LabelType(StrEnum):
    """Type of experimental label."""

    DDG_BINDING = "ddG_binding"        # ΔΔG in kcal/mol
    LOG_KI_FOLD = "log_Ki_fold"        # log10(Ki_mutant / Ki_WT)
    RESISTANCE_BINARY = "resistance_binary"  # 0 = sensitive, 1 = resistant
    RESISTANCE_FOLD = "resistance_fold"  # fold-change in IC50/MIC


@dataclass
class BenchmarkSample:
    """One labeled sample in the benchmark."""

    sample_id: str
    protein: str
    protein_family: str
    mutation: str          # e.g. "V82A"
    chain: str
    wt_pdb: str            # filename in examples/data/
    mutant_pdb: str | None = None
    ligand: str = ""       # 3-letter PDB code
    label_type: LabelType = LabelType.RESISTANCE_BINARY
    label_value: float = 0.0
    label_unit: str = ""
    label_direction: str = ""  # "increased", "decreased", "unchanged"
    split_group: str = ""  # protein-level split key
    source: str = ""       # PMID or DOI


# ---------------------------------------------------------------------------
# Pilot benchmark — curated cases
# ---------------------------------------------------------------------------

PILOT_BENCHMARK: list[BenchmarkSample] = [
    # ---- HIV-1 Protease (split_group = "HIV_PROTEASE") ------------------
    BenchmarkSample(
        sample_id="HIV_V82A_MK1",
        protein="HIV-1 Protease", protein_family="aspartyl_protease",
        mutation="V82A", chain="A",
        wt_pdb="1sdt.cif", mutant_pdb="1sdv.cif",
        ligand="MK1",
        label_type=LabelType.RESISTANCE_BINARY, label_value=1.0,
        label_direction="increased",
        split_group="HIV_PROTEASE",
        source="PMID:2548654",
    ),
    BenchmarkSample(
        sample_id="HIV_V82A_DRV",
        protein="HIV-1 Protease", protein_family="aspartyl_protease",
        mutation="V82A", chain="A",
        wt_pdb="1sdt.cif", mutant_pdb="1sdv.cif",
        ligand="DRV",
        label_type=LabelType.LOG_KI_FOLD, label_value=0.70,
        label_unit="log10_fold_Ki", label_direction="increased",
        split_group="HIV_PROTEASE",
        source="PMID:12730686",
    ),
    # ---- DHFR (split_group = "DHFR") ------------------------------------
    BenchmarkSample(
        sample_id="DHFR_L22Y_MTX",
        protein="Human DHFR", protein_family="DHFR",
        mutation="L22Y", chain="A",
        wt_pdb="1U72.pdb", mutant_pdb="1DLS.pdb",
        ligand="MTX",
        label_type=LabelType.RESISTANCE_BINARY, label_value=1.0,
        label_direction="increased",
        split_group="DHFR",
        source="PMID:8345919",
    ),
    # ---- EGFR (split_group = "EGFR") — placeholder for expansion --------
    BenchmarkSample(
        sample_id="EGFR_T790M_IRESSA",
        protein="EGFR Kinase", protein_family="kinase",
        mutation="T790M", chain="A",
        wt_pdb="", mutant_pdb="",
        ligand="IRE",
        label_type=LabelType.RESISTANCE_BINARY, label_value=1.0,
        label_direction="increased",
        split_group="EGFR",
        source="PMID:15118073",
    ),
    # ---- ABL1 (split_group = "ABL1") — placeholder for expansion ---------
    BenchmarkSample(
        sample_id="ABL1_T315I_STI",
        protein="ABL1 Kinase", protein_family="kinase",
        mutation="T315I", chain="A",
        wt_pdb="", mutant_pdb="",
        ligand="STI",
        label_type=LabelType.RESISTANCE_BINARY, label_value=1.0,
        label_direction="increased",
        split_group="ABL1",
        source="PMID:11964322",
    ),
    # ---- TEM-1 β-lactamase (split_group = "BLAC") — placeholder ---------
    BenchmarkSample(
        sample_id="BLAC_S70A_PEN",
        protein="TEM-1 Beta-lactamase", protein_family="beta_lactamase",
        mutation="S70A", chain="A",
        wt_pdb="", mutant_pdb="",
        ligand="PEN",
        label_type=LabelType.RESISTANCE_BINARY, label_value=0.0,
        label_direction="decreased",
        split_group="BLAC",
        source="PMID:2205042",
    ),
]


def get_pilot_benchmark() -> list[BenchmarkSample]:
    """Return the current pilot benchmark dataset."""
    return PILOT_BENCHMARK


def get_samples_by_split(split_key: str) -> list[BenchmarkSample]:
    """Filter benchmark samples by split group."""
    return [s for s in PILOT_BENCHMARK if s.split_group == split_key]
