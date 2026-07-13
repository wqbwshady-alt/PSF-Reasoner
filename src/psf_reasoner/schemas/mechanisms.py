"""Structural mechanism contracts."""

from enum import StrEnum

from psf_reasoner.schemas.common import Claim, Direction


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


class StructuralMechanism(Claim):
    mechanism_type: MechanismType
    direction: Direction = Direction.CHANGE
    affected_region: str | None = None
