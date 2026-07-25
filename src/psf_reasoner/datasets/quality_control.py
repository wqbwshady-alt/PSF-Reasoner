"""Dataset quality control checks (V3 data pipeline).

Runs comprehensive QC on a dataset before it enters training.
Produces a QC report with per-sample and aggregate statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psf_reasoner.datasets.schemas import MutationLigandPair, ReviewStatus


@dataclass
class DatasetQCReport:
    """Quality control report for a calibration dataset."""

    total_samples: int = 0
    accepted: int = 0
    pending: int = 0
    rejected: int = 0
    needs_clarification: int = 0

    # Structure availability
    has_wt_pdb: int = 0
    has_mutant_pdb: int = 0
    has_structure_pair: int = 0

    # Label quality
    has_quantitative_label: int = 0
    has_ddg: int = 0
    has_direction_only: int = 0

    # Data quality
    curated: int = 0
    reported: int = 0
    inferred: int = 0
    unverified: int = 0

    # Issues
    missing_pmid: int = 0
    background_mutation_count: int = 0
    multi_point_mutations: int = 0

    # Protein systems
    protein_systems: dict[str, int] = field(default_factory=dict)
    assay_types: dict[str, int] = field(default_factory=dict)

    # Per-sample issues
    sample_issues: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Dataset QC Report",
            f"==================",
            f"Total: {self.total_samples}",
            f"  Accepted: {self.accepted}  Pending: {self.pending}  Rejected: {self.rejected}",
            f"  With WT PDB: {self.has_wt_pdb}  With mutant PDB: {self.has_mutant_pdb}",
            f"  Structure pairs: {self.has_structure_pair}",
            f"  With ΔΔG: {self.has_ddg}  Quantitative: {self.has_quantitative_label}",
            f"  Missing PMID: {self.missing_pmid}",
            f"  Background mutations: {self.background_mutation_count}",
            f"  Multi-point: {self.multi_point_mutations}",
            f"",
            f"Protein systems:",
        ]
        for protein, count in sorted(self.protein_systems.items()):
            lines.append(f"  {protein}: {count}")
        lines.append(f"")
        lines.append(f"Assay types:")
        for assay, count in sorted(self.assay_types.items()):
            lines.append(f"  {assay}: {count}")
        if self.sample_issues:
            lines.append(f"")
            lines.append(f"Sample issues ({len(self.sample_issues)}):")
            for issue in self.sample_issues[:10]:
                lines.append(f"  {issue['sample_id']}: {issue['issue']}")
        return "\n".join(lines)


def run_dataset_qc(samples: list[MutationLigandPair]) -> DatasetQCReport:
    """Run comprehensive QC on a dataset."""
    report = DatasetQCReport(total_samples=len(samples))

    proteins: dict[str, int] = {}
    assays: dict[str, int] = {}

    for s in samples:
        # Review status
        if s.review_status == ReviewStatus.ACCEPTED:
            report.accepted += 1
        elif s.review_status == ReviewStatus.REJECTED:
            report.rejected += 1
        elif s.review_status == ReviewStatus.NEEDS_CLARIFICATION:
            report.needs_clarification += 1
        else:
            report.pending += 1

        # Structures
        if s.wt_pdb:
            report.has_wt_pdb += 1
        if s.mutant_pdb:
            report.has_mutant_pdb += 1
        if s.has_structure_pair:
            report.has_structure_pair += 1

        # Labels
        if s.delta_delta_g is not None:
            report.has_ddg += 1
        if s.wt_value is not None and s.mutant_value is not None:
            report.has_quantitative_label += 1

        # Data quality
        quality = s.data_quality.value
        if quality == "curated":
            report.curated += 1
        elif quality == "reported":
            report.reported += 1
        elif quality == "inferred":
            report.inferred += 1
        else:
            report.unverified += 1

        # Issues
        if not s.pmid and not s.doi:
            report.missing_pmid += 1
        if s.background_mutations:
            report.background_mutation_count += len(s.background_mutations)
        if "/" in s.mutation_notation or "+" in s.mutation_notation:
            report.multi_point_mutations += 1

        # Protein systems
        key = s.protein_name or s.protein_accession or "unknown"
        proteins[key] = proteins.get(key, 0) + 1

        # Assay types
        assay_key = s.assay_type.value
        assays[assay_key] = assays.get(assay_key, 0) + 1

        # Per-sample validation errors
        errors = s.validate_basic()
        for err in errors:
            report.sample_issues.append({"sample_id": s.sample_id, "issue": err})

    report.protein_systems = proteins
    report.assay_types = assays
    return report
