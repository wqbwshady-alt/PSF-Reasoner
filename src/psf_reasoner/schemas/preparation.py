"""Structure-preparation provenance and quality contracts."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import ScientificModel


class PreparationRole(StrEnum):
    REFERENCE = "reference"
    MUTANT = "mutant"


class PreparationIssue(ScientificModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    message: str = Field(min_length=1)
    affected_entities: tuple[str, ...] = ()


class StructurePreparation(ScientificModel):
    role: PreparationRole
    source: str = Field(min_length=1)
    model_index: int = Field(ge=0)
    format: str = Field(min_length=1)
    residue_count: int = Field(ge=0)
    atom_count: int = Field(ge=0)
    water_residue_count: int = Field(ge=0)
    alternate_atom_count: int = Field(ge=0)
    assumptions: tuple[str, ...] = ()
    ligand_atom_types: tuple[str, ...] = ()
    issues: tuple[PreparationIssue, ...] = ()
