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
# Pilot benchmark — evidence-audited cases (2026-09-10)
#
# Only samples whose source and label were verified against the cited
# literature are included.  See docs/EVIDENCE-REVIEW.md for the audit.
# ---------------------------------------------------------------------------

PILOT_BENCHMARK: list[BenchmarkSample] = [
    # ---- HIV-1 Protease (split_group = "HIV_PROTEASE") ------------------
    # V82A + indinavir (MK1): 3.3-fold Ki (Mahalingam 2004, Eur J Biochem
    # 271:1516-24, abstract).  log10(3.3) = 0.5185.
    BenchmarkSample(
        sample_id="HIV_V82A_MK1",
        protein="HIV-1 Protease", protein_family="aspartyl_protease",
        mutation="V82A", chain="A",
        wt_pdb="1sdt.cif", mutant_pdb="1sdv.cif",
        ligand="MK1",
        label_type=LabelType.LOG_KI_FOLD, label_value=0.5185,
        label_unit="log10_fold_Ki", label_direction="increased",
        split_group="HIV_PROTEASE",
        source="PMID:15066177",
    ),
    # L90M + indinavir (MK1): 0.16-fold Ki, i.e. increased susceptibility
    # (same paper, same abstract).  log10(0.16) = -0.7959.
    BenchmarkSample(
        sample_id="HIV_L90M_MK1",
        protein="HIV-1 Protease", protein_family="aspartyl_protease",
        mutation="L90M", chain="A",
        wt_pdb="1sdt.cif", mutant_pdb="1sdu.cif",
        ligand="MK1",
        label_type=LabelType.LOG_KI_FOLD, label_value=-0.7959,
        label_unit="log10_fold_Ki", label_direction="decreased",
        split_group="HIV_PROTEASE",
        source="PMID:15066177",
    ),
    # G48V + saquinavir: 86-fold Ki increase (Liu 2008, J Mol Biol
    # 381:102-15, Table 1).  log10(86) = 1.9345.
    BenchmarkSample(
        sample_id="HIV_G48V_SQV",
        protein="HIV-1 Protease", protein_family="aspartyl_protease",
        mutation="G48V", chain="A",
        wt_pdb="", mutant_pdb="",
        ligand="SQV",
        label_type=LabelType.LOG_KI_FOLD, label_value=1.9345,
        label_unit="log10_fold_Ki", label_direction="increased",
        split_group="HIV_PROTEASE",
        source="PMID:18597780",
    ),
    # ---- DHFR (split_group = "DHFR") ------------------------------------
    # L22Y + methotrexate: structure pair 1U72/1DLS verified; direction is
    # resistance (reduced MTX binding); numeric value pending full text.
    BenchmarkSample(
        sample_id="DHFR_L22Y_MTX",
        protein="Human DHFR", protein_family="DHFR",
        mutation="L22Y", chain="A",
        wt_pdb="1U72.pdb", mutant_pdb="1DLS.pdb",
        ligand="MTX",
        label_type=LabelType.RESISTANCE_BINARY, label_value=1.0,
        label_direction="increased",
        split_group="DHFR",
        source="PMID:7890613",
    ),
    # F31R + methotrexate: delta-delta-G 2.1 kcal/mol (Volpato 2009,
    # J Biol Chem 284:20079-89, PMC2740434 Table 2).
    BenchmarkSample(
        sample_id="DHFR_F31R_MTX",
        protein="Human DHFR", protein_family="DHFR",
        mutation="F31R", chain="A",
        wt_pdb="1U72.pdb", mutant_pdb="",
        ligand="MTX",
        label_type=LabelType.DDG_BINDING, label_value=2.1,
        label_unit="kcal/mol", label_direction="increased",
        split_group="DHFR",
        source="PMID:19478082",
    ),
]


def get_pilot_benchmark() -> list[BenchmarkSample]:
    """Return the current pilot benchmark dataset."""
    return PILOT_BENCHMARK


def get_samples_by_split(split_key: str) -> list[BenchmarkSample]:
    """Filter benchmark samples by split group."""
    return [s for s in PILOT_BENCHMARK if s.split_group == split_key]
