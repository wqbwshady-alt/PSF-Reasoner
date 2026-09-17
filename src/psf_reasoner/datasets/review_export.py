"""Human review export workflow (V3 data pipeline).

Exports candidate datasets to CSV and JSON formats suitable for manual
curation.  Supports review status tracking and re-import of reviewed data.
"""

from __future__ import annotations

import csv
import io
import json

from psf_reasoner.datasets.schemas import MutationLigandPair, ReviewStatus


def export_review_csv(samples: list[MutationLigandPair]) -> str:
    """Export samples to a CSV string for manual review.

    Columns are ordered for easy human scanning: identity first, then
    experimental values, then provenance, then review status.
    """
    if not samples:
        return ""

    output = io.StringIO()
    fieldnames = [
        "sample_id",
        "protein",
        "accession",
        "mutation",
        "wt_residue",
        "mutant_residue",
        "uniprot_pos",
        "pdb_pos",
        "chain",
        "ligand",
        "ligand_name",
        "assay",
        "wt_value",
        "mutant_value",
        "unit",
        "ddG",
        "effect",
        "wt_pdb",
        "mutant_pdb",
        "bg_mutations",
        "method",
        "pmid",
        "doi",
        "source",
        "quality",
        "review",
        "review_notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for s in samples:
        writer.writerow(s.to_flat_dict())
    return output.getvalue()


def export_review_json(samples: list[MutationLigandPair]) -> str:
    """Export samples to a JSON string for programmatic review tools."""
    return json.dumps(
        {
            "dataset_version": "1.0.0",
            "exported_count": len(samples),
            "by_review_status": {
                status.value: len([s for s in samples if s.review_status == status])
                for status in ReviewStatus
            },
            "samples": [s.to_flat_dict() for s in samples],
        },
        indent=2,
        default=str,
    )


def import_reviewed_json(json_str: str) -> list[MutationLigandPair]:
    """Import reviewed samples from a JSON file.

    Only updates review_status and review_notes — does not modify
    experimental values or structural references.
    """
    data = json.loads(json_str)
    samples = []
    for item in data.get("samples", []):
        s = MutationLigandPair(
            sample_id=item.get("sample_id", ""),
            protein_accession=item.get("accession", ""),
            protein_name=item.get("protein", ""),
            mutation_notation=item.get("mutation", ""),
            wt_residue=item.get("wt_residue", ""),
            mutant_residue=item.get("mutant_residue", ""),
            uniprot_position=item.get("uniprot_pos"),
            ligand_id=item.get("ligand", ""),
            ligand_name=item.get("ligand_name", ""),
            review_status=ReviewStatus(item.get("review", "pending")),
            review_notes=item.get("review_notes", ""),
            pmid=item.get("pmid", ""),
            doi=item.get("doi", ""),
            data_source=item.get("source", ""),
        )
        samples.append(s)
    return samples


def get_review_statistics(samples: list[MutationLigandPair]) -> dict:
    """Return summary statistics about review status."""
    return {
        "total": len(samples),
        "accepted": sum(1 for s in samples if s.review_status == ReviewStatus.ACCEPTED),
        "rejected": sum(1 for s in samples if s.review_status == ReviewStatus.REJECTED),
        "pending": sum(1 for s in samples if s.review_status == ReviewStatus.PENDING),
        "needs_clarification": sum(1 for s in samples if s.review_status == ReviewStatus.NEEDS_CLARIFICATION),
        "rejection_reasons": {
            s.rejection_reason
            for s in samples
            if s.review_status == ReviewStatus.REJECTED and s.rejection_reason
        },
    }
