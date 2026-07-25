"""Deduplication and background mutation checking (V3 data pipeline).

Ensures that each mutation–ligand pair appears only once in the dataset
and that background mutations are correctly identified.
"""

from __future__ import annotations

from psf_reasoner.datasets.schemas import MutationLigandPair


def deduplicate(samples: list[MutationLigandPair]) -> list[MutationLigandPair]:
    """Remove duplicate samples by (accession, mutation, ligand, assay) key.

    When duplicates exist, prefer:
    1. Samples with structure pairs over those without
    2. Higher review_status (accepted > pending > rejected)
    3. More recent PMID (higher number, crude proxy)
    """
    groups: dict[tuple, list[MutationLigandPair]] = {}
    for s in samples:
        key = (s.protein_accession, s.mutation_notation, s.ligand_id, s.assay_type)
        if key not in groups:
            groups[key] = []
        groups[key].append(s)

    result = []
    for key, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
        else:
            # Sort by quality heuristics
            def score(s: MutationLigandPair) -> int:
                pts = 0
                if s.has_structure_pair: pts += 100
                if s.review_status.value == "accepted": pts += 50
                if s.pmid: pts += min(int(s.pmid) // 100000, 50)
                return pts

            group.sort(key=score, reverse=True)
            best = group[0]
            best.review_notes += f" [deduplicated from {len(group)} records]"
            result.append(best)

    return result


def check_background_mutations(samples: list[MutationLigandPair]) -> list[str]:
    """Flag samples that may have unaccounted background mutations.

    Returns a list of warnings, one per flagged sample.
    """
    warnings = []
    for s in samples:
        if s.background_mutations:
            warnings.append(
                f"{s.sample_id}: has {len(s.background_mutations)} background mutations — "
                f"effect may not be solely from {s.mutation_notation}"
            )
        if s.wt_pdb and s.mutant_pdb and s.wt_pdb == s.mutant_pdb:
            warnings.append(
                f"{s.sample_id}: wt_pdb == mutant_pdb ({s.wt_pdb}) — "
                "may not be a genuine structure pair"
            )
    return warnings


def check_multi_point_mutations(samples: list[MutationLigandPair]) -> list[str]:
    """Flag samples where the mutation notation suggests multiple mutations."""
    warnings = []
    for s in samples:
        notation = s.mutation_notation
        if "/" in notation or "+" in notation:
            warnings.append(
                f"{s.sample_id}: multi-point mutation detected ({notation}) — "
                "exclude from single-point training set"
            )
    return warnings
