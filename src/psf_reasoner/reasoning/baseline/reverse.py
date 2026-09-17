"""Reverse baseline reasoning: phenotype -> candidate mechanisms -> required evidence."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.reasoning.baseline.scoring import _bounded, _qualitative, _rule_provenance
from psf_reasoner.reasoning.baseline.support import (
    _matching_evidence_ids,
    _reverse_evidence_support,
)
from psf_reasoner.reasoning.results import ReverseResult
from psf_reasoner.schemas.common import CalibrationStatus, Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    Measurement,
    PhysicalEvidence,
)
from psf_reasoner.schemas.function import ReverseCandidate
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import MechanismCategory, MechanismType, StructuralMechanism
from psf_reasoner.schemas.validation import MissingEvidence, ValidationKind, ValidationStep


class BaselineReverseReasoner:
    def reason(
        self,
        request: AnalysisRequest,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> ReverseResult:
        phenotype = request.phenotype
        if phenotype is None:
            return ReverseResult()

        if phenotype.name == "drug_resistance":
            return self._drug_resistance(request, evidence)
        return self._generic_phenotype(request)

    def _drug_resistance(
        self, request: AnalysisRequest, evidence: tuple[PhysicalEvidence, ...]
    ) -> ReverseResult:
        ligand = request.ligand.identifier
        mechanisms = (
            self._mechanism(
                request,
                MechanismType.POCKET_PACKING,
                "Candidate loss or reorganization of inhibitor pocket packing",
                "Resistance could arise if pocket packing changes preferentially weaken inhibitor binding.",
                0.62,
            ),
            self._mechanism(
                request,
                MechanismType.LIGAND_ANCHORING,
                "Candidate weakening of ligand anchoring",
                "Resistance could arise from loss of a direct or water-mediated inhibitor anchor.",
                0.56,
            ),
            self._mechanism(
                request,
                MechanismType.WATER_NETWORK,
                "Candidate binding-site water-network reorganization",
                "Resistance could arise if conserved hydration interactions are disrupted or displaced.",
                0.45,
            ),
        )
        required = (
            self._required_evidence(
                request,
                EvidenceType.RESIDUE_CONTACT,
                Direction.DECREASE,
                "Expected loss or reorganization of inhibitor contacts",
                "The resistant state should show altered contact occupancy near the inhibitor.",
            ),
            self._required_evidence(
                request,
                EvidenceType.POCKET_GEOMETRY,
                Direction.CHANGE,
                "Expected inhibitor-pocket geometry change",
                "A packing mechanism predicts a detectable local cavity, shape, or flexibility change.",
            ),
            self._required_evidence(
                request,
                EvidenceType.WATER_BRIDGE,
                Direction.CHANGE,
                "Expected water-network change",
                "A hydration mechanism predicts changed water occupancy or bridge persistence.",
            ),
            self._required_evidence(
                request,
                EvidenceType.ENERGY_COMPONENT,
                Direction.INCREASE,
                "Expected reduction in favorable inhibitor binding",
                "Resistance via weaker binding predicts a less favorable mutant local interaction score.",
            ),
        )
        candidate_specs = (
            (mechanisms[0], required[0:2]),
            (mechanisms[1], (required[0], required[3])),
            (mechanisms[2], (required[2], required[3])),
        )
        candidate_items = []
        for mechanism, expected in candidate_specs:
            evidence_support = _reverse_evidence_support(evidence, expected)
            candidate_items.append(
                (
                    evidence_support,
                    ReverseCandidate(
                        id=make_id("candidate", request.phenotype.name, mechanism.mechanism_type, ligand),
                        title=mechanism.title,
                        description=mechanism.description,
                        mechanism_type=mechanism.mechanism_type,
                        expected_evidence=tuple(item.id for item in expected),
                        rank=0,
                        confidence=_bounded(mechanism.confidence + evidence_support),
                        provenance=_rule_provenance("resistance phenotype -> candidate binding mechanism"),
                        supports=(mechanism.id, *_matching_evidence_ids(evidence, expected)),
                        limitations=(
                            "Ranking combines phenotype prior with computed physical evidence "
                            "when available.",
                        ),
                    ),
                )
            )
        candidates = tuple(
            candidate.model_copy(update={"rank": rank})
            for rank, (_, candidate) in enumerate(
                sorted(candidate_items, key=lambda item: item[0] + item[1].confidence, reverse=True),
                start=1,
            )
        )
        missing = tuple(
            MissingEvidence(
                id=make_id("missing", item.evidence_type, request.phenotype.name, ligand),
                evidence_type=item.evidence_type,
                reason=f"Required reverse-predicted evidence is not yet available: {item.title}.",
                impact="The associated reverse mechanism cannot yet be discriminated.",
                related_claims=tuple(
                    candidate.id for candidate in candidates if item.id in candidate.expected_evidence
                ),
            )
            for item in required
        )
        steps = (
            ValidationStep(
                id=make_id("validation", "reverse_structure", request.phenotype.name, ligand),
                priority=1,
                kind=ValidationKind.MUTANT_MODELLING,
                objective="Discriminate packing, anchoring, and hydration mechanisms.",
                method="Compare relaxed wild-type and mutant contact, pocket, and water-network features.",
                expected_result="One or more candidate-specific physical signatures should emerge.",
                addresses=tuple(item.id for item in missing[:3]),
            ),
            ValidationStep(
                id=make_id("validation", "reverse_binding", request.phenotype.name, ligand),
                priority=2,
                kind=ValidationKind.BINDING_ASSAY,
                objective="Link the resistant phenotype to altered inhibitor binding.",
                method="Measure matched inhibitor affinity and catalytic competence for both variants.",
                expected_result="Reduced inhibitor affinity with retained function would support resistance.",
                addresses=(missing[3].id,),
            ),
        )
        return ReverseResult(
            mechanisms=mechanisms,
            candidates=candidates,
            required_evidence=required,
            missing_evidence=missing,
            validation_steps=steps,
        )

    def _generic_phenotype(self, request: AnalysisRequest) -> ReverseResult:
        assert request.phenotype is not None
        mechanism = self._mechanism(
            request,
            MechanismType.CONFORMATIONAL_PREFERENCE,
            "Candidate conformational-preference change",
            f"The {request.phenotype.name} phenotype may reflect a shifted conformational ensemble.",
            0.30,
        )
        evidence = self._required_evidence(
            request,
            EvidenceType.RESIDUE_CONTACT,
            Direction.CHANGE,
            "Expected state-dependent contact-network change",
            "A conformational mechanism predicts reproducible contact differences between states.",
        )
        candidate = ReverseCandidate(
            id=make_id("candidate", request.phenotype.name, mechanism.mechanism_type),
            title=mechanism.title,
            description=mechanism.description,
            mechanism_type=mechanism.mechanism_type,
            expected_evidence=(evidence.id,),
            rank=1,
            confidence=0.30,
            provenance=_rule_provenance("generic phenotype -> conformational candidate"),
            supports=(mechanism.id,),
            limitations=("No phenotype-specific rule is available in the baseline engine.",),
        )
        missing = MissingEvidence(
            id=make_id("missing", evidence.evidence_type, request.phenotype.name),
            evidence_type=evidence.evidence_type,
            reason="State-resolved structural evidence is unavailable.",
            impact="The generic mechanism cannot be tested or ranked against alternatives.",
            related_claims=(candidate.id,),
        )
        return ReverseResult(
            mechanisms=(mechanism,),
            candidates=(candidate,),
            required_evidence=(evidence,),
            missing_evidence=(missing,),
            validation_steps=(
                ValidationStep(
                    id=make_id("validation", "generic_reverse", request.phenotype.name),
                    priority=1,
                    kind=ValidationKind.MOLECULAR_DYNAMICS,
                    objective="Determine whether the phenotype tracks a conformational shift.",
                    method="Compare state ensembles and residue-contact occupancies.",
                    expected_result="A reproducible ensemble shift would support the candidate.",
                    addresses=(missing.id, candidate.id),
                ),
            ),
        )

    @staticmethod
    def _mechanism(
        request: AnalysisRequest,
        mechanism_type: MechanismType,
        title: str,
        description: str,
        confidence: float,
        category: MechanismCategory = MechanismCategory.HYPOTHESIZED,
    ) -> StructuralMechanism:
        assert request.phenotype is not None
        return StructuralMechanism(
            id=make_id("mechanism", "reverse", request.phenotype.name, mechanism_type),
            title=title,
            description=description,
            mechanism_type=mechanism_type,
            direction=Direction.CHANGE,
            affected_region="ligand-binding site",
            confidence=confidence,
            provenance=(
                Provenance(kind=ProvenanceKind.INPUT, source="analysis request phenotype"),
                *_rule_provenance("phenotype -> candidate structural mechanism"),
            ),
            limitations=(
                "This mechanism is reverse-inferred and requires physical evidence. [LEGACY HEURISTIC]",
            ),
            category=category,
            calibration_status=CalibrationStatus.HEURISTIC,
            qualitative_confidence=_qualitative(confidence),
        )

    @staticmethod
    def _required_evidence(
        request: AnalysisRequest,
        evidence_type: EvidenceType,
        direction: Direction,
        title: str,
        description: str,
    ) -> PhysicalEvidence:
        assert request.phenotype is not None
        return PhysicalEvidence(
            id=make_id("evidence", "required", request.phenotype.name, evidence_type),
            title=title,
            description=description,
            evidence_type=evidence_type,
            status=EvidenceStatus.REQUIRED,
            entities=(request.ligand.identifier,),
            measurement=Measurement(name=str(evidence_type), direction=direction),
            confidence=0.55,
            provenance=_rule_provenance("candidate mechanism -> expected physical signature"),
            limitations=("This is a prediction to test, not an observed result.",),
        )
