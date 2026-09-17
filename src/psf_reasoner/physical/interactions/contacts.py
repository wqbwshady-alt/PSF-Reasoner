"""Interaction predicates plus the ring-centroid and water-bridge factories.

The interaction-type cutoffs are read through :mod:`.constants` (not imported
by value) so that the cutoff sweep in :mod:`.sensitivity` still sees them.

:class:`~psf_reasoner.physical.interactions.analysis.Interaction` is imported
inside the two factory functions on purpose: :mod:`.analysis` imports this
module at import time, so a module-level import here would close a cycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.interactions import constants
from psf_reasoner.physical.interactions.geometry import _centroid_distance
from psf_reasoner.physical.interactions.typing import AtomTyping, _type_ligand_atom, _type_protein_atom
from psf_reasoner.physical.structure import AtomRecord, ResidueRecord

if TYPE_CHECKING:
    from psf_reasoner.physical.interactions.analysis import Interaction


def _forms_hydrogen_bond(first: AtomTyping, second: AtomTyping) -> bool:
    return (first.donor and second.acceptor) or (second.donor and first.acceptor)


def _forms_salt_bridge(first: AtomTyping, second: AtomTyping) -> bool:
    return (first.positive and second.negative) or (first.negative and second.positive)


def _pi_interaction(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    protein_atoms: tuple[AtomRecord, ...],
    ligand_atoms: tuple[AtomRecord, ...],
    ligand_graph: dict[str, tuple[AtomRecord, ...]],
) -> Interaction | None:
    from psf_reasoner.physical.interactions.analysis import Interaction

    del residue, ligand
    protein_ring = tuple(atom for atom in protein_atoms if _type_protein_atom(atom).aromatic)
    ligand_ring = tuple(atom for atom in ligand_atoms if _type_ligand_atom(atom, ligand_graph).aromatic)
    if not protein_ring or not ligand_ring:
        return None
    distance = _centroid_distance(protein_ring, ligand_ring)
    if distance > constants.PI_CENTROID_CUTOFF_ANGSTROM:
        return None
    return Interaction(
        interaction_type="pi_interaction",
        protein_atom=",".join(atom.label for atom in protein_ring),
        ligand_atom=",".join(atom.label for atom in ligand_ring),
        distance_angstrom=round(distance, 3),
        geometry="aromatic ring centroid cutoff",
        confidence=0.55,
    )


def _water_bridge_events(
    waters: tuple[ResidueRecord, ...],
    protein_atoms: tuple[AtomRecord, ...],
    ligand_atoms: tuple[AtomRecord, ...],
    ligand_graph: dict[str, tuple[AtomRecord, ...]],
) -> tuple[Interaction, ...]:
    from psf_reasoner.physical.interactions.analysis import Interaction

    interactions: list[Interaction] = []
    for water in waters:
        for water_atom in (atom for atom in water.atoms if atom.element == "O"):
            protein_partner = next(
                (
                    protein_atom
                    for protein_atom in protein_atoms
                    if atom_distance(water_atom, protein_atom) <= constants.HYDROGEN_BOND_CUTOFF_ANGSTROM
                    and (_type_protein_atom(protein_atom).donor or _type_protein_atom(protein_atom).acceptor)
                ),
                None,
            )
            ligand_partner = next(
                (
                    ligand_atom
                    for ligand_atom in ligand_atoms
                    if atom_distance(water_atom, ligand_atom) <= constants.HYDROGEN_BOND_CUTOFF_ANGSTROM
                    and (
                        _type_ligand_atom(ligand_atom, ligand_graph).donor
                        or _type_ligand_atom(ligand_atom, ligand_graph).acceptor
                    )
                ),
                None,
            )
            if protein_partner is not None and ligand_partner is not None:
                interactions.append(
                    Interaction(
                        interaction_type="water_bridge",
                        protein_atom=protein_partner.label,
                        ligand_atom=ligand_partner.label,
                        distance_angstrom=round(
                            atom_distance(water_atom, protein_partner)
                            + atom_distance(water_atom, ligand_partner),
                            3,
                        ),
                        geometry="resolved water within donor/acceptor cutoffs to protein and ligand",
                        confidence=0.60,
                        mediator=water_atom.label,
                    )
                )
    return tuple(interactions)
