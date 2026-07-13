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
from psf_reasoner.reasoning.protocols import ConsistencyChecker, ForwardReasoner, ReverseReasoner
from psf_reasoner.schemas.common import Claim
from psf_reasoner.schemas.inputs import AnalysisRequest
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
    ) -> None:
        self._evidence_provider = evidence_provider
        self._forward_reasoner = forward_reasoner
        self._reverse_reasoner = reverse_reasoner
        self._consistency_checker = consistency_checker
        self._preparation_inspector = preparation_inspector or StructurePreparationInspector()
        self._mutation_modeler = mutation_modeler

    def analyze(self, request: AnalysisRequest) -> PSFReport:
        effective_request, model_evidence = self._effective_request(request)
        preparation = self._preparation_inspector.inspect_request(effective_request)
        physical = (*model_evidence, *self._evidence_provider.collect(effective_request))
        forward = self._forward_reasoner.reason(effective_request, physical)
        reverse = self._reverse_reasoner.reason(effective_request, physical)
        checks = self._consistency_checker.check(forward, reverse, physical)

        all_evidence = _unique_by_id((*physical, *reverse.required_evidence))
        mechanisms = _unique_by_id((*forward.mechanisms, *reverse.mechanisms))
        missing = _unique_by_id((*forward.missing_evidence, *reverse.missing_evidence))
        steps = _unique_by_id((*forward.validation_steps, *reverse.validation_steps))
        scored_claims = (*mechanisms, *forward.hypotheses, *reverse.candidates)
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
            physical_evidence=all_evidence,
            structural_mechanisms=mechanisms,
            functional_hypotheses=forward.hypotheses,
            reverse_candidates=reverse.candidates,
            consistency_checks=checks,
            missing_evidence=missing,
            validation_plan=ValidationPlan(steps=steps),
            confidence=confidence,
            limitations=(
                "Baseline structural mechanisms remain qualitative; coordinate evidence describes "
                "only the supplied reference and mutant structures.",
                "Required evidence denotes predictions to test, not completed calculations.",
                "Confidence values are heuristic and are not calibrated probabilities.",
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


def _unique_by_id[T: Claim | MissingEvidence | ValidationStep](items: tuple[T, ...]) -> tuple[T, ...]:
    return tuple({item.id: item for item in items}.values())
