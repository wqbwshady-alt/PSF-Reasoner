"""Transparent baseline rules for bidirectional PSF reasoning."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.reasoning.results import ForwardResult, ReverseResult
from psf_reasoner.schemas.common import (
    CalibrationStatus,
    Direction,
    Provenance,
    ProvenanceKind,
    QualitativeConfidence,
    ScoreBreakdown,
    ScoreType,
)
from psf_reasoner.schemas.consistency import AgreementDetail, ConsistencyCheck, ConsistencyStatus
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    Measurement,
    PhysicalEvidence,
)
from psf_reasoner.schemas.function import (
    FunctionalHypothesis,
    FunctionType,
    ReverseCandidate,
    SupportCoverage,
)
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import (
    EvidenceGraph,
    EvidenceNode,
    MechanismCategory,
    MechanismType,
    MissingEvidenceNode,
    StructuralMechanism,
)
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
        packing_confidence = _bounded(
            (0.63 if size_direction == Direction.DECREASE else 0.47) + packing_score
        )
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
            confidence=packing_confidence,
            provenance=_rule_provenance("smaller-side-chain -> candidate packing loss [LEGACY HEURISTIC]"),
            supports=(property_evidence.id, *coordinate_evidence_ids),
            limitations=(
                "The mutation has not been placed or relaxed in 3D."
                if not has_paired_comparison
                else "The paired structures are compared geometrically but may differ in "
                "crystal state or unresolved conformational ensembles.",
            ),
            score_breakdown=_make_score_breakdown(
                ScoreType.MECHANISM_SUPPORT,
                (0.63 if size_direction == Direction.DECREASE else 0.47) + packing_score,
                supporting=_count_supporting_evidence(evidence, MechanismType.POCKET_PACKING),
                conflicting=0,
                missing=1 if not has_paired_comparison else 0,
            ),
            category=MechanismCategory.EVIDENCE_SUPPORTED,
            evidence_graph=_build_evidence_graph(evidence, MechanismType.POCKET_PACKING),
            calibration_status=CalibrationStatus.HEURISTIC,
            qualitative_confidence=_qualitative(packing_confidence),
        )
        mechanisms = [mechanism]
        if any(item.evidence_type is EvidenceType.RESIDUE_NETWORK for item in evidence):
            network_evidence = tuple(
                item.id for item in evidence if item.evidence_type is EvidenceType.RESIDUE_NETWORK
            )
            network_conf = _bounded(0.48 + _evidence_support_score(evidence, MechanismType.RESIDUE_NETWORK))
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
                    confidence=network_conf,
                    provenance=_rule_provenance(
                        "computed residue-network delta -> candidate network mechanism [LEGACY HEURISTIC]"
                    ),
                    supports=network_evidence,
                    limitations=("Residue-network edges are cutoff based and structure-state specific.",),
                    score_breakdown=_make_score_breakdown(
                        ScoreType.MECHANISM_SUPPORT,
                        0.48 + _evidence_support_score(evidence, MechanismType.RESIDUE_NETWORK),
                        supporting=_count_supporting_evidence(evidence, MechanismType.RESIDUE_NETWORK),
                        missing=1,
                    ),
                    category=MechanismCategory.EVIDENCE_SUPPORTED,
                    evidence_graph=_build_evidence_graph(evidence, MechanismType.RESIDUE_NETWORK),
                    calibration_status=CalibrationStatus.HEURISTIC,
                    qualitative_confidence=_qualitative(network_conf),
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
            anchoring_conf = _bounded(
                0.42 + _evidence_support_score(evidence, MechanismType.LIGAND_ANCHORING)
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
                    confidence=anchoring_conf,
                    provenance=_rule_provenance(
                        "typed interaction deltas -> ligand anchoring mechanism [LEGACY HEURISTIC]"
                    ),
                    supports=anchoring_evidence,
                    limitations=(
                        "Interaction counts are local structural signatures, not occupancies "
                        "over an ensemble.",
                    ),
                    score_breakdown=_make_score_breakdown(
                        ScoreType.MECHANISM_SUPPORT,
                        0.42 + _evidence_support_score(evidence, MechanismType.LIGAND_ANCHORING),
                        supporting=_count_supporting_evidence(evidence, MechanismType.LIGAND_ANCHORING),
                        missing=1,
                    ),
                    category=MechanismCategory.HYPOTHESIZED,
                    evidence_graph=_build_evidence_graph(evidence, MechanismType.LIGAND_ANCHORING),
                    calibration_status=CalibrationStatus.HEURISTIC,
                    qualitative_confidence=_qualitative(anchoring_conf),
                )
            )
        func_score = _function_support_score(evidence)
        func_support_count = _function_support_count(evidence)
        affinity_conf = _bounded(0.42 + func_score)
        resistance_conf = _bounded(0.36 + func_score)
        affinity = FunctionalHypothesis(
            id=make_id("hypothesis", "ligand_affinity", mutation.notation, request.ligand.identifier),
            title="Potential ligand-affinity decrease",
            description=(
                "If the candidate packing loss weakens favorable protein-ligand contacts, "
                "ligand affinity may decrease."
            ),
            function_type=FunctionType.LIGAND_AFFINITY,
            direction=Direction.DECREASE,
            confidence=affinity_conf,
            provenance=_rule_provenance("packing loss -> possible affinity loss [LEGACY HEURISTIC]"),
            supports=(mechanism.id,),
            limitations=(
                "Entropic compensation, water rearrangement, and conformational relaxation are unknown.",
            ),
            score_breakdown=_make_score_breakdown(
                ScoreType.EVIDENCE_COVERAGE,
                0.42 + func_score,
                supporting=func_support_count,
                conflicting=0,
                missing=3,  # MMGBSA, Ki, ΔΔG
            ),
            support_coverage=SupportCoverage(
                current_evidence=tuple(
                    item.id
                    for item in evidence
                    if item.status is EvidenceStatus.COMPUTED
                    and item.evidence_type in {EvidenceType.RESIDUE_CONTACT, EvidenceType.HYDROPHOBIC_CONTACT}
                ),
                missing_evidence=("MMGBSA", "Ki / IC50", "ΔΔG"),
                coverage_ratio=round(min(func_support_count / max(1, func_support_count + 3), 1.0), 2),
                evidence_labels=("Contact change", "Hydrophobic change"),
                missing_labels=("MMGBSA", "Ki / IC50", "ΔΔG"),
            ),
            calibration_status=CalibrationStatus.HEURISTIC,
            qualitative_confidence=_qualitative(affinity_conf),
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
            confidence=resistance_conf,
            provenance=_rule_provenance(
                "inhibitor affinity loss with retained function -> possible resistance [LEGACY HEURISTIC]"
            ),
            supports=(affinity.id,),
            limitations=("The ligand role and retained catalytic competence have not been established.",),
            score_breakdown=_make_score_breakdown(
                ScoreType.EVIDENCE_COVERAGE,
                0.36 + func_score,
                supporting=func_support_count,
                conflicting=0,
                missing=4,  # catalytic activity, cell assay, drug assay, Ki
            ),
            support_coverage=SupportCoverage(
                current_evidence=tuple(
                    item.id
                    for item in evidence
                    if item.status is EvidenceStatus.COMPUTED
                    and item.evidence_type in {EvidenceType.ENERGY_COMPONENT, EvidenceType.RESIDUE_CONTACT}
                ),
                missing_evidence=("Catalytic Activity", "Cell Assay", "Drug Assay", "Ki / IC50"),
                coverage_ratio=round(min(func_support_count / max(1, func_support_count + 4), 1.0), 2),
                evidence_labels=("Energy change", "Contact change"),
                missing_labels=("Catalytic Activity", "Cell Assay", "Drug Assay", "Ki / IC50"),
            ),
            calibration_status=CalibrationStatus.HEURISTIC,
            qualitative_confidence=_qualitative(resistance_conf),
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
            ValidationStep(
                id=make_id("validation", "md", mutation.notation, request.ligand.identifier),
                priority=4,
                kind=ValidationKind.MOLECULAR_DYNAMICS,
                objective="Characterize conformational dynamics and interaction occupancies.",
                method=(
                    "Run MD simulations for WT and mutant; compute contact occupancies, "
                    "RMSF, hydrogen-bond lifetimes."
                ),
                expected_result=(
                    "MD-derived occupancies and dynamics should corroborate structural mechanisms."
                ),
                addresses=(missing_contacts.id, missing_energy.id),
            ),
            ValidationStep(
                id=make_id("validation", "experiment", mutation.notation, request.ligand.identifier),
                priority=5,
                kind=ValidationKind.FUNCTIONAL_ASSAY,
                objective="Validate resistance phenotype experimentally.",
                method="Measure catalytic activity, cell-based drug susceptibility, and selectivity panel.",
                expected_result="Mutant retains catalytic function while inhibitor potency drops ≥ 5-fold.",
                addresses=(resistance.id, missing_energy.id),
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


def _bounded(value: float) -> float:
    return round(max(0.0, min(0.95, value)), 3)


def _qualitative(value: float) -> QualitativeConfidence:
    """Map a heuristic numeric score to a qualitative label (V3 P0)."""
    if value >= 0.70:
        return QualitativeConfidence.STRONG
    if value >= 0.45:
        return QualitativeConfidence.MODERATE
    if value >= 0.25:
        return QualitativeConfidence.WEAK
    return QualitativeConfidence.INSUFFICIENT


def _make_score_breakdown(
    score_type: ScoreType,
    raw_score: float,
    supporting: int = 0,
    conflicting: int = 0,
    missing: int = 0,
    quality_factor: float = 1.0,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        score_type=score_type,
        raw_score=round(_bounded(raw_score), 3),
        supporting_evidence_count=supporting,
        conflicting_evidence_count=conflicting,
        missing_evidence_count=missing,
        evidence_quality_factor=round(quality_factor, 3),
    )


def _count_supporting_evidence(
    evidence: tuple[PhysicalEvidence, ...],
    mechanism_type: MechanismType,
) -> int:
    return len(_supporting_evidence_for_mechanism(evidence, mechanism_type))


def _build_evidence_graph(
    evidence: tuple[PhysicalEvidence, ...],
    mechanism_type: MechanismType,
) -> EvidenceGraph:
    """Build a structured evidence graph for a mechanism."""
    type_map = {
        MechanismType.POCKET_PACKING: {
            EvidenceType.RESIDUE_CONTACT,
            EvidenceType.POCKET_GEOMETRY,
            EvidenceType.HYDROPHOBIC_CONTACT,
            EvidenceType.ENERGY_COMPONENT,
            EvidenceType.ATOMIC_DISTANCE,
            EvidenceType.RESIDUE_NETWORK,
        },
        MechanismType.LIGAND_ANCHORING: {
            EvidenceType.HYDROGEN_BOND,
            EvidenceType.SALT_BRIDGE,
            EvidenceType.WATER_BRIDGE,
            EvidenceType.ENERGY_COMPONENT,
        },
        MechanismType.RESIDUE_NETWORK: {EvidenceType.RESIDUE_NETWORK},
    }
    relevant = type_map.get(mechanism_type, set())

    supporting: list[EvidenceNode] = []
    conflicting: list[EvidenceNode] = []

    for item in evidence:
        if item.status is not EvidenceStatus.COMPUTED:
            continue
        if item.evidence_type not in relevant:
            continue
        m = item.measurement
        value_str = ""
        direction = Direction.UNKNOWN
        if m is not None:
            direction = m.direction
            value_str = f"{m.value} {m.unit or ''}".strip()
        node = EvidenceNode(
            evidence_label=item.title,
            value=value_str,
            direction=direction,
            is_supporting=True,
        )
        # If a measurement shows UNCHANGED for a mechanism that expects
        # CHANGE, that is conflicting evidence.
        if m is not None and direction is Direction.UNCHANGED:
            node = node.model_copy(update={"is_supporting": False})
            conflicting.append(node)
        else:
            supporting.append(node)

    # Missing evidence nodes
    missing = _build_missing_nodes(mechanism_type, evidence)

    return EvidenceGraph(
        supporting=tuple(supporting),
        conflicting=tuple(conflicting),
        missing=tuple(missing),
    )


def _build_missing_nodes(
    mechanism_type: MechanismType,
    evidence: tuple[PhysicalEvidence, ...],
) -> list[MissingEvidenceNode]:
    """Determine what evidence types are missing for a mechanism."""
    present_types = frozenset(
        item.evidence_type for item in evidence if item.status is EvidenceStatus.COMPUTED
    )
    missing_defs = {
        MechanismType.POCKET_PACKING: (
            (EvidenceType.POCKET_GEOMETRY, "Real pocket volume change"),
            (EvidenceType.ENERGY_COMPONENT, "Binding energy calculation"),
        ),
        MechanismType.LIGAND_ANCHORING: (
            (EvidenceType.HYDROGEN_BOND, "Hydrogen bond occupancy"),
            (EvidenceType.ENERGY_COMPONENT, "Anchor-point energy"),
        ),
        MechanismType.RESIDUE_NETWORK: ((EvidenceType.POCKET_GEOMETRY, "Network topology change magnitude"),),
    }
    nodes: list[MissingEvidenceNode] = []
    for ev_type, importance in missing_defs.get(mechanism_type, ()):
        if ev_type not in present_types:
            nodes.append(
                MissingEvidenceNode(
                    evidence_label=ev_type.value,
                    importance=importance,
                )
            )
    return nodes


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


def _function_support_count(evidence: tuple[PhysicalEvidence, ...]) -> int:
    """Count how many computed evidence items support functional hypotheses."""
    count = 0
    for item in evidence:
        if item.status is not EvidenceStatus.COMPUTED:
            continue
        if item.evidence_type in {
            EvidenceType.ENERGY_COMPONENT,
            EvidenceType.RESIDUE_CONTACT,
            EvidenceType.HYDROPHOBIC_CONTACT,
            EvidenceType.ATOMIC_DISTANCE,
        }:
            count += 1
    return count


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
