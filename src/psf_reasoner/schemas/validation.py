"""Missing-evidence and validation-plan contracts."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import ScientificModel
from psf_reasoner.schemas.evidence import EvidenceType


class ValidationKind(StrEnum):
    STRUCTURE_ANALYSIS = "structure_analysis"
    MUTANT_MODELLING = "mutant_modelling"
    MOLECULAR_DYNAMICS = "molecular_dynamics"
    ENERGY_CALCULATION = "energy_calculation"
    BINDING_ASSAY = "binding_assay"
    FUNCTIONAL_ASSAY = "functional_assay"


class MissingEvidence(ScientificModel):
    id: str = Field(pattern=r"^missing-[a-f0-9]{12}$")
    evidence_type: EvidenceType
    reason: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    related_claims: tuple[str, ...] = ()


class ValidationStep(ScientificModel):
    id: str = Field(pattern=r"^validation-[a-f0-9]{12}$")
    priority: int = Field(ge=1)
    kind: ValidationKind
    objective: str = Field(min_length=1)
    method: str = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    addresses: tuple[str, ...] = ()


class ValidationPlan(ScientificModel):
    steps: tuple[ValidationStep, ...] = ()
