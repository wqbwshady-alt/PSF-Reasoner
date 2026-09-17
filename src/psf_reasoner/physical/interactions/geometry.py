"""Hydrogen-bond geometry helpers: angles, estimated H positions, centroids.

Depends only on :mod:`.graph` (for distance-perceived bonding) and on the
constants it needs; it never imports :mod:`.typing` at runtime — the atom
typing record is used for annotations only.
"""

from __future__ import annotations

from math import acos, degrees
from typing import TYPE_CHECKING

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.interactions.constants import HYDROGEN_BOND_MIN_ANGLE_DEGREES
from psf_reasoner.physical.interactions.graph import _likely_bonded
from psf_reasoner.physical.structure import AtomRecord, ResidueRecord

if TYPE_CHECKING:
    from psf_reasoner.physical.interactions.typing import AtomTyping


def _passes_hydrogen_bond_geometry(
    protein_atom: AtomRecord,
    ligand_atom: AtomRecord,
    residue: ResidueRecord,
    ligand: ResidueRecord,
    protein_type: AtomTyping,
    ligand_type: AtomTyping,
) -> bool:
    donor = protein_atom if protein_type.donor else ligand_atom
    acceptor = ligand_atom if protein_type.donor else protein_atom
    donor_residue = residue if protein_type.donor else ligand

    # Prefer explicit hydrogens
    hydrogens = tuple(
        atom
        for atom in donor_residue.atoms
        if atom.element in {"D", "H"} and atom_distance(atom, donor) <= 1.25
    )
    if hydrogens:
        return any(
            _angle_degrees(donor, hydrogen, acceptor) >= HYDROGEN_BOND_MIN_ANGLE_DEGREES
            for hydrogen in hydrogens
        )

    # No explicit H — estimate H position from donor geometry
    estimated_h = _estimate_hydrogen_position(donor, donor_residue)
    if estimated_h is not None:
        angle = _angle_degrees(estimated_h, donor, acceptor)
        if angle >= HYDROGEN_BOND_MIN_ANGLE_DEGREES:
            return True

    # Fallback: use heavy-atom base–donor–acceptor angle as a proxy.
    # If the donor's base points toward the acceptor, geometry is acceptable
    # even when the H-position estimate is imprecise.
    bases = _donor_base_atoms(donor, donor_residue)
    if not bases:
        return True  # cannot judge — conservative accept
    for base in bases:
        base_angle = _angle_degrees(base, donor, acceptor)
        if base_angle >= 90.0:  # relaxed vs 110° H-bond minimum
            return True
    return False


def _donor_base_atoms(donor: AtomRecord, residue: ResidueRecord) -> list[AtomRecord]:
    """Return heavy atoms bonded to *donor* (the 'base' for angle proxy)."""
    return [
        atom
        for atom in residue.atoms
        if atom.element not in {"D", "H"} and atom.label != donor.label and _likely_bonded(donor, atom)
    ]


def _estimate_hydrogen_position(donor: AtomRecord, residue: ResidueRecord) -> AtomRecord | None:
    """Estimate the polar hydrogen position from heavy-atom geometry.

    - 1 base atom (e.g. hydroxyl O–H): H is placed opposite the base.
    - 2 base atoms (sp², e.g. backbone N–H): H is placed in the plane
      bisecting the two bond directions.
    - ≥3 base atoms: the donor is fully substituted → no H (returns None).
    """
    bases = [
        atom
        for atom in residue.atoms
        if atom.element not in {"D", "H"} and atom.label != donor.label and _likely_bonded(donor, atom)
    ]
    if not bases or len(bases) >= 3:
        return None

    if len(bases) == 1:
        b = bases[0]
        dx = donor.x - b.x
        dy = donor.y - b.y
        dz = donor.z - b.z
    else:
        # Two bases: place H opposite to their bisector
        b1, b2 = bases[0], bases[1]
        v1 = (donor.x - b1.x, donor.y - b1.y, donor.z - b1.z)
        v2 = (donor.x - b2.x, donor.y - b2.y, donor.z - b2.z)
        dx = v1[0] + v2[0]
        dy = v1[1] + v2[1]
        dz = v1[2] + v2[2]

    length = (dx * dx + dy * dy + dz * dz) ** 0.5
    if length < 0.001:
        return None

    scale = 1.0 / length
    return AtomRecord(
        residue=donor.residue,
        name="H_est",
        element="H",
        x=donor.x + dx * scale,
        y=donor.y + dy * scale,
        z=donor.z + dz * scale,
        occupancy=1.0,
        altloc=None,
        formal_charge=0,
    )


def _angle_degrees(first: AtomRecord, vertex: AtomRecord, third: AtomRecord) -> float:
    vector_a = (first.x - vertex.x, first.y - vertex.y, first.z - vertex.z)
    vector_b = (third.x - vertex.x, third.y - vertex.y, third.z - vertex.z)
    norm_a = sum(component * component for component in vector_a) ** 0.5
    norm_b = sum(component * component for component in vector_b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    cosine = sum(a * b for a, b in zip(vector_a, vector_b, strict=True)) / (norm_a * norm_b)
    return degrees(acos(max(-1.0, min(1.0, cosine))))


def _centroid_distance(first: tuple[AtomRecord, ...], second: tuple[AtomRecord, ...]) -> float:
    first_centroid = _centroid(first)
    second_centroid = _centroid(second)
    return (
        (first_centroid[0] - second_centroid[0]) ** 2
        + (first_centroid[1] - second_centroid[1]) ** 2
        + (first_centroid[2] - second_centroid[2]) ** 2
    ) ** 0.5


def _centroid(atoms: tuple[AtomRecord, ...]) -> tuple[float, float, float]:
    return tuple(sum(getattr(atom, axis) for atom in atoms) / len(atoms) for axis in ("x", "y", "z"))  # type: ignore[return-value]


def _heavy_atoms(residue: ResidueRecord) -> tuple[AtomRecord, ...]:
    return tuple(atom for atom in residue.atoms if atom.element not in {"D", "H"})
