"""Transparent baseline rules for bidirectional PSF reasoning."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.reasoning.results import ForwardResult, ReverseResult
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.consistency import ConsistencyCheck, ConsistencyStatus
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    Measurement,
    PhysicalEvidence,
)
from psf_reasoner.schemas.function import FunctionalHypothesis, FunctionType, ReverseCandidate
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import MechanismType, StructuralMechanism
from psf_reasoner.schemas.validation import MissingEvidence, ValidationKind, ValidationStep


def _rule_provenance(rule: str) -> tuple[Provenance, ...]:
    return (
        Provenance(
            kind=ProvenanceKind.BUILTIN_PRIOR,
            source="PSF baseline rules v1",
            method=rule,
        ),
    )


class BaselineForwardReasoner:
    def reason(
        self,
        request: AnalysisRequest,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> ForwardResult:
        property_evidence = next(
            (item for item in evidence if item.evidence_type is EvidenceType.RESIDUE_PROPERTY_CHANGE),
            None,
        )
        if request.mutation is None or property_evidence is None:
            return ForwardResult()

        mutation = request.mutation
        coordinate_evidence_ids = tuple(
            item.id
            for item in evidence
            if item.status is EvidenceStatus.COMPUTED
            and item.evidence_type
            in {
                EvidenceType.ATOMIC_DISTANCE,
                EvidenceType.RESIDUE_CONTACT,
                EvidenceType.HYDROPHOBIC_CONTACT,
                EvidenceType.HYDROGEN_BOND,
                EvidenceType.WATER_BRIDGE,
                EvidenceType.POCKET_GEOMETRY,
                EvidenceType.RESIDUE_NETWORK,
                EvidenceType.ENERGY_COMPONENT,
                EvidenceType.MUTATION_MODEL,
            }
        )
        has_paired_comparison = request.mutant_structure is not None and any(
            item.measurement is not None and item.measurement.name == "contact_state_delta"
            for item in evidence
        )
        has_shell_geometry = request.mutant_structure is not None and any(
            item.measurement is not None and item.measurement.name == "ligand_shell_bounding_box_volume_delta"
            for item in evidence
        )
        size_direction = (
            property_evidence.measurement.direction
            if property_evidence.measurement is not None
            else Direction.UNKNOWN
        )
        packing_direction = Direction.DECREASE if size_direction == Direction.DECREASE else Direction.CHANGE
        packing_score = _evidence_support_score(evidence, MechanismType.POCKET_PACKING)
        mechanism = StructuralMechanism(
            id=make_id("mechanism", "forward_pocket_packing", mutation.notation),
            title="Candidate pocket-packing change",
            description=(
                f"The {mutation.notation} side-chain change may alter local packing around "
                f"ligand {request.ligand.identifier}; coordinates are required to establish contact loss."
            ),
            mechanism_type=MechanismType.POCKET_PACKING,
            direction=packing_direction,
            affected_region=f"residue {mutation.residue_number} and ligand-contact shell",
            confidence=_bounded((0.63 if size_direction == Direction.DECREASE else 0.47) + packing_score),
            provenance=_rule_provenance("smaller-side-chain -> candidate packing loss"),
            supports=(property_evidence.id, *coordinate_evidence_ids),
            limitations=(
                "The mutation has not been placed or relaxed in 3D."
                if not has_paired_comparison
                else "The paired structures are compared geometrically but may differ in "
                "crystal state or unresolved conformational ensembles.",
            ),
        )
        mechanisms = [mechanism]
        if any(item.evidence_type is EvidenceType.RESIDUE_NETWORK for item in evidence):
            network_evidence = tuple(
                item.id for item in evidence if item.evidence_type is EvidenceType.RESIDUE_NETWORK
            )
            mechanisms.append(
                StructuralMechanism(
                    id=make_id("mechanism", "forward_residue_network", mutation.notation),
                    title="Candidate pocket residue-network change",
                    description=(
                        "Computed mutation-site graph degree changes indicate local residue-network rewiring."
                    ),
                    mechanism_type=MechanismType.RESIDUE_NETWORK,
                    direction=_measurement_direction(evidence, EvidenceType.RESIDUE_NETWORK),
                    affected_region="ligand-pocket residue graph",
                    confidence=_bounded(
                        0.48 + _evidence_support_score(evidence, MechanismType.RESIDUE_NETWORK)
                    ),
                    provenance=_rule_provenance(
                        "computed residue-network delta -> candidate network mechanism"
                    ),
                    supports=network_evidence,
                    limitations=("Residue-network edges are cutoff based and structure-state specific.",),
                )
            )
        if any(
            item.evidence_type
            in {EvidenceType.HYDROGEN_BOND, EvidenceType.WATER_BRIDGE, EvidenceType.SALT_BRIDGE}
            and item.status is EvidenceStatus.COMPUTED
            for item in evidence
        ):
            anchoring_evidence = tuple(
                item.id
                for item in evidence
                if item.evidence_type
                in {EvidenceType.HYDROGEN_BOND, EvidenceType.WATER_BRIDGE, EvidenceType.SALT_BRIDGE}
                and item.status is EvidenceStatus.COMPUTED
            )
            mechanisms.append(
                StructuralMechanism(
                    id=make_id("mechanism", "forward_ligand_anchoring", mutation.notation),
                    title="Candidate ligand-anchoring change",
                    description=(
                        "Typed direct or water-mediated interaction deltas suggest altered ligand anchoring."
                    ),
                    mechanism_type=MechanismType.LIGAND_ANCHORING,
                    direction=Direction.CHANGE,
                    affected_region=(
                        f"{mutation.notation} contact shell and ligand {request.ligand.identifier}"
                    ),
                    confidence=_bounded(
                        0.42 + _evidence_support_score(evidence, MechanismType.LIGAND_ANCHORING)
                    ),
                    provenance=_rule_provenance("typed interaction deltas -> ligand anchoring mechanism"),
                    supports=anchoring_evidence,
                    limitations=(
                        "Interaction counts are local structural signatures, not occupancies "
                        "over an ensemble.",
                    ),
                )
            )
        affinity = FunctionalHypothesis(
            id=make_id("hypothesis", "ligand_affinity", mutation.notation, request.ligand.identifier),
            title="Potential ligand-affinity decrease",
            description=(
                "If the candidate packing loss weakens favorable protein-ligand contacts, "
                "ligand affinity may decrease."
            ),
            function_type=FunctionType.LIGAND_AFFINITY,
            direction=Direction.DECREASE,
            confidence=_bounded(0.42 + _function_support_score(evidence)),
            provenance=_rule_provenance("packing loss -> possible affinity loss"),
            supports=(mechanism.id,),
            limitations=(
                "Entropic compensation, water rearrangement, and conformational relaxation are unknown.",
            ),
        )
        resistance = FunctionalHypothesis(
            id=make_id("hypothesis", "drug_resistance", mutation.notation, request.ligand.identifier),
            title="Potential inhibitor-resistance increase",
            description=(
                "If the ligand is an inhibitor and binding is selectively weakened while protein "
                "function is retained, resistance may increase."
            ),
            function_type=FunctionType.DRUG_RESISTANCE,
            direction=Direction.INCREASE,
            phenotype="drug_resistance",
            confidence=_bounded(0.36 + _function_support_score(evidence)),
            provenance=_rule_provenance(
                "inhibitor affinity loss with retained function -> possible resistance"
            ),
            supports=(affinity.id,),
            limitations=("The ligand role and retained catalytic competence have not been established.",),
        )

        missing_contacts = MissingEvidence(
            id=make_id("missing", "mutant_contacts", mutation.notation, request.ligand.identifier),
            evidence_type=EvidenceType.RESIDUE_CONTACT,
            reason=(
                "A local mutant-versus-reference comparison is available, but no full contact-map "
                "or conformational-ensemble comparison has been computed."
                if has_paired_comparison
                else "The supplied structure provides reference contacts, but no mutant-versus-reference "
                "contact comparison has been computed."
                if coordinate_evidence_ids
                else "Wild-type and mutant protein-ligand contacts have not been computed."
            ),
            impact="Contact changes are needed to support or reject the packing mechanism.",
            related_claims=(mechanism.id, affinity.id),
        )
        missing_geometry = MissingEvidence(
            id=make_id("missing", "pocket_geometry", mutation.notation, request.ligand.identifier),
            evidence_type=EvidenceType.POCKET_GEOMETRY,
            reason=(
                "A ligand-shell geometry proxy is available, but pocket shape and absolute cavity "
                "volume have not been evaluated with a validated cavity definition."
                if has_shell_geometry
                else "Pocket shape and volume have not been compared after mutation modelling."
            ),
            impact="The direction and magnitude of pocket remodelling remain unknown.",
            related_claims=(mechanism.id,),
        )
        missing_energy = MissingEvidence(
            id=make_id("missing", "binding_energy", mutation.notation, request.ligand.identifier),
            evidence_type=EvidenceType.ENERGY_COMPONENT,
            reason="No binding-energy calculation or experimental affinity measurement is available.",
            impact="Functional affinity and resistance hypotheses remain qualitative.",
            related_claims=(affinity.id, resistance.id),
        )
        steps = (
            ValidationStep(
                id=make_id("validation", "contacts", mutation.notation, request.ligand.identifier),
                priority=1,
                kind=ValidationKind.MUTANT_MODELLING,
                objective="Test whether the mutation changes direct ligand contacts and pocket packing.",
                method=(
                    "Compare complete contact maps and conformational ensembles for the supplied "
                    "wild-type and mutant structures."
                    if has_paired_comparison
                    else "Model and locally relax wild-type and mutant structures; compare contact maps."
                ),
                expected_result="Reduced or reorganized contacts would support the packing mechanism.",
                addresses=(missing_contacts.id, mechanism.id),
            ),
            ValidationStep(
                id=make_id("validation", "geometry", mutation.notation, request.ligand.identifier),
                priority=2,
                kind=ValidationKind.STRUCTURE_ANALYSIS,
                objective="Quantify mutation-associated pocket geometry and solvent exposure changes.",
                method=(
                    "Apply a validated cavity definition; compare pocket volume, local SASA, and "
                    "residue-ligand distances."
                ),
                expected_result="A reproducible cavity or exposure change would strengthen the mechanism.",
                addresses=(missing_geometry.id,),
            ),
            ValidationStep(
                id=make_id("validation", "affinity", mutation.notation, request.ligand.identifier),
                priority=3,
                kind=ValidationKind.BINDING_ASSAY,
                objective="Determine whether inhibitor affinity decreases in the mutant.",
                method="Measure matched wild-type and mutant binding affinity under the same conditions.",
                expected_result="Lower mutant affinity would support the functional hypothesis.",
                addresses=(missing_energy.id, affinity.id, resistance.id),
            ),
        )
        return ForwardResult(
            mechanisms=tuple(mechanisms),
            hypotheses=(affinity, resistance),
            missing_evidence=(missing_contacts, missing_geometry, missing_energy),
            validation_steps=steps,
        )


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
            limitations=("This mechanism is reverse-inferred and requires physical evidence.",),
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
            )
            for mechanism_type in shared
        )


def _bounded(value: float) -> float:
    return round(max(0.0, min(0.95, value)), 3)


def _measurement_direction(evidence: tuple[PhysicalEvidence, ...], evidence_type: EvidenceType) -> Direction:
    for item in evidence:
        if item.evidence_type is evidence_type and item.measurement is not None:
            return item.measurement.direction
    return Direction.UNKNOWN


def _evidence_support_score(evidence: tuple[PhysicalEvidence, ...], mechanism_type: MechanismType) -> float:
    score = 0.0
    for item in evidence:
        if item.status is not EvidenceStatus.COMPUTED or item.measurement is None:
            continue
        direction = item.measurement.direction
        if mechanism_type is MechanismType.POCKET_PACKING and item.evidence_type in {
            EvidenceType.RESIDUE_CONTACT,
            EvidenceType.POCKET_GEOMETRY,
            EvidenceType.HYDROPHOBIC_CONTACT,
            EvidenceType.ENERGY_COMPONENT,
        }:
            score += 0.06 if direction in {Direction.CHANGE, Direction.DECREASE, Direction.INCREASE} else 0.01
        if mechanism_type is MechanismType.LIGAND_ANCHORING and item.evidence_type in {
            EvidenceType.HYDROGEN_BOND,
            EvidenceType.SALT_BRIDGE,
            EvidenceType.WATER_BRIDGE,
        }:
            score += 0.07 if direction is not Direction.UNCHANGED else -0.03
        if (
            mechanism_type is MechanismType.RESIDUE_NETWORK
            and item.evidence_type is EvidenceType.RESIDUE_NETWORK
        ):
            score += 0.12 if direction is not Direction.UNCHANGED else -0.04
    return score


def _function_support_score(evidence: tuple[PhysicalEvidence, ...]) -> float:
    score = 0.0
    for item in evidence:
        if item.status is not EvidenceStatus.COMPUTED or item.measurement is None:
            continue
        if item.evidence_type is EvidenceType.ENERGY_COMPONENT:
            score += 0.12 if item.measurement.direction is Direction.INCREASE else -0.05
        elif item.evidence_type in {EvidenceType.RESIDUE_CONTACT, EvidenceType.HYDROPHOBIC_CONTACT}:
            score += 0.04 if item.measurement.direction is not Direction.UNCHANGED else 0.0
    return score


def _matching_evidence_ids(
    evidence: tuple[PhysicalEvidence, ...],
    expected: tuple[PhysicalEvidence, ...],
) -> tuple[str, ...]:
    return tuple(
        item.id
        for item in evidence
        if item.status is EvidenceStatus.COMPUTED
        and any(item.evidence_type is expected_item.evidence_type for expected_item in expected)
    )


def _reverse_evidence_support(
    evidence: tuple[PhysicalEvidence, ...],
    expected: tuple[PhysicalEvidence, ...],
) -> float:
    score = 0.0
    for expected_item in expected:
        for item in evidence:
            if (
                item.status is not EvidenceStatus.COMPUTED
                or item.evidence_type is not expected_item.evidence_type
            ):
                continue
            if item.measurement is None or expected_item.measurement is None:
                score += 0.03
                continue
            if expected_item.measurement.direction in {Direction.CHANGE, item.measurement.direction}:
                score += 0.08
            elif item.measurement.direction is Direction.UNCHANGED:
                score -= 0.03
            else:
                score -= 0.06
    return score


def _supporting_evidence_for_mechanism(
    evidence: tuple[PhysicalEvidence, ...],
    mechanism_type: MechanismType,
) -> tuple[str, ...]:
    type_map = {
        MechanismType.POCKET_PACKING: {
            EvidenceType.RESIDUE_CONTACT,
            EvidenceType.POCKET_GEOMETRY,
            EvidenceType.HYDROPHOBIC_CONTACT,
            EvidenceType.ENERGY_COMPONENT,
        },
        MechanismType.LIGAND_ANCHORING: {
            EvidenceType.HYDROGEN_BOND,
            EvidenceType.SALT_BRIDGE,
            EvidenceType.WATER_BRIDGE,
            EvidenceType.ENERGY_COMPONENT,
        },
        MechanismType.RESIDUE_NETWORK: {EvidenceType.RESIDUE_NETWORK},
    }
    return tuple(
        item.id
        for item in evidence
        if item.status is EvidenceStatus.COMPUTED
        and item.evidence_type in type_map.get(mechanism_type, set())
    )


def _consistency_bonus(evidence: tuple[PhysicalEvidence, ...], mechanism_type: MechanismType) -> float:
    return min(0.12, 0.03 * len(_supporting_evidence_for_mechanism(evidence, mechanism_type)))
