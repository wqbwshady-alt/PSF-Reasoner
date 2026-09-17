"""Evidence-support helpers shared by the baseline reasoning rules."""

from psf_reasoner.schemas.common import Direction
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType, PhysicalEvidence
from psf_reasoner.schemas.mechanisms import (
    EvidenceGraph,
    EvidenceNode,
    MechanismType,
    MissingEvidenceNode,
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
