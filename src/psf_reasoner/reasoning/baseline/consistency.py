"""Consistency checking between forward and reverse baseline reasoning paths."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.reasoning.baseline.scoring import _bounded, _rule_provenance
from psf_reasoner.reasoning.baseline.support import (
    _consistency_bonus,
    _supporting_evidence_for_mechanism,
)
from psf_reasoner.reasoning.results import ForwardResult, ReverseResult
from psf_reasoner.schemas.consistency import AgreementDetail, ConsistencyCheck, ConsistencyStatus
from psf_reasoner.schemas.evidence import PhysicalEvidence


class BaselineConsistencyChecker:
    def check(
        self,
        forward: ForwardResult,
        reverse: ReverseResult,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> tuple[ConsistencyCheck, ...]:
        if not forward.mechanisms or not reverse.candidates:
            available = tuple(claim.id for claim in (*forward.mechanisms, *reverse.candidates))
            return (
                ConsistencyCheck(
                    id=make_id("check", "one_direction", *available),
                    title="Bidirectional comparison unavailable",
                    description="Both a mutation and a functional phenotype are needed for comparison.",
                    status=ConsistencyStatus.INSUFFICIENT_EVIDENCE,
                    compared_claims=available,
                    confidence=1.0,
                    provenance=_rule_provenance("bidirectional completeness check"),
                ),
            )

        forward_by_type = {item.mechanism_type: item for item in forward.mechanisms}
        reverse_by_type = {item.mechanism_type: item for item in reverse.candidates}
        shared = sorted(set(forward_by_type) & set(reverse_by_type), key=str)
        if not shared:
            compared = tuple(item.id for item in (*forward.mechanisms, *reverse.candidates))
            return (
                ConsistencyCheck(
                    id=make_id("check", "mechanism_mismatch", *compared),
                    title="Forward and reverse mechanisms do not converge",
                    description="The baseline paths currently nominate different mechanism classes.",
                    status=ConsistencyStatus.CONFLICT,
                    compared_claims=compared,
                    confidence=0.55,
                    provenance=_rule_provenance("mechanism-type consistency check"),
                    limitations=("Additional evidence may reconcile or reprioritize the candidates.",),
                ),
            )

        return tuple(
            ConsistencyCheck(
                id=make_id("check", "mechanism_match", mechanism_type),
                title=f"Forward and reverse paths converge on {mechanism_type.value}",
                description=(
                    "The mutation-driven path and phenotype-driven path independently nominate "
                    "the same structural mechanism class."
                ),
                status=ConsistencyStatus.CONSISTENT,
                compared_claims=(
                    forward_by_type[mechanism_type].id,
                    reverse_by_type[mechanism_type].id,
                ),
                confidence=_bounded(
                    min(
                        forward_by_type[mechanism_type].confidence,
                        reverse_by_type[mechanism_type].confidence,
                    )
                    + _consistency_bonus(evidence, mechanism_type)
                ),
                provenance=_rule_provenance("mechanism-type consistency check"),
                supports=(
                    forward_by_type[mechanism_type].id,
                    reverse_by_type[mechanism_type].id,
                    *_supporting_evidence_for_mechanism(evidence, mechanism_type),
                ),
                limitations=(
                    "Agreement is strengthened only by computed evidence that matches the "
                    "nominated mechanism.",
                ),
                agreement_detail=AgreementDetail(
                    physical_agreement=round(
                        min(
                            forward_by_type[mechanism_type].confidence,
                            reverse_by_type[mechanism_type].confidence,
                        ),
                        3,
                    ),
                    functional_agreement=round(_consistency_bonus(evidence, mechanism_type), 3),
                    phenotype_agreement=round(0.5 + 0.5 * _consistency_bonus(evidence, mechanism_type), 3),
                ),
            )
            for mechanism_type in shared
        )
