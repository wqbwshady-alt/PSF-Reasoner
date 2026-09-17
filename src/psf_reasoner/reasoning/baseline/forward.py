"""Forward baseline reasoning: mutation -> structural mechanism -> function."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.reasoning.baseline.scoring import (
    _bounded,
    _make_score_breakdown,
    _qualitative,
    _rule_provenance,
)
from psf_reasoner.reasoning.baseline.support import (
    _build_evidence_graph,
    _count_supporting_evidence,
    _evidence_support_score,
    _function_support_count,
    _function_support_score,
    _measurement_direction,
)
from psf_reasoner.reasoning.results import ForwardResult
from psf_reasoner.schemas.common import CalibrationStatus, Direction, ScoreType
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType, PhysicalEvidence
from psf_reasoner.schemas.function import FunctionalHypothesis, FunctionType, SupportCoverage
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import MechanismCategory, MechanismType, StructuralMechanism
from psf_reasoner.schemas.validation import MissingEvidence, ValidationKind, ValidationStep


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
        # ---------------------------------------------------------------------------
        # 机制层构造 (mechanism layer)
        # ---------------------------------------------------------------------------
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
        # ---------------------------------------------------------------------------
        # 功能层构造 (function layer)
        # ---------------------------------------------------------------------------
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

        # ---------------------------------------------------------------------------
        # 验证计划 (validation plan)
        # ---------------------------------------------------------------------------
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
