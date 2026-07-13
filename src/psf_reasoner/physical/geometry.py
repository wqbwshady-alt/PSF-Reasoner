"""Deterministic coordinate geometry used by physical evidence providers."""

from __future__ import annotations

from dataclasses import dataclass
from math import dist

from psf_reasoner.physical.structure import AtomRecord, ResidueRecord


@dataclass(frozen=True, slots=True)
class AtomPairDistance:
    first: AtomRecord
    second: AtomRecord
    angstrom: float


def atom_distance(first: AtomRecord, second: AtomRecord) -> float:
    return dist((first.x, first.y, first.z), (second.x, second.y, second.z))


def nearest_heavy_atom_pair(
    first: ResidueRecord,
    second: ResidueRecord,
) -> AtomPairDistance | None:
    first_atoms = tuple(atom for atom in first.atoms if atom.element not in {"D", "H"})
    second_atoms = tuple(atom for atom in second.atoms if atom.element not in {"D", "H"})
    if not first_atoms or not second_atoms:
        return None
    return min(
        (
            AtomPairDistance(
                first=first_atom,
                second=second_atom,
                angstrom=atom_distance(first_atom, second_atom),
            )
            for first_atom in first_atoms
            for second_atom in second_atoms
        ),
        key=lambda pair: pair.angstrom,
    )
