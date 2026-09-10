"""Regression tests for case-data integrity (2026-09-10 evidence audit).

These tests lock in the corrections from docs/EVIDENCE-REVIEW.md so that
fabricated values, wrong PMIDs, and ligand-mismatched structure pairs
cannot silently re-enter the verified dataset or the benchmark files.
"""

from __future__ import annotations

import json
from pathlib import Path

from psf_reasoner.datasets.golden_cases import (
    get_dataset_summary,
    load_golden_cases,
    load_verified_cases,
)
from psf_reasoner.datasets.schemas import ReviewStatus

# PMIDs that the 2026-09-10 audit proved to be unrelated to the claims that
# cited them.  None of these may appear on an ACCEPTED case.
KNOWN_BAD_PMIDS = {
    "2548654",  # juvenile polyp case report
    "12730686",  # cyclophilin A
    "15632378",  # CYP2D6 / tamoxifen
    "10681379",  # cocaine metabolites
    "9149701",  # prostacyclin
    "7540751",  # nursing humanities
    "8810284",  # chick collagen
    "11502742",  # occludin
    "11095614",  # corneal MMP
    "8345919",  # nurse education
    "11258910",  # plant glycoproteins
    "11527979",  # Wilson ATPase chimeras
    "2205042",  # pig parasites
    "3131872",  # oxygen therapy review
    "32726803",  # SARS-CoV-2 PLpro (not Mpro)
    "16954204",  # Derlin-1 / CFTR
    "24722272",  # aspergillus endophthalmitis
    "16189104",  # AmpC (not TEM-1)
}

# PMIDs verified as supporting the claims they are attached to.
VERIFIED_PMIDS = {
    "15066177",  # Mahalingam 2004 — V82A 3.3x / L90M 0.16x vs indinavir
    "18597780",  # Liu 2008 Table 1 — G48V/I50V/I54V/I54M Ki values
    "14690411",  # Clemente 2003 — D30N 2-6x
    "8643082",  # Ercikan-Abali 1996 — L22F 88x
    "19478082",  # Volpato 2009 — F31R dG 2.1
    "7890613",  # Lewis 1995 — 1DLR/1DLS L22 structures
    "25939061",  # Thress 2015 — C797S
}


def test_no_verified_case_cites_known_bad_pmid() -> None:
    for case in load_verified_cases():
        assert case.pmid not in KNOWN_BAD_PMIDS, f"{case.sample_id} cites known-bad PMID {case.pmid}"


def test_every_verified_case_has_verified_source() -> None:
    verified = load_verified_cases()
    assert verified, "the verified set must not be empty"
    for case in verified:
        assert case.pmid in VERIFIED_PMIDS, (
            f"{case.sample_id} is ACCEPTED but its PMID {case.pmid} has not been verified"
        )


def test_rejected_cases_have_explicit_reasons() -> None:
    rejected = [c for c in load_golden_cases() if c.review_status == ReviewStatus.REJECTED]
    assert len(rejected) > 0
    for case in rejected:
        assert case.rejection_reason, f"{case.sample_id} is REJECTED without a rejection_reason"


def test_bulk_fill_cases_are_not_accepted() -> None:
    # The old quota-fill rows carried "... bulk —" review notes and were
    # all ACCEPTED.  None of them may be ACCEPTED anymore.
    for case in load_verified_cases():
        assert "bulk" not in case.review_notes.lower(), case.sample_id


def test_flagship_v82a_case_is_correct() -> None:
    case = next(c for c in load_verified_cases() if c.sample_id == "HIV_V82A_MK1")
    assert case.pmid == "15066177"
    assert case.mutant_value == 3.3
    assert case.wt_pdb == "1sdt.cif"
    assert case.mutant_pdb == "1sdv.cif"
    assert case.ligand_id == "MK1"
    assert case.review_status == ReviewStatus.ACCEPTED
    assert {"Q7K", "L33I", "L63I", "C67A", "C95A"} <= set(case.background_mutations)


def test_verified_structure_pairs_have_matching_ligand() -> None:
    # Every verified case with a structure pair must have its assay ligand
    # actually present in the paired structures.
    import gemmi

    root = Path(__file__).parent.parent
    for case in load_verified_cases():
        if not (case.wt_pdb and case.mutant_pdb):
            continue
        for filename in (case.wt_pdb, case.mutant_pdb):
            path = root / "examples" / "data" / filename
            assert path.exists(), f"{case.sample_id}: structure file missing: {path}"
            structure = gemmi.read_structure(str(path))
            het_resnames = {
                residue.name
                for model in structure
                for chain in model
                for residue in chain
                if residue.het_flag and residue.name not in {"HOH", "CL", "SO4"}
            }
            assert case.ligand_id in het_resnames, (
                f"{case.sample_id}: ligand {case.ligand_id} not present in {filename} "
                f"(found: {sorted(het_resnames)})"
            )


def test_drv_case_with_mk1_structure_is_rejected() -> None:
    # The DRV case that used MK1-bound 1sdt/1sdv as its structure pair must
    # never be accepted for training.
    case = next(c for c in load_golden_cases() if c.sample_id == "HIV_V82A_DRV")
    assert case.review_status == ReviewStatus.REJECTED
    assert "ligand" in case.rejection_reason.lower()


def test_benchmark_json_mutant_structure_ids_fixed() -> None:
    root = Path(__file__).parent.parent
    v12 = json.loads((root / "benchmarks/hiv1_protease/v1.2.0.json").read_text())
    by_id = {c["case_id"]: c for c in v12["cases"]}
    assert by_id["hiv1-v82a-mk1"]["mutant_pdb_id"] == "1SDV"
    assert by_id["hiv1-l90m-mk1"]["mutant_pdb_id"] == "1SDU"
    assert by_id["hiv1-v82a-mk1"]["excluded_from_calibration"] is True


def test_pilot_benchmark_sources_are_verified() -> None:
    from psf_reasoner.benchmarks.schemas import get_pilot_benchmark

    for sample in get_pilot_benchmark():
        pmid = sample.source.removeprefix("PMID:")
        assert pmid in VERIFIED_PMIDS, f"{sample.sample_id} cites {sample.source} which is not verified"


def test_dataset_summary_reports_review_statuses() -> None:
    summary = get_dataset_summary()
    assert summary["verified"] > 0
    assert summary["review_statuses"].get("rejected", 0) > 0
    assert summary["total"] == len(load_golden_cases())
