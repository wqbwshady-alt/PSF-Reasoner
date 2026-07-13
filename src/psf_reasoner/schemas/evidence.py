"""Physical evidence contracts."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import Claim, Direction, ScientificModel


class EvidenceStatus(StrEnum):
    OBSERVED = "observed"
    COMPUTED = "computed"
    INFERRED = "inferred"
    REQUIRED = "required"


class EvidenceType(StrEnum):
    RESIDUE_PROPERTY_CHANGE = "residue_property_change"
    ATOMIC_DISTANCE = "atomic_distance"
    RESIDUE_CONTACT = "residue_contact"
    HYDROGEN_BOND = "hydrogen_bond"
    SALT_BRIDGE = "salt_bridge"
    HYDROPHOBIC_CONTACT = "hydrophobic_contact"
    PI_INTERACTION = "pi_interaction"
    WATER_BRIDGE = "water_bridge"
    SOLVENT_EXPOSURE = "solvent_exposure"
    POCKET_GEOMETRY = "pocket_geometry"
    RESIDUE_NETWORK = "residue_network"
    MUTATION_MODEL = "mutation_model"
    ENERGY_COMPONENT = "energy_component"
    EXPERIMENTAL_CALIBRATION = "experimental_calibration"


class Measurement(ScientificModel):
    name: str = Field(min_length=1)
    value: float | None = None
    unit: str | None = None
    direction: Direction = Direction.UNKNOWN
    reference_value: float | None = None


class PhysicalEvidence(Claim):
    evidence_type: EvidenceType
    status: EvidenceStatus
    entities: tuple[str, ...] = ()
    measurement: Measurement | None = None
