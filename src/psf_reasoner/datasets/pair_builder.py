"""WT–Mutant pairing logic (V3 data pipeline).

Takes candidate measurement records and pairs WT with mutant measurements
for the same protein + ligand + assay type.  Strict pairing prevents
spurious comparisons (different background, different isoforms, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psf_reasoner.datasets.schemas import AssayType, MutationLigandPair, ReviewStatus


@dataclass
class CandidateRecord:
    """A single raw measurement record before pairing."""

    protein_accession: str = ""
    organism: str = ""
    residue_position: int = 0
    wt_residue: str = ""      # WT residue at this position
    observed_residue: str = ""  # what was actually measured (WT or mutant)
    ligand_id: str = ""
    assay_type: AssayType = AssayType.OTHER
    value: float = 0.0
    unit: str = ""
    temperature_kelvin: float | None = None
    ph: float | None = None
    pmid: str = ""
    is_wt: bool = True
    pdb_id: str = ""
    chain: str = ""


@dataclass
class PairingResult:
    """Result of one WT–mutant pairing attempt."""

    sample: MutationLigandPair
    pair_quality: str = ""  # "exact_match", "conditions_differ", "incomplete"
    issues: list[str] = field(default_factory=list)


def build_pairs(
    candidates: list[CandidateRecord],
    strict_conditions: bool = True,
) -> list[PairingResult]:
    """Build WT–mutant pairs from candidate records.

    Pairing criteria (all must be satisfied):
    1. Same protein_accession
    2. Same ligand_id
    3. Same assay_type
    4. Same residue_position
    5. One WT record + one mutant record at that position
    6. Same organism (if strict_conditions)
    7. Compatible temperature (within 5K, if strict_conditions)
    """
    results: list[PairingResult] = []

    # Group candidates by (protein, ligand, assay, position)
    groups: dict[tuple, list[CandidateRecord]] = {}
    for c in candidates:
        key = (c.protein_accession, c.ligand_id, c.assay_type, c.residue_position)
        if key not in groups:
            groups[key] = []
        groups[key].append(c)

    for key, group in groups.items():
        accession, ligand, assay, position = key
        wt_records = [c for c in group if c.is_wt]
        mut_records = [c for c in group if not c.is_wt]

        if not wt_records or not mut_records:
            continue  # need both WT and mutant

        for wt in wt_records:
            for mut in mut_records:
                if wt.observed_residue == mut.observed_residue:
                    continue  # same residue = not a mutation

                issues = []
                quality = "exact_match"

                # Check organism
                if strict_conditions and wt.organism != mut.organism:
                    issues.append(f"organism mismatch: {wt.organism} vs {mut.organism}")
                    quality = "conditions_differ"

                # Check temperature
                if strict_conditions and wt.temperature_kelvin and mut.temperature_kelvin:
                    if abs(wt.temperature_kelvin - mut.temperature_kelvin) > 5:
                        issues.append(f"temperature differs: {wt.temperature_kelvin}K vs {mut.temperature_kelvin}K")
                        quality = "conditions_differ"

                # Check unit match
                if wt.unit.lower() != mut.unit.lower():
                    issues.append(f"unit mismatch: {wt.unit} vs {mut.unit}")
                    quality = "conditions_differ"

                sample = MutationLigandPair(
                    sample_id=f"{accession}_{wt.observed_residue}{position}{mut.observed_residue}_{ligand}",
                    protein_accession=accession,
                    organism=wt.organism,
                    mutation_notation=f"{wt.observed_residue}{position}{mut.observed_residue}",
                    wt_residue=wt.observed_residue,
                    mutant_residue=mut.observed_residue,
                    uniprot_position=position,
                    ligand_id=ligand,
                    assay_type=assay,
                    wt_value=wt.value,
                    mutant_value=mut.value,
                    value_unit=wt.unit,
                    temperature_kelvin=wt.temperature_kelvin,
                    wt_pdb=wt.pdb_id,
                    mutant_pdb=mut.pdb_id,
                    pmid=wt.pmid,
                    data_source="paired_from_candidates",
                    split_group=accession,
                )

                results.append(PairingResult(sample=sample, pair_quality=quality, issues=issues))

    return results
