"""Validate the teaching-case JSON files against the case-record schema."""

from __future__ import annotations

import json
from pathlib import Path

CASES_DIR = Path(__file__).parent.parent / "cases" / "teaching"

_REQUIRED_TOP = {
    "case_id",
    "title",
    "protein",
    "mutation",
    "structures",
    "functional_measurement",
    "provenance",
    "mechanism",
    "review",
    "usage",
    "teaching",
}
_REQUIRED_MUTATION = {"notation", "wt_residue", "mutant_residue", "chain", "uniprot_position", "pdb_position"}
_REQUIRED_PROVENANCE = {"pmid", "doi", "source_location"}
_REQUIRED_MECHANISM = {"conclusion", "supporting_evidence", "conflicting_evidence", "missing_evidence"}
_REQUIRED_REVIEW = {"status", "reviewed_by", "review_date"}
_REQUIRED_USAGE = {"demo_ready", "teaching_ready", "quantitative_eval_ready"}
_REQUIRED_TEACHING = {
    "background",
    "learning_objectives",
    "observation_tasks",
    "thinking_questions",
    "stepwise_explanation",
    "facts",
    "computed_inferences",
    "hypotheses",
    "run_instructions",
}


def _load_cases() -> dict[str, dict]:
    cases = {}
    for path in sorted(CASES_DIR.glob("*.json")):
        cases[path.stem] = json.loads(path.read_text())
    return cases


def test_teaching_case_count() -> None:
    cases = _load_cases()
    assert 3 <= len(cases) <= 6, f"expected 3-5 teaching cases, got {len(cases)}"


def test_required_fields_present() -> None:
    for case_id, case in _load_cases().items():
        missing = _REQUIRED_TOP - set(case)
        assert not missing, f"{case_id}: missing top-level fields {missing}"
        for group, required in (
            ("mutation", _REQUIRED_MUTATION),
            ("provenance", _REQUIRED_PROVENANCE),
            ("mechanism", _REQUIRED_MECHANISM),
            ("review", _REQUIRED_REVIEW),
            ("usage", _REQUIRED_USAGE),
            ("teaching", _REQUIRED_TEACHING),
        ):
            missing = required - set(case[group])
            assert not missing, f"{case_id}: {group} missing {missing}"


def test_teaching_cases_never_eval_ready() -> None:
    for case_id, case in _load_cases().items():
        assert case["usage"]["quantitative_eval_ready"] is False, (
            f"{case_id}: teaching cases must not be marked quantitative_eval_ready"
        )


def test_review_status_values_valid() -> None:
    valid = {"verified", "pending_verification", "excluded"}
    for case_id, case in _load_cases().items():
        assert case["review"]["status"] in valid, case_id


def test_step_explanations_carry_evidence_status() -> None:
    valid = {"fact", "computed", "hypothesis"}
    for case_id, case in _load_cases().items():
        steps = case["teaching"]["stepwise_explanation"]
        assert steps, f"{case_id}: stepwise_explanation is empty"
        for step in steps:
            assert step.get("evidence_status") in valid, (
                f"{case_id}: step {step.get('step')} has invalid evidence_status"
            )


def test_verified_cases_have_real_pmids() -> None:
    known_good = {"15066177", "18597780", "7890613", "19478082"}
    for case_id, case in _load_cases().items():
        if case["review"]["status"] == "verified":
            assert case["provenance"]["pmid"] in known_good, (
                f"{case_id}: verified case cites PMID {case['provenance']['pmid']}"
            )


def test_structure_files_exist() -> None:
    root = Path(__file__).parent.parent
    for case_id, case in _load_cases().items():
        for side in ("wild_type", "mutant"):
            structure = case["structures"].get(side)
            if not structure:
                continue
            path = root / structure["file"]
            actual_names = {entry.name for entry in path.parent.iterdir()}
            assert path.name in actual_names, (
                f"{case_id}: {structure['file']} does not match the on-disk filename case"
            )
            assert path.is_file(), f"{case_id}: {structure['file']} missing"
