"""Shared application use case for all delivery adapters.

AnalysisService orchestrates the full PSF reasoning pipeline:
  input validation → structure preparation → physical evidence collection →
  forward reasoning → reverse reasoning → consistency verification →
  report assembly.

It depends on protocol interfaces (ForwardReasoner, ReverseReasoner,
ConsistencyChecker, PhysicalEvidenceProvider, MutationModeler) — never on
concrete implementations.  Wire concrete implementations through the
composition root in ``psf_reasoner.bootstrap``.
"""

from psf_reasoner.identifiers import make_id
from psf_reasoner.physical.base import PhysicalEvidenceProvider
from psf_reasoner.physical.modeling import (
    MutationModeler,
    MutationModelingUnavailableError,
)
from psf_reasoner.physical.preparation import StructurePreparationInspector
from psf_reasoner.physical.structure_qc import StructureQCProvider
from psf_reasoner.reasoning.protocols import ConsistencyChecker, ForwardReasoner, ReverseReasoner
from psf_reasoner.schemas.common import CalibrationStatus, Claim
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.preparation import QCGrade
from psf_reasoner.schemas.report import PSFReport
from psf_reasoner.schemas.validation import MissingEvidence, ValidationPlan, ValidationStep


class AnalysisService:
    def __init__(
        self,
        evidence_provider: PhysicalEvidenceProvider,
        forward_reasoner: ForwardReasoner,
        reverse_reasoner: ReverseReasoner,
        consistency_checker: ConsistencyChecker,
        preparation_inspector: StructurePreparationInspector | None = None,
        mutation_modeler: MutationModeler | None = None,
        structure_qc: StructureQCProvider | None = None,
    ) -> None:
        self._evidence_provider = evidence_provider
        self._forward_reasoner = forward_reasoner
        self._reverse_reasoner = reverse_reasoner
        self._consistency_checker = consistency_checker
        self._preparation_inspector = preparation_inspector or StructurePreparationInspector()
        self._mutation_modeler = mutation_modeler
        self._structure_qc = structure_qc or StructureQCProvider()

    def analyze(self, request: AnalysisRequest) -> PSFReport:
        effective_request, model_evidence = self._effective_request(request)
        preparation = self._preparation_inspector.inspect_request(effective_request)

        # -- Structure Pair QC (V2 Phase 1A) --------------------------------
        qc_report = None
        qc_confidence_factor = 1.0
        if effective_request.mutant_structure is not None:
            qc_report = self._structure_qc.assess(effective_request)
            if qc_report.grade is QCGrade.POORLY_COMPARABLE:
                qc_confidence_factor = 0.70
            elif qc_report.grade is QCGrade.PARTIALLY_COMPARABLE:
                qc_confidence_factor = 0.90
        # --------------------------------------------------------------------

        physical = (*model_evidence, *self._evidence_provider.collect(effective_request))
        forward = self._forward_reasoner.reason(effective_request, physical)
        reverse = self._reverse_reasoner.reason(effective_request, physical)
        checks = self._consistency_checker.check(forward, reverse, physical)

        # Apply QC confidence factor to all scored claims
        if qc_confidence_factor < 1.0:
            forward = self._apply_qc_discount(forward, qc_confidence_factor)
            reverse = self._apply_qc_discount(reverse, qc_confidence_factor)
            checks = tuple(
                check.model_copy(update={"confidence": round(check.confidence * qc_confidence_factor, 3)})
                for check in checks
            )

        all_evidence = _unique_by_id((*physical, *reverse.required_evidence))
        mechanisms = _unique_by_id((*forward.mechanisms, *reverse.mechanisms))
        missing = _unique_by_id((*forward.missing_evidence, *reverse.missing_evidence))
        steps = _unique_by_id((*forward.validation_steps, *reverse.validation_steps))

        # Defensive: filter stale/invalid supports/contradicts references
        known_ids = frozenset(
            claim.id
            for group in (
                all_evidence, mechanisms, forward.hypotheses,
                reverse.candidates, checks,
            )
            for claim in group
        )
        all_evidence = _sanitize_supports(all_evidence, known_ids)
        mechanisms = _sanitize_supports(mechanisms, known_ids)
        hypotheses = _sanitize_supports(
            forward.hypotheses, known_ids
        )
        candidates = _sanitize_supports(
            reverse.candidates, known_ids
        )
        # Also filter expected_evidence on ReverseCandidate
        candidates = tuple(
            candidate.model_copy(
                update={
                    "expected_evidence": tuple(
                        e for e in candidate.expected_evidence if e in known_ids
                    )
                }
            )
            if any(e not in known_ids for e in candidate.expected_evidence)
            else candidate
            for candidate in candidates
        )
        scored_claims = (*mechanisms, *hypotheses, *candidates)
        confidence = (
            round(sum(item.confidence for item in scored_claims) / len(scored_claims), 3)
            if scored_claims
            else 0.0
        )
        request_fingerprint = request.model_dump_json(exclude_none=True)
        return PSFReport(
            report_id=make_id("report", request_fingerprint),
            mode=request.mode,
            request=request,
            structure_preparation=preparation,
            structure_qc=qc_report,
            physical_evidence=all_evidence,
            structural_mechanisms=mechanisms,
            functional_hypotheses=hypotheses,
            reverse_candidates=candidates,
            consistency_checks=checks,
            missing_evidence=missing,
            validation_plan=ValidationPlan(steps=steps),
            confidence=confidence,
            calibration_status=CalibrationStatus.HEURISTIC,
            limitations=(
                "[LEGACY HEURISTIC ENGINE] All confidence values are uncalibrated heuristic "
                "weights (e.g. +0.06 per evidence match).  Qualitative labels "
                "(Strong/Moderate/Weak/Insufficient) are derived from these uncalibrated "
                "scores and must not be interpreted as probabilities.  See V3 roadmap "
                "for planned calibration against experimental ΔΔG / Ki data.",
                "Baseline structural mechanisms remain qualitative; coordinate evidence describes "
                "only the supplied reference and mutant structures.",
                "Required evidence denotes predictions to test, not completed calculations.",
            ),
        )

    def _effective_request(
        self,
        request: AnalysisRequest,
    ) -> tuple[AnalysisRequest, tuple]:
        if self._mutation_modeler is None or request.mutation is None or request.mutant_structure is not None:
            return request, ()
        try:
            result = self._mutation_modeler.build(request.structure, request.mutation, request.ligand)
        except MutationModelingUnavailableError:
            return request, ()
        return request.model_copy(update={"mutant_structure": result.structure}), (result.evidence,)

    @staticmethod
    def _apply_qc_discount(result, factor: float):
        """Apply confidence discount from Structure Pair QC to result claims."""
        from psf_reasoner.reasoning.results import ForwardResult, ReverseResult

        if isinstance(result, ForwardResult):
            return ForwardResult(
                mechanisms=tuple(
                    m.model_copy(update={"confidence": round(m.confidence * factor, 3)})
                    for m in result.mechanisms
                ),
                hypotheses=tuple(
                    h.model_copy(update={"confidence": round(h.confidence * factor, 3)})
                    for h in result.hypotheses
                ),
                missing_evidence=result.missing_evidence,
                validation_steps=result.validation_steps,
            )
        else:
            return ReverseResult(
                mechanisms=tuple(
                    m.model_copy(update={"confidence": round(m.confidence * factor, 3)})
                    for m in result.mechanisms
                ),
                candidates=tuple(
                    c.model_copy(update={"confidence": round(c.confidence * factor, 3)})
                    for c in result.candidates
                ),
                required_evidence=result.required_evidence,
                missing_evidence=result.missing_evidence,
                validation_steps=result.validation_steps,
            )


def _unique_by_id[T: Claim | MissingEvidence | ValidationStep](items: tuple[T, ...]) -> tuple[T, ...]:
    return tuple({item.id: item for item in items}.values())


def _sanitize_supports[T: Claim](claims: tuple[T, ...], known_ids: frozenset[str]) -> tuple[T, ...]:
    """Remove supports/contradicts references to IDs that don't exist in *known_ids*.

    This is a defensive measure against evidence providers or reasoners that
    generate stale or malformed reference IDs.  Claims with invalid references
    are replaced with copies that only reference valid IDs.
    """
    cleaned: list[T] = []
    for claim in claims:
        valid_supports = tuple(s for s in claim.supports if s in known_ids)
        valid_contradicts = tuple(c for c in claim.contradicts if c in known_ids)
        if valid_supports != claim.supports or valid_contradicts != claim.contradicts:
            claim = claim.model_copy(
                update={"supports": valid_supports, "contradicts": valid_contradicts}
            )
        cleaned.append(claim)
    return tuple(cleaned)
