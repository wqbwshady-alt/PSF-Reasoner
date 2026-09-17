"""Distance-perceived ligand bond graph.

This is the lowest layer of the package apart from :mod:`.constants`: it only
depends on :mod:`psf_reasoner.physical.geometry` and the structure records, so
every other submodule may import it.
"""

from __future__ import annotations

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import AtomRecord


def _ligand_bond_graph(atoms: tuple[AtomRecord, ...]) -> dict[str, tuple[AtomRecord, ...]]:
    graph: dict[str, list[AtomRecord]] = {atom.label: [] for atom in atoms}
    for index, atom in enumerate(atoms):
        for other in atoms[index + 1 :]:
            if _likely_bonded(atom, other):
                graph[atom.label].append(other)
                graph[other.label].append(atom)
    return {label: tuple(neighbors) for label, neighbors in graph.items()}


def _likely_bonded(first: AtomRecord, second: AtomRecord) -> bool:
    cutoff = 1.25 if first.element in {"D", "H"} or second.element in {"D", "H"} else 1.90
    return atom_distance(first, second) <= cutoff


def _looks_like_ligand_aromatic_atom(atom: AtomRecord, neighbors: tuple[AtomRecord, ...]) -> bool:
    if atom.element != "C":
        return False
    carbon_like_neighbors = sum(neighbor.element in {"C", "N"} for neighbor in neighbors)
    aromatic_name_hint = atom.name.upper().startswith(("C", "CA", "CB", "CG", "CD", "CE", "CZ"))
    return carbon_like_neighbors >= 2 or (aromatic_name_hint and len(neighbors) >= 2)
