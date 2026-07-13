"""Project-owned records and parsing helpers for coordinate structures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gemmi

from psf_reasoner.schemas.inputs import LigandSpec, MutationSpec, StructureFormat, StructureInput

THREE_TO_ONE = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}
WATER_RESIDUES = frozenset({"DOD", "HOH", "WAT"})


class StructureAnalysisError(ValueError):
    """Raised when a requested structural entity cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class ResidueIdentity:
    chain: str
    name: str
    number: int
    insertion_code: str | None

    @property
    def label(self) -> str:
        insertion = self.insertion_code or ""
        return f"{self.chain}:{self.name}{self.number}{insertion}"


@dataclass(frozen=True, slots=True)
class AtomRecord:
    residue: ResidueIdentity
    name: str
    element: str
    x: float
    y: float
    z: float
    occupancy: float
    altloc: str | None
    formal_charge: int

    @property
    def label(self) -> str:
        return f"{self.residue.label}:{self.name}"


@dataclass(frozen=True, slots=True)
class ResidueRecord:
    identity: ResidueIdentity
    one_letter_code: str | None
    is_hetero: bool
    atoms: tuple[AtomRecord, ...]

    @property
    def is_water(self) -> bool:
        return self.identity.name in WATER_RESIDUES


@dataclass(frozen=True, slots=True)
class ParsedStructure:
    source_path: str
    source_format: StructureFormat
    model_index: int
    residues: tuple[ResidueRecord, ...]
    alternate_atom_count: int

    def locate_ligand(self, ligand: LigandSpec) -> ResidueRecord:
        candidates = [
            residue
            for residue in self.residues
            if residue.identity.name == ligand.identifier.upper()
            and residue.identity.name not in WATER_RESIDUES
            and (ligand.chain is None or residue.identity.chain == ligand.chain)
            and (ligand.residue_number is None or residue.identity.number == ligand.residue_number)
        ]
        if not candidates:
            raise StructureAnalysisError(
                f"ligand {ligand.identifier!r} was not found in model {self.model_index}"
            )
        if len(candidates) > 1:
            labels = ", ".join(candidate.identity.label for candidate in candidates)
            raise StructureAnalysisError(
                f"ligand {ligand.identifier!r} is ambiguous; specify chain or residue_number "
                f"(matches: {labels})"
            )
        return candidates[0]

    def locate_ligand_by_identifier(self, identifier: str) -> ResidueRecord:
        return self.locate_ligand(LigandSpec(identifier=identifier))

    def locate_mutation_residues(self, mutation: MutationSpec) -> tuple[ResidueRecord, ...]:
        return self.locate_residues_at_site(mutation, mutation.wild_type)

    def locate_mutant_residues(self, mutation: MutationSpec) -> tuple[ResidueRecord, ...]:
        return self.locate_residues_at_site(mutation, mutation.mutant)

    def locate_residues_at_site(
        self,
        mutation: MutationSpec,
        expected_one_letter_code: str,
    ) -> tuple[ResidueRecord, ...]:
        candidates = tuple(
            residue
            for residue in self.residues
            if residue.identity.number == mutation.residue_number
            and residue.identity.insertion_code == mutation.insertion_code
            and (mutation.chain is None or residue.identity.chain == mutation.chain)
            and residue.one_letter_code == expected_one_letter_code
        )
        if candidates:
            return candidates

        position_matches = [
            residue
            for residue in self.residues
            if residue.identity.number == mutation.residue_number
            and residue.identity.insertion_code == mutation.insertion_code
            and (mutation.chain is None or residue.identity.chain == mutation.chain)
        ]
        if position_matches:
            observed = ", ".join(
                f"{residue.identity.label} ({residue.one_letter_code or '?'})" for residue in position_matches
            )
            raise StructureAnalysisError(
                f"mutation {mutation.notation} expects residue {expected_one_letter_code}, "
                f"but found {observed}"
            )
        chain_hint = f" in chain {mutation.chain}" if mutation.chain else ""
        raise StructureAnalysisError(
            f"residue {mutation.residue_number}{mutation.insertion_code or ''}{chain_hint} "
            f"was not found for mutation {mutation.notation}"
        )


class StructureParser:
    """Decode PDB/mmCIF while exposing only project-owned coordinate records."""

    def parse(self, structure_input: StructureInput) -> ParsedStructure:
        path = Path(structure_input.path)
        if not path.is_file():
            raise StructureAnalysisError(f"structure file does not exist: {path}")
        try:
            structure = gemmi.read_structure(str(path))
        except RuntimeError as error:
            raise StructureAnalysisError(f"could not parse structure file {path}: {error}") from error

        if structure_input.model_index >= len(structure):
            raise StructureAnalysisError(
                f"model_index {structure_input.model_index} is unavailable; "
                f"the structure has {len(structure)} model(s)"
            )
        parsed_format = _resolve_format(structure_input, path)
        residues = tuple(
            _to_residue_record(chain.name, residue)
            for chain in structure[structure_input.model_index]
            for residue in chain
        )
        return ParsedStructure(
            source_path=str(path),
            source_format=parsed_format,
            model_index=structure_input.model_index,
            residues=residues,
            alternate_atom_count=sum(
                1
                for chain in structure[structure_input.model_index]
                for residue in chain
                for atom in residue
                if str(atom.altloc).strip()
            ),
        )


def _resolve_format(structure_input: StructureInput, path: Path) -> StructureFormat:
    if structure_input.format is not StructureFormat.AUTO:
        return structure_input.format
    return StructureFormat.MMCIF if path.suffix.lower() in {".cif", ".mmcif"} else StructureFormat.PDB


def _to_residue_record(chain_name: str, residue: gemmi.Residue) -> ResidueRecord:
    identity = ResidueIdentity(
        chain=chain_name,
        name=residue.name.upper(),
        number=residue.seqid.num,
        insertion_code=_insertion_code(residue.seqid.icode),
    )
    selected_atoms = _select_altloc_atoms(residue)
    atoms = tuple(
        AtomRecord(
            residue=identity,
            name=atom.name.strip(),
            element=atom.element.name,
            x=atom.pos.x,
            y=atom.pos.y,
            z=atom.pos.z,
            occupancy=atom.occ,
            altloc=_altloc(atom),
            formal_charge=atom.charge,
        )
        for atom in selected_atoms
    )
    return ResidueRecord(
        identity=identity,
        one_letter_code=THREE_TO_ONE.get(identity.name),
        is_hetero=residue.het_flag == "H",
        atoms=atoms,
    )


def _insertion_code(value: str) -> str | None:
    normalized = str(value).strip()
    return normalized or None


def _select_altloc_atoms(residue: gemmi.Residue) -> tuple[gemmi.Atom, ...]:
    selected: dict[str, gemmi.Atom] = {}
    for atom in residue:
        key = atom.name.strip()
        previous = selected.get(key)
        if previous is None or _altloc_priority(atom) > _altloc_priority(previous):
            selected[key] = atom
    return tuple(selected.values())


def _altloc_priority(atom: gemmi.Atom) -> tuple[float, int, str]:
    altloc = _altloc(atom) or ""
    return (atom.occ, int(not altloc), altloc)


def _altloc(atom: gemmi.Atom) -> str | None:
    value = str(atom.altloc).strip()
    return value or None
