"""Local solvent exposure and ligand-shell geometry metrics."""

from __future__ import annotations

from math import cos, pi, sin, sqrt

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import AtomRecord, ParsedStructure, ResidueRecord

PROBE_RADIUS_ANGSTROM = 1.4
VDW_RADII_ANGSTROM = {
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "P": 1.80,
    "S": 1.80,
}


def residue_sasa(
    structure: ParsedStructure,
    residue: ResidueRecord,
    samples_per_atom: int = 96,
    probe_radius_angstrom: float = PROBE_RADIUS_ANGSTROM,
) -> float:
    """Shrake-Rupley approximation for one residue in its supplied structure."""

    if samples_per_atom < 12:
        raise ValueError("samples_per_atom must be at least 12")
    target_atoms = _heavy_atoms(residue)
    occluders = tuple(
        atom
        for other in structure.residues
        if not other.is_water
        for atom in _heavy_atoms(other)
        if atom.residue != residue.identity
    )
    points = _fibonacci_sphere(samples_per_atom)
    area = 0.0
    for atom in target_atoms:
        radius = _radius(atom.element) + probe_radius_angstrom
        accessible = sum(
            not any(
                _point_is_occluded(atom, point, radius, occluder, probe_radius_angstrom)
                for occluder in occluders
            )
            for point in points
        )
        area += 4.0 * pi * radius**2 * accessible / samples_per_atom
    return area


def ligand_shell_bounding_box_volume(
    structure: ParsedStructure,
    ligand: ResidueRecord,
    shell_radius_angstrom: float = 6.0,
) -> tuple[float, int]:
    """Return a local geometry proxy, not a cavity-volume estimate."""

    ligand_atoms = _heavy_atoms(ligand)
    shell_atoms = tuple(
        atom
        for residue in structure.residues
        if not residue.is_hetero and not residue.is_water
        for atom in _heavy_atoms(residue)
        if any(atom_distance(atom, ligand_atom) <= shell_radius_angstrom for ligand_atom in ligand_atoms)
    )
    if not shell_atoms:
        return 0.0, 0
    x_values = [atom.x for atom in shell_atoms]
    y_values = [atom.y for atom in shell_atoms]
    z_values = [atom.z for atom in shell_atoms]
    volume = (
        (max(x_values) - min(x_values)) * (max(y_values) - min(y_values)) * (max(z_values) - min(z_values))
    )
    return volume, len(shell_atoms)


def _point_is_occluded(
    atom: AtomRecord,
    point: tuple[float, float, float],
    radius: float,
    occluder: AtomRecord,
    probe_radius: float,
) -> bool:
    point_x = atom.x + radius * point[0]
    point_y = atom.y + radius * point[1]
    point_z = atom.z + radius * point[2]
    occluder_radius = _radius(occluder.element) + probe_radius
    return (point_x - occluder.x) ** 2 + (point_y - occluder.y) ** 2 + (
        point_z - occluder.z
    ) ** 2 < occluder_radius**2


def _fibonacci_sphere(samples: int) -> tuple[tuple[float, float, float], ...]:
    golden_angle = pi * (3.0 - sqrt(5.0))
    return tuple(
        (
            sqrt(1.0 - y * y) * cos(index * golden_angle),
            y,
            sqrt(1.0 - y * y) * sin(index * golden_angle),
        )
        for index in range(samples)
        for y in (1.0 - 2.0 * (index + 0.5) / samples,)
    )


def _heavy_atoms(residue: ResidueRecord) -> tuple[AtomRecord, ...]:
    return tuple(atom for atom in residue.atoms if atom.element not in {"D", "H"})


def _radius(element: str) -> float:
    return VDW_RADII_ANGSTROM.get(element, 1.70)
