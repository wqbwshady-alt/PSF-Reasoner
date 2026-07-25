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


# ---------------------------------------------------------------------------
# Structure Pair Quality Control (V2 Phase 1A)
# ---------------------------------------------------------------------------


class QCGrade(StrEnum):
    """Overall comparability grade for paired WT/mutant structures."""

    COMPARABLE = "comparable"
    PARTIALLY_COMPARABLE = "partially_comparable"
    POORLY_COMPARABLE = "poorly_comparable"


class ChainMapping(ScientificModel):
    """Chain-level mapping between reference and mutant structures."""

    reference_chain: str = Field(min_length=1)
    mutant_chain: str = Field(min_length=1)
    reference_residue_count: int = Field(ge=0)
    mutant_residue_count: int = Field(ge=0)
    sequence_identity: float | None = Field(default=None, ge=0.0, le=1.0)


class BackgroundMutation(ScientificModel):
    """A sequence difference between WT and mutant beyond the target mutation."""

    chain: str = Field(min_length=1)
    residue_number: int
    reference_residue: str = Field(min_length=1, max_length=3)
    mutant_residue: str = Field(min_length=1, max_length=3)
    insertion_code: str | None = None


class StructureQCReport(ScientificModel):
    """Quality control report for paired WT/mutant structures.

    Produced before any comparative evidence computation.  A grade of
    ``POORLY_COMPARABLE`` should reduce confidence in all downstream deltas.
    """

    grade: QCGrade
    reference_resolution: float | None = Field(default=None, ge=0.0, description="Angstrom")
    mutant_resolution: float | None = Field(default=None, ge=0.0, description="Angstrom")
    chain_mappings: tuple[ChainMapping, ...] = ()
    ligand_mapping: str = Field(
        default="",
        description="Summary of ligand identity and pose correspondence across structures.",
    )
    background_mutations: tuple[BackgroundMutation, ...] = ()
    missing_residues_reference: tuple[str, ...] = ()
    missing_residues_mutant: tuple[str, ...] = ()
    missing_atoms_reference: tuple[str, ...] = ()
    missing_atoms_mutant: tuple[str, ...] = ()
    occupancy_issues: tuple[str, ...] = ()
    alternate_location_count_reference: int = Field(default=0, ge=0)
    alternate_location_count_mutant: int = Field(default=0, ge=0)
    rmsd_overall: float | None = Field(default=None, ge=0.0, description="C-alpha RMSD in Angstrom")
    rmsd_pocket: float | None = Field(default=None, ge=0.0, description="Pocket C-alpha RMSD")
    rmsd_ligand: float | None = Field(default=None, ge=0.0, description="Ligand heavy-atom RMSD")
    issues: tuple[PreparationIssue, ...] = ()
