"""Residue-template and ligand-environment atom typing.

Holds the atom-classification tables plus the :class:`AtomTyping` record and
the two typing entry points.  Nothing here imports :mod:`.analysis` (or
:mod:`.contacts`), so the typing layer stays below the assembly layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from psf_reasoner.physical.interactions.geometry import _heavy_atoms
from psf_reasoner.physical.interactions.graph import _ligand_bond_graph, _looks_like_ligand_aromatic_atom
from psf_reasoner.physical.structure import AtomRecord, ResidueRecord

AROMATIC_RESIDUE_ATOMS = {
    "PHE": frozenset({"CG", "CD1", "CD2", "CE1", "CE2", "CZ"}),
    "TYR": frozenset({"CG", "CD1", "CD2", "CE1", "CE2", "CZ"}),
    "TRP": frozenset({"CG", "CD1", "CD2", "NE1", "CE2", "CE3", "CZ2", "CZ3", "CH2"}),
    "HIS": frozenset({"CG", "ND1", "CD2", "CE1", "NE2"}),
}
DONOR_ATOMS = {
    "ARG": frozenset({"NE", "NH1", "NH2"}),
    "ASN": frozenset({"ND2"}),
    "CYS": frozenset({"SG"}),
    "GLN": frozenset({"NE2"}),
    "HIS": frozenset({"ND1", "NE2"}),
    "LYS": frozenset({"NZ"}),
    "SER": frozenset({"OG"}),
    "THR": frozenset({"OG1"}),
    "TRP": frozenset({"NE1"}),
    "TYR": frozenset({"OH"}),
}
# Polar carbon atoms — carbons bonded to O/N in side chains.
# These should NOT be counted as hydrophobic (aligns with PLIP's sp3-C-only rule).
POLAR_CARBON_ATOMS: dict[str, frozenset[str]] = {
    "ARG": frozenset({"CZ"}),
    "ASN": frozenset({"CG"}),
    "ASP": frozenset({"CG"}),
    "GLN": frozenset({"CD"}),
    "GLU": frozenset({"CD"}),
}

ACCEPTOR_ATOMS = {
    "ASN": frozenset({"OD1"}),
    "ASP": frozenset({"OD1", "OD2"}),
    "CYS": frozenset({"SG"}),
    "GLN": frozenset({"OE1"}),
    "GLU": frozenset({"OE1", "OE2"}),
    "HIS": frozenset({"ND1", "NE2"}),
    "MET": frozenset({"SD"}),
    "SER": frozenset({"OG"}),
    "THR": frozenset({"OG1"}),
    "TYR": frozenset({"OH"}),
}
POSITIVE_ATOMS = {
    "ARG": frozenset({"NE", "NH1", "NH2"}),
    "HIS": frozenset({"ND1", "NE2"}),
    "LYS": frozenset({"NZ"}),
}
NEGATIVE_ATOMS = {
    "ASP": frozenset({"OD1", "OD2"}),
    "GLU": frozenset({"OE1", "OE2"}),
}


@dataclass(frozen=True, slots=True)
class AtomTyping:
    donor: bool = False
    acceptor: bool = False
    positive: bool = False
    negative: bool = False
    aromatic: bool = False
    hydrophobic: bool = False
    confidence: float = 1.0
    reason: str = ""


def _type_protein_atom(atom: AtomRecord) -> AtomTyping:
    residue_name = atom.residue.name
    atom_name = atom.name
    if atom_name == "O" or atom_name == "OXT":
        return AtomTyping(acceptor=True, reason="protein backbone oxygen")
    if atom_name == "N":
        return AtomTyping(
            donor=residue_name != "PRO",
            reason="protein backbone amide nitrogen",
        )
    is_polar_carbon = atom_name in POLAR_CARBON_ATOMS.get(residue_name, frozenset())
    return AtomTyping(
        donor=atom_name in DONOR_ATOMS.get(residue_name, frozenset()),
        acceptor=atom_name in ACCEPTOR_ATOMS.get(residue_name, frozenset()),
        positive=atom_name in POSITIVE_ATOMS.get(residue_name, frozenset()),
        negative=atom_name in NEGATIVE_ATOMS.get(residue_name, frozenset()),
        aromatic=atom_name in AROMATIC_RESIDUE_ATOMS.get(residue_name, frozenset()),
        hydrophobic=(
            (atom.element == "C" and atom_name not in {"C", "CA"} and not is_polar_carbon)
            or atom.element == "S"
        ),
        reason="residue-template atom typing",
    )


def _type_ligand_atom(
    atom: AtomRecord,
    bond_graph: dict[str, tuple[AtomRecord, ...]] | None = None,
) -> AtomTyping:
    neighbors = bond_graph.get(atom.label, ()) if bond_graph is not None else ()
    heavy_neighbors = tuple(neighbor for neighbor in neighbors if neighbor.element not in {"D", "H"})
    is_oxygen = atom.element == "O"
    is_sulfur = atom.element == "S"
    is_carbon = atom.element == "C"
    is_nitrogen = atom.element == "N"
    bonded_hydrogen = any(neighbor.element in {"D", "H"} for neighbor in neighbors)
    aromatic = is_carbon and _looks_like_ligand_aromatic_atom(atom, neighbors)
    confidence = (
        0.95
        if atom.formal_charge
        else 0.78
        if neighbors
        else 0.70
        if is_oxygen
        else 0.50
        if is_sulfur
        else 0.45
        if aromatic
        else 0.30
    )
    # Crystal structures frequently lack explicit H.  For nitrogen with
    # 1–2 heavy-atom neighbours (sp/sp²), assume donor capability — the
    # missing H is likely present but unresolved.  Nitrogen with ≥3
    # heavy neighbours is fully substituted and cannot donate.
    # Oxygen/sulfur are conservative: only donors with explicit H or
    # formal charge (carbonyl/ether are almost never donors).
    n_donor = is_nitrogen and (
        bonded_hydrogen or atom.formal_charge > 0 or (bool(heavy_neighbors) and len(heavy_neighbors) < 3)
    )
    os_donor = (is_oxygen or is_sulfur) and (bonded_hydrogen or atom.formal_charge > 0)
    likely_donor = n_donor or os_donor
    # Carbons bonded to O/N are polar, not hydrophobic (aligned with PLIP)
    ligand_hydrophobic = (
        is_carbon and not any(neighbor.element in {"O", "N"} for neighbor in neighbors)
    ) or atom.element in {"CL", "BR", "I", "F"}
    # Nitrogen with <3 heavy neighbours is protonatable → potential positive
    # (aligned with PLIP's OpenBabel-based charge assignment at phys. pH)
    n_protonatable = is_nitrogen and bool(heavy_neighbors) and len(heavy_neighbors) < 3
    return AtomTyping(
        donor=likely_donor,
        acceptor=is_oxygen or is_sulfur,
        positive=(atom.formal_charge > 0) or n_protonatable,
        negative=atom.formal_charge < 0,
        aromatic=aromatic,
        hydrophobic=ligand_hydrophobic,
        confidence=confidence,
        reason=(
            "explicit formal charge with element typing"
            if atom.formal_charge
            else "distance-perceived ligand bond environment"
            if neighbors
            else "element-only ligand oxygen typing"
            if is_oxygen
            else "element-only ligand sulfur typing"
            if is_sulfur
            else "element-only ligand carbon typing"
            if is_carbon
            else "ligand nitrogen protonation and bond order unknown"
            if atom.element == "N"
            else "no ligand atom-typing rule"
        ),
    )


def describe_ligand_atom_types(ligand: ResidueRecord) -> tuple[str, ...]:
    ligand_atoms = _heavy_atoms(ligand)
    graph = _ligand_bond_graph(ligand.atoms)
    return tuple(
        (
            f"{atom.label}: donor={typing.donor}, acceptor={typing.acceptor}, "
            f"positive={typing.positive}, negative={typing.negative}, aromatic={typing.aromatic}, "
            f"hydrophobic={typing.hydrophobic}, confidence={typing.confidence:.2f}"
        )
        for atom in ligand_atoms
        for typing in (_type_ligand_atom(atom, graph),)
    )
