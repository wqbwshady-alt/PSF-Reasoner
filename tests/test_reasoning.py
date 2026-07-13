from psf_reasoner.bootstrap import create_default_service
from psf_reasoner.schemas.consistency import ConsistencyStatus
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType
from psf_reasoner.schemas.function import FunctionType
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import MechanismType


def test_v82a_bidirectional_chain_is_complete_and_consistent(
    bidirectional_request: AnalysisRequest,
) -> None:
    report = create_default_service().analyze(bidirectional_request)

    assert report.mode.value == "bidirectional"
    assert any(
        item.evidence_type is EvidenceType.RESIDUE_PROPERTY_CHANGE and item.status is EvidenceStatus.INFERRED
        for item in report.physical_evidence
    )
    assert any(
        item.evidence_type is EvidenceType.RESIDUE_CONTACT and item.status is EvidenceStatus.REQUIRED
        for item in report.physical_evidence
    )
    assert any(
        item.evidence_type is EvidenceType.ATOMIC_DISTANCE and item.status is EvidenceStatus.COMPUTED
        for item in report.physical_evidence
    )
    assert any(item.evidence_type is EvidenceType.MUTATION_MODEL for item in report.physical_evidence)
    assert any(
        item.evidence_type is EvidenceType.EXPERIMENTAL_CALIBRATION for item in report.physical_evidence
    )
    assert any(item.mechanism_type is MechanismType.POCKET_PACKING for item in report.structural_mechanisms)
    assert any(item.function_type is FunctionType.DRUG_RESISTANCE for item in report.functional_hypotheses)
    assert report.reverse_candidates[0].mechanism_type is MechanismType.POCKET_PACKING
    assert any(item.status is ConsistencyStatus.CONSISTENT for item in report.consistency_checks)
    assert report.missing_evidence
    assert report.validation_plan.steps


def test_all_causal_references_resolve_within_report(
    bidirectional_request: AnalysisRequest,
) -> None:
    report = create_default_service().analyze(bidirectional_request)
    claims = (
        *report.physical_evidence,
        *report.structural_mechanisms,
        *report.functional_hypotheses,
        *report.reverse_candidates,
        *report.consistency_checks,
    )
    known_ids = {claim.id for claim in claims}

    for claim in claims:
        assert set(claim.supports).issubset(known_ids)
        assert set(claim.contradicts).issubset(known_ids)
    for candidate in report.reverse_candidates:
        assert set(candidate.expected_evidence).issubset(known_ids)


def test_report_id_is_stable_for_same_request(
    bidirectional_request: AnalysisRequest,
) -> None:
    service = create_default_service()

    first = service.analyze(bidirectional_request)
    second = service.analyze(bidirectional_request)

    assert first.report_id == second.report_id
    assert first.generated_at != second.generated_at
