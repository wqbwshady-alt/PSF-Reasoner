"""Atom-typed, conservative interaction classifiers — package facade.

Re-exports the historical flat-module surface so that existing import paths
keep working::

    from psf_reasoner.physical.interactions import analyze_typed_interactions

Private helpers are re-exported too because callers (and the interaction
tests) import some of them by name.  Layer order, imports only ever point
downwards::

    constants -> graph -> geometry / typing -> contacts -> analysis -> sensitivity
"""

from __future__ import annotations

from psf_reasoner.physical.interactions.analysis import (
    Interaction,
    InteractionAnalysis,
    InteractionCounts,
    analyze_typed_interactions,
    count_typed_interactions,
)
from psf_reasoner.physical.interactions.constants import (
    HYDROGEN_BOND_CUTOFF_ANGSTROM,
    HYDROGEN_BOND_MIN_ANGLE_DEGREES,
    HYDROPHOBIC_CUTOFF_ANGSTROM,
    PI_CENTROID_CUTOFF_ANGSTROM,
    SALT_BRIDGE_CUTOFF_ANGSTROM,
)
from psf_reasoner.physical.interactions.contacts import (
    _forms_hydrogen_bond,
    _forms_salt_bridge,
    _pi_interaction,
    _water_bridge_events,
)
from psf_reasoner.physical.interactions.geometry import (
    _angle_degrees,
    _centroid,
    _centroid_distance,
    _donor_base_atoms,
    _estimate_hydrogen_position,
    _heavy_atoms,
    _passes_hydrogen_bond_geometry,
)
from psf_reasoner.physical.interactions.graph import (
    _ligand_bond_graph,
    _likely_bonded,
    _looks_like_ligand_aromatic_atom,
)
from psf_reasoner.physical.interactions.sensitivity import (
    _classify_stability,
    cutoff_sensitivity_analysis,
)
from psf_reasoner.physical.interactions.typing import (
    ACCEPTOR_ATOMS,
    AROMATIC_RESIDUE_ATOMS,
    DONOR_ATOMS,
    NEGATIVE_ATOMS,
    POLAR_CARBON_ATOMS,
    POSITIVE_ATOMS,
    AtomTyping,
    _type_ligand_atom,
    _type_protein_atom,
    describe_ligand_atom_types,
)

__all__ = [
    "ACCEPTOR_ATOMS",
    "AROMATIC_RESIDUE_ATOMS",
    "DONOR_ATOMS",
    "HYDROGEN_BOND_CUTOFF_ANGSTROM",
    "HYDROGEN_BOND_MIN_ANGLE_DEGREES",
    "HYDROPHOBIC_CUTOFF_ANGSTROM",
    "NEGATIVE_ATOMS",
    "PI_CENTROID_CUTOFF_ANGSTROM",
    "POLAR_CARBON_ATOMS",
    "POSITIVE_ATOMS",
    "SALT_BRIDGE_CUTOFF_ANGSTROM",
    "AtomTyping",
    "Interaction",
    "InteractionAnalysis",
    "InteractionCounts",
    "_angle_degrees",
    "_centroid",
    "_centroid_distance",
    "_classify_stability",
    "_donor_base_atoms",
    "_estimate_hydrogen_position",
    "_forms_hydrogen_bond",
    "_forms_salt_bridge",
    "_heavy_atoms",
    "_ligand_bond_graph",
    "_likely_bonded",
    "_looks_like_ligand_aromatic_atom",
    "_passes_hydrogen_bond_geometry",
    "_pi_interaction",
    "_type_ligand_atom",
    "_type_protein_atom",
    "_water_bridge_events",
    "analyze_typed_interactions",
    "count_typed_interactions",
    "cutoff_sensitivity_analysis",
    "describe_ligand_atom_types",
]
