"""Atom-typed interaction analysis: the data model and the assembly loop.

This is the only module that pulls the other layers together — typing,
contacts, geometry and graph.  The distance cutoffs are read through
:mod:`.constants` at call time so that the cutoff sweep in :mod:`.sensitivity`
keeps working exactly as it did when everything lived in one module.
"""

from __future__ import annotations

from dataclasses import dataclass

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.interactions import constants
from psf_reasoner.physical.interactions.contacts import (
    _forms_hydrogen_bond,
    _forms_salt_bridge,
    _pi_interaction,
    _water_bridge_events,
)
from psf_reasoner.physical.interactions.geometry import _heavy_atoms, _passes_hydrogen_bond_geometry
from psf_reasoner.physical.interactions.graph import _ligand_bond_graph
from psf_reasoner.physical.interactions.typing import AtomTyping, _type_ligand_atom, _type_protein_atom
from psf_reasoner.physical.structure import ResidueRecord

# ``AtomTyping`` is defined in the typing layer and re-exported here, so the
# data model of the engine is reachable from a single module.
__all__ = [
    "AtomTyping",
    "Interaction",
    "InteractionAnalysis",
    "InteractionCounts",
    "analyze_typed_interactions",
    "count_typed_interactions",
]

# Interaction-type discriminators.
HYDROGEN_BOND_TYPE = "hydrogen_bond"
HYDROPHOBIC_CONTACT_TYPE = "hydrophobic_contact"
SALT_BRIDGE_TYPE = "salt_bridge"
PI_INTERACTION_TYPE = "pi_interaction"
WATER_BRIDGE_TYPE = "water_bridge"


@dataclass(frozen=True, slots=True)
class InteractionCounts:
    hydrogen_bonds: int
    hydrophobic_contacts: int
    salt_bridges: int
    pi_interactions: int
    water_bridges: int


@dataclass(frozen=True, slots=True)
class Interaction:
    interaction_type: str
    protein_atom: str
    ligand_atom: str
    distance_angstrom: float
    geometry: str
    confidence: float
    mediator: str | None = None


@dataclass(frozen=True, slots=True)
class InteractionAnalysis:
    interactions: tuple[Interaction, ...]

    @property
    def counts(self) -> InteractionCounts:
        return InteractionCounts(
            hydrogen_bonds=sum(item.interaction_type == HYDROGEN_BOND_TYPE for item in self.interactions),
            hydrophobic_contacts=sum(
                item.interaction_type == HYDROPHOBIC_CONTACT_TYPE for item in self.interactions
            ),
            salt_bridges=sum(item.interaction_type == SALT_BRIDGE_TYPE for item in self.interactions),
            pi_interactions=sum(item.interaction_type == PI_INTERACTION_TYPE for item in self.interactions),
            water_bridges=sum(item.interaction_type == WATER_BRIDGE_TYPE for item in self.interactions),
        )


def count_typed_interactions(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    waters: tuple[ResidueRecord, ...],
) -> InteractionCounts:
    return analyze_typed_interactions(residue, ligand, waters).counts


def analyze_typed_interactions(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    waters: tuple[ResidueRecord, ...],
) -> InteractionAnalysis:
    protein_atoms = _heavy_atoms(residue)
    ligand_atoms = _heavy_atoms(ligand)
    ligand_graph = _ligand_bond_graph(ligand.atoms)
    interactions: list[Interaction] = []
    for protein_atom in protein_atoms:
        protein_type = _type_protein_atom(protein_atom)
        for ligand_atom in ligand_atoms:
            ligand_type = _type_ligand_atom(ligand_atom, ligand_graph)
            distance = atom_distance(protein_atom, ligand_atom)
            if (
                distance <= constants.HYDROGEN_BOND_CUTOFF_ANGSTROM
                and _forms_hydrogen_bond(protein_type, ligand_type)
                and _passes_hydrogen_bond_geometry(
                    protein_atom, ligand_atom, residue, ligand, protein_type, ligand_type
                )
            ):
                interactions.append(
                    Interaction(
                        interaction_type=HYDROGEN_BOND_TYPE,
                        protein_atom=protein_atom.label,
                        ligand_atom=ligand_atom.label,
                        distance_angstrom=round(distance, 3),
                        geometry="donor-acceptor pair with distance/angle geometry check",
                        confidence=round(min(protein_type.confidence, ligand_type.confidence, 0.82), 3),
                    )
                )
            if (
                distance <= constants.HYDROPHOBIC_CUTOFF_ANGSTROM
                and protein_type.hydrophobic
                and ligand_type.hydrophobic
            ):
                interactions.append(
                    Interaction(
                        interaction_type=HYDROPHOBIC_CONTACT_TYPE,
                        protein_atom=protein_atom.label,
                        ligand_atom=ligand_atom.label,
                        distance_angstrom=round(distance, 3),
                        geometry="heavy-atom hydrophobic contact cutoff",
                        confidence=round(min(protein_type.confidence, ligand_type.confidence, 0.75), 3),
                    )
                )
            if distance <= constants.SALT_BRIDGE_CUTOFF_ANGSTROM and _forms_salt_bridge(
                protein_type, ligand_type
            ):
                interactions.append(
                    Interaction(
                        interaction_type=SALT_BRIDGE_TYPE,
                        protein_atom=protein_atom.label,
                        ligand_atom=ligand_atom.label,
                        distance_angstrom=round(distance, 3),
                        geometry="oppositely charged atom-pair cutoff",
                        confidence=round(min(protein_type.confidence, ligand_type.confidence, 0.85), 3),
                    )
                )
    pi_interaction = _pi_interaction(residue, ligand, protein_atoms, ligand_atoms, ligand_graph)
    if pi_interaction is not None:
        interactions.append(pi_interaction)
    interactions.extend(_water_bridge_events(waters, protein_atoms, ligand_atoms, ligand_graph))
    return InteractionAnalysis(tuple(interactions))
