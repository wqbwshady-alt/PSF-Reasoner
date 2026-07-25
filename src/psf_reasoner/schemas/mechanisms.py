"""Structural mechanism contracts (V2 — Phase 3 overhaul)."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import Claim, Direction, ScientificModel


class MechanismType(StrEnum):
    LIGAND_ANCHORING = "ligand_anchoring"
    POCKET_PACKING = "pocket_packing"
    WATER_NETWORK = "water_network"
    POCKET_GEOMETRY = "pocket_geometry"
    POCKET_FLEXIBILITY = "pocket_flexibility"
    RESIDUE_NETWORK = "residue_network"
    ALLOSTERIC_PATH = "allosteric_path"
    LOCAL_STABILITY = "local_stability"
    CONFORMATIONAL_PREFERENCE = "conformational_preference"


class MechanismCategory(StrEnum):
    """Whether a mechanism is directly supported by computed evidence or inferred."""

    EVIDENCE_SUPPORTED = "evidence_supported"
    HYPOTHESIZED = "hypothesized"


# ---------------------------------------------------------------------------
# Evidence Graph (V2 Phase 3C)
# ---------------------------------------------------------------------------


class EvidenceNode(ScientificModel):
    """One supporting or conflicting evidence item in a mechanism's evidence graph."""

    evidence_label: str = Field(min_length=1, description="Human-readable evidence name")
    value: str = Field(default="", description="e.g. '+0.35 Å', '5 → 3 contacts'")
    direction: Direction = Direction.UNKNOWN
    is_supporting: bool = True  # True = supporting, False = conflicting


class MissingEvidenceNode(ScientificModel):
    """An evidence type missing from a mechanism's support graph."""

    evidence_label: str = Field(min_length=1)
    importance: str = Field(default="", description="Why this evidence matters for the mechanism")


class EvidenceGraph(ScientificModel):
    """Structured evidence picture for a single mechanism (V2 Phase 3C).

    Shows what supports the mechanism (✅), what conflicts (❌), and
    what is missing (⬜).  Replaces opaque single-percentage confidence.
    """

    supporting: tuple[EvidenceNode, ...] = ()
    conflicting: tuple[EvidenceNode, ...] = ()
    missing: tuple[MissingEvidenceNode, ...] = ()


class StructuralMechanism(Claim):
    mechanism_type: MechanismType
    direction: Direction = Direction.CHANGE
    affected_region: str | None = None
    category: MechanismCategory | None = None
    evidence_graph: EvidenceGraph | None = None
