"""Quality checks and provenance for structures used in evidence calculations."""

from psf_reasoner.physical.interactions import describe_ligand_atom_types
from psf_reasoner.physical.structure import ParsedStructure, ResidueRecord, StructureParser
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.preparation import (
    PreparationIssue,
    PreparationRole,
    StructurePreparation,
)

EXPECTED_HEAVY_ATOMS = {
    "ALA": frozenset({"N", "CA", "C", "O", "CB"}),
    "ARG": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD", "NE", "CZ", "NH1", "NH2"}),
    "ASN": frozenset({"N", "CA", "C", "O", "CB", "CG", "OD1", "ND2"}),
    "ASP": frozenset({"N", "CA", "C", "O", "CB", "CG", "OD1", "OD2"}),
    "CYS": frozenset({"N", "CA", "C", "O", "CB", "SG"}),
    "GLN": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD", "OE1", "NE2"}),
    "GLU": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD", "OE1", "OE2"}),
    "GLY": frozenset({"N", "CA", "C", "O"}),
    "HIS": frozenset({"N", "CA", "C", "O", "CB", "CG", "ND1", "CD2", "CE1", "NE2"}),
    "ILE": frozenset({"N", "CA", "C", "O", "CB", "CG1", "CG2", "CD1"}),
    "LEU": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD1", "CD2"}),
    "LYS": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD", "CE", "NZ"}),
    "MET": frozenset({"N", "CA", "C", "O", "CB", "CG", "SD", "CE"}),
    "PHE": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD1", "CD2", "CE1", "CE2", "CZ"}),
    "PRO": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD"}),
    "SER": frozenset({"N", "CA", "C", "O", "CB", "OG"}),
    "THR": frozenset({"N", "CA", "C", "O", "CB", "OG1", "CG2"}),
    "TRP": frozenset(
        {"N", "CA", "C", "O", "CB", "CG", "CD1", "CD2", "NE1", "CE2", "CE3", "CZ2", "CZ3", "CH2"}
    ),
    "TYR": frozenset({"N", "CA", "C", "O", "CB", "CG", "CD1", "CD2", "CE1", "CE2", "CZ", "OH"}),
    "VAL": frozenset({"N", "CA", "C", "O", "CB", "CG1", "CG2"}),
}
SUPPORTED_LIGAND_ELEMENTS = frozenset({"B", "BR", "C", "CL", "F", "H", "I", "N", "O", "P", "S"})


class StructurePreparationInspector:
    def __init__(self, parser: StructureParser | None = None) -> None:
        self._parser = parser or StructureParser()

    def inspect_request(self, request: AnalysisRequest) -> tuple[StructurePreparation, ...]:
        reference = self._parser.parse(request.structure)
        prepared = [self.inspect(reference, PreparationRole.REFERENCE, request.ligand.identifier)]
        if request.mutant_structure is not None:
            mutant = self._parser.parse(request.mutant_structure)
            prepared.append(self.inspect(mutant, PreparationRole.MUTANT, request.ligand.identifier))
        return tuple(prepared)

    def inspect(
        self,
        structure: ParsedStructure,
        role: PreparationRole,
        ligand_identifier: str,
    ) -> StructurePreparation:
        issues = [
            *_alternate_conformation_issues(structure),
            *_missing_atom_issues(structure),
            *_ligand_typing_issues(structure, ligand_identifier),
        ]
        ligand_atom_types = _ligand_atom_types(structure, ligand_identifier)
        return StructurePreparation(
            role=role,
            source=structure.source_path,
            model_index=structure.model_index,
            format=structure.source_format.value,
            residue_count=len(structure.residues),
            atom_count=sum(len(residue.atoms) for residue in structure.residues),
            water_residue_count=sum(residue.is_water for residue in structure.residues),
            alternate_atom_count=structure.alternate_atom_count,
            assumptions=(
                "Alternate conformations are reduced by highest occupancy before calculations.",
                "No protonation-state repair or hydrogen addition is performed by the preparation inspector.",
                "Ligand bonds are inferred from coordinate-distance heuristics unless "
                "explicit chemistry is configured.",
            ),
            ligand_atom_types=ligand_atom_types,
            issues=tuple(issues),
        )


def _alternate_conformation_issues(structure: ParsedStructure) -> tuple[PreparationIssue, ...]:
    if not structure.alternate_atom_count:
        return ()
    return (
        PreparationIssue(
            code="alternate_conformations_selected",
            message=(
                "Alternate conformations were reduced to the highest-occupancy atom for each atom name."
            ),
        ),
    )


def _missing_atom_issues(structure: ParsedStructure) -> tuple[PreparationIssue, ...]:
    incomplete = tuple(
        residue.identity.label
        for residue in structure.residues
        if not residue.is_hetero and not residue.is_water and _missing_heavy_atoms(residue)
    )
    if not incomplete:
        return ()
    shown = incomplete[:24]
    suffix = "" if len(incomplete) <= len(shown) else f" and {len(incomplete) - len(shown)} more"
    return (
        PreparationIssue(
            code="missing_protein_heavy_atoms",
            message=f"Protein residues are missing expected heavy atoms: {', '.join(shown)}{suffix}.",
            affected_entities=shown,
        ),
    )


def _ligand_typing_issues(
    structure: ParsedStructure,
    ligand_identifier: str,
) -> tuple[PreparationIssue, ...]:
    try:
        ligand = structure.locate_ligand_by_identifier(ligand_identifier)
    except ValueError:
        return ()
    unknown = tuple(
        atom.label for atom in ligand.atoms if atom.element.upper() not in SUPPORTED_LIGAND_ELEMENTS
    )
    nitrogen_atoms = tuple(atom.label for atom in ligand.atoms if atom.element == "N")
    issues: list[PreparationIssue] = []
    if unknown:
        issues.append(
            PreparationIssue(
                code="unsupported_ligand_elements",
                message="Some ligand elements have no built-in chemical typing rule.",
                affected_entities=unknown,
            )
        )
    if nitrogen_atoms:
        issues.append(
            PreparationIssue(
                code="ligand_nitrogen_protonation_unknown",
                message=(
                    "Ligand nitrogen donor/acceptor status is conservative until protonation or bond-order "
                    "information is supplied."
                ),
                affected_entities=nitrogen_atoms,
            )
        )
    return tuple(issues)


def _ligand_atom_types(
    structure: ParsedStructure,
    ligand_identifier: str,
) -> tuple[str, ...]:
    try:
        ligand = structure.locate_ligand_by_identifier(ligand_identifier)
    except ValueError:
        return ()
    return describe_ligand_atom_types(ligand)


def _missing_heavy_atoms(residue: ResidueRecord) -> frozenset[str]:
    expected = EXPECTED_HEAVY_ATOMS.get(residue.identity.name)
    if expected is None:
        return frozenset()
    observed = frozenset(atom.name for atom in residue.atoms if atom.element not in {"D", "H"})
    return expected - observed
