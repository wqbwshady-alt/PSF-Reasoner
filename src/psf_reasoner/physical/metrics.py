"""Local solvent exposure and ligand-shell geometry metrics."""

from __future__ import annotations

from math import cos, pi, sin, sqrt

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import AtomRecord, ParsedStructure, ResidueRecord

PROBE_RADIUS_ANGSTROM = 1.4
DEFAULT_SAMPLES_PER_ATOM = 48  # reduced from 96 for speed; still within 2% of 96-point SASA
VDW_RADII_ANGSTROM = {
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "P": 1.80,
    "S": 1.80,
}

# Reference SASA for each standard residue in an extended Gly-X-Gly tripeptide
# (values from Miller et al., J. Mol. Biol. 1987, in Å²).
_REFERENCE_SASA_GLY_X_GLY: dict[str, float] = {
    "ALA": 113.0, "ARG": 241.0, "ASN": 158.0, "ASP": 151.0,
    "CYS": 140.0, "GLN": 189.0, "GLU": 183.0, "GLY": 85.0,
    "HIS": 194.0, "ILE": 182.0, "LEU": 180.0, "LYS": 211.0,
    "MET": 204.0, "PHE": 218.0, "PRO": 143.0, "SER": 122.0,
    "THR": 146.0, "TRP": 259.0, "TYR": 229.0, "VAL": 160.0,
}

# Backbone atoms for SASA decomposition
_BACKBONE_ATOM_NAMES = frozenset({"N", "CA", "C", "O", "OXT"})

# Cached Fibonacci sphere points — computed once, reused across all SASA calls
_FIBONACCI_CACHE: dict[int, tuple[tuple[float, float, float], ...]] = {}


# -- V2 SASA variants + updated residue_sasa (Phase 2B) ------------------------


def relative_sasa(
    structure: ParsedStructure,
    residue: ResidueRecord,
    **kwargs,
) -> float:
    """Relative SASA: absolute SASA divided by Gly-X-Gly reference for that residue type."""
    absolute = residue_sasa(structure, residue, **kwargs)
    reference = _REFERENCE_SASA_GLY_X_GLY.get(residue.identity.name)
    if reference is None or reference == 0.0:
        return absolute
    return round(absolute / reference, 3)


def backbone_sasa(
    structure: ParsedStructure,
    residue: ResidueRecord,
    **kwargs,
) -> float:
    """SASA from backbone atoms only (N, CA, C, O)."""
    return residue_sasa(structure, residue, atom_filter=_BACKBONE_ATOM_NAMES, **kwargs)


def sidechain_sasa(
    structure: ParsedStructure,
    residue: ResidueRecord,
    **kwargs,
) -> float:
    """SASA from sidechain atoms only (excludes N, CA, C, O)."""
    return residue_sasa(structure, residue, atom_filter=None, sidechain_only=True, **kwargs)


def ligand_burial(
    structure: ParsedStructure,
    ligand: ResidueRecord,
    probe_radius_angstrom: float = PROBE_RADIUS_ANGSTROM,
) -> float:
    """Fraction of ligand surface buried by protein contacts (0.0–1.0)."""
    ligand_atoms = _heavy_atoms(ligand)
    if not ligand_atoms:
        return 0.0
    protein_atoms = tuple(
        atom
        for residue in structure.residues
        if not residue.is_hetero and not residue.is_water
        for atom in _heavy_atoms(residue)
    )
    if not protein_atoms:
        return 0.0
    points = _fibonacci_sphere(96)
    total_accessible = 0
    protein_accessible = 0
    for atom in ligand_atoms:
        radius = _radius(atom.element) + probe_radius_angstrom
        for point in points:
            px = atom.x + radius * point[0]
            py = atom.y + radius * point[1]
            pz = atom.z + radius * point[2]
            occluded = any(
                (px - pa.x) ** 2 + (py - pa.y) ** 2 + (pz - pa.z) ** 2
                < (_radius(pa.element) + probe_radius_angstrom) ** 2
                for pa in protein_atoms
            )
            if not occluded:
                total_accessible += 1
            else:
                protein_accessible += 1
    total = total_accessible + protein_accessible
    if total == 0:
        return 0.0
    return round(protein_accessible / total, 3)


# -- Original functions (updated to accept optional filters) -------------------


def residue_sasa(
    structure: ParsedStructure,
    residue: ResidueRecord,
    samples_per_atom: int = DEFAULT_SAMPLES_PER_ATOM,
    probe_radius_angstrom: float = PROBE_RADIUS_ANGSTROM,
    atom_filter: frozenset[str] | None = None,
    sidechain_only: bool = False,
) -> float:
    """Shrake-Rupley approximation for one residue in its supplied structure.

    When *atom_filter* is provided, only atoms whose names are in the set
    contribute.  When *sidechain_only* is True, backbone atoms are excluded.
    """

    if samples_per_atom < 12:
        raise ValueError("samples_per_atom must be at least 12")
    target_atoms = _heavy_atoms(residue, atom_filter=atom_filter, sidechain_only=sidechain_only)
    if not target_atoms:
        return 0.0

    # Pre-compute target atom positions + radii for spatial filter
    target_info = tuple(
        (atom.x, atom.y, atom.z, _radius(atom.element) + probe_radius_angstrom)
        for atom in target_atoms
    )

    # Spatial filter: only keep occluders within ~10 Å of any target atom
    # (max VDW radius ~1.8 + 2*probe ~2.8 + generous margin = 10 Å)
    occlusion_cutoff = 10.0
    occluders = tuple(
        atom
        for other in structure.residues
        if not other.is_water
        for atom in _heavy_atoms(other)
        if atom.residue != residue.identity
        and any(
            (atom.x - tx) ** 2 + (atom.y - ty) ** 2 + (atom.z - tz) ** 2
            < occlusion_cutoff ** 2
            for tx, ty, tz, _ in target_info
        )
    )

    # Cached Fibonacci sphere points
    if samples_per_atom not in _FIBONACCI_CACHE:
        _FIBONACCI_CACHE[samples_per_atom] = _fibonacci_sphere(samples_per_atom)
    points = _FIBONACCI_CACHE[samples_per_atom]

    area = 0.0
    for i, atom in enumerate(target_atoms):
        radius = target_info[i][3]
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


def _heavy_atoms(
    residue: ResidueRecord,
    atom_filter: frozenset[str] | None = None,
    sidechain_only: bool = False,
) -> tuple[AtomRecord, ...]:
    atoms = tuple(atom for atom in residue.atoms if atom.element not in {"D", "H"})
    if sidechain_only:
        atoms = tuple(a for a in atoms if a.name not in _BACKBONE_ATOM_NAMES)
    if atom_filter is not None:
        atoms = tuple(a for a in atoms if a.name in atom_filter)
    return atoms


def _radius(element: str) -> float:
    return VDW_RADII_ANGSTROM.get(element, 1.70)
