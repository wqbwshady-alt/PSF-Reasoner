"""Pocket volume, shape complementarity, and cavity analysis (V2 Phase 2C).

Provides a lightweight grid-based pocket volume estimate that replaces the
bounding-box proxy.  For production use, the Cloud Run fpocket integration
(``cloud/fpocket-src/``) gives validated cavity volumes.
"""

from __future__ import annotations

from math import sqrt

from psf_reasoner.physical.structure import AtomRecord, ParsedStructure, ResidueRecord

# Grid resolution in Angstrom per voxel.  0.5 A balances accuracy with
# compute cost for on-the-fly analysis.
_GRID_SPACING_ANGSTROM = 0.5

# Pocket radius around ligand (same as operational pocket definition).
_POCKET_RADIUS_ANGSTROM = 6.0


def grid_pocket_volume(
    structure: ParsedStructure,
    ligand: ResidueRecord,
    grid_spacing: float = _GRID_SPACING_ANGSTROM,
    pocket_radius: float = _POCKET_RADIUS_ANGSTROM,
) -> float:
    """Estimate pocket cavity volume around *ligand* using a 3D occupancy grid.

    Returns volume in Å³.  The estimate is a lower bound — grid points
    inside protein atoms or outside the pocket radius are excluded.
    """
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

    # Bounding box of ligand + pocket radius
    lx = [a.x for a in ligand_atoms]
    ly = [a.y for a in ligand_atoms]
    lz = [a.z for a in ligand_atoms]
    min_x = min(lx) - pocket_radius
    max_x = max(lx) + pocket_radius
    min_y = min(ly) - pocket_radius
    max_y = max(ly) + pocket_radius
    min_z = min(lz) - pocket_radius
    max_z = max(lz) + pocket_radius

    # Ligand centroid for radius check
    cx = sum(lx) / len(lx)
    cy = sum(ly) / len(ly)
    cz = sum(lz) / len(lz)
    radius_sq = pocket_radius * pocket_radius

    cavity_count = 0
    x = min_x
    while x <= max_x:
        y = min_y
        while y <= max_y:
            z = min_z
            while z <= max_z:
                # Must be within pocket radius of ligand centroid
                if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 > radius_sq:
                    z += grid_spacing
                    continue
                # Must not be inside any protein atom
                inside_protein = any(
                    (x - pa.x) ** 2 + (y - pa.y) ** 2 + (z - pa.z) ** 2 < _vdw_radius_sq(pa.element)
                    for pa in protein_atoms
                )
                if not inside_protein:
                    # Must not be inside any ligand atom
                    inside_ligand = any(
                        (x - la.x) ** 2 + (y - la.y) ** 2 + (z - la.z) ** 2 < _vdw_radius_sq(la.element)
                        for la in ligand_atoms
                    )
                    if not inside_ligand:
                        cavity_count += 1
                z += grid_spacing
            y += grid_spacing
        x += grid_spacing

    return cavity_count * (grid_spacing**3)


def shape_complementarity(
    structure: ParsedStructure,
    ligand: ResidueRecord,
    pocket_radius: float = _POCKET_RADIUS_ANGSTROM,
) -> float:
    """Estimate shape complementarity (0.0–1.0) within the ligand pocket.

    High values indicate good geometric fit between ligand and protein
    surface.  Computed as the fraction of ligand-surface grid points
    that are in contact with protein atoms.
    """
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

    # Sample points on the ligand's accessible surface
    points = _sample_ligand_surface(ligand_atoms)
    if not points:
        return 0.0

    contact_count = 0
    for px, py, pz in points:
        for pa in protein_atoms:
            dist_sq = (px - pa.x) ** 2 + (py - pa.y) ** 2 + (pz - pa.z) ** 2
            vdw_sq = _vdw_radius_sq(pa.element)
            # Within 1.5 A of protein vdW surface = contact
            contact_radius_sq = (sqrt(vdw_sq) + 1.5) ** 2
            if dist_sq < contact_radius_sq:
                contact_count += 1
                break

    return round(contact_count / len(points), 3)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _heavy_atoms(residue: ResidueRecord) -> tuple[AtomRecord, ...]:
    return tuple(a for a in residue.atoms if a.element not in {"D", "H"})


def _vdw_radius_sq(element: str) -> float:
    radii = {"C": 1.70, "N": 1.55, "O": 1.52, "P": 1.80, "S": 1.80}
    r = radii.get(element, 1.70)
    return r * r


def _sample_ligand_surface(
    atoms: tuple[AtomRecord, ...],
    samples_per_atom: int = 24,
) -> tuple[tuple[float, float, float], ...]:
    """Generate points on the solvent-accessible surface of ligand atoms."""
    from math import cos, pi, sin

    points: list[tuple[float, float, float]] = []
    for atom in atoms:
        r = sqrt(_vdw_radius_sq(atom.element)) + 1.4  # + probe radius
        for i in range(samples_per_atom):
            theta = 2.0 * pi * i / samples_per_atom
            for j in range(max(4, samples_per_atom // 2)):
                phi = pi * (j + 0.5) / max(4, samples_per_atom // 2)
                points.append(
                    (
                        atom.x + r * sin(phi) * cos(theta),
                        atom.y + r * sin(phi) * sin(theta),
                        atom.z + r * cos(phi),
                    )
                )
    return tuple(points)
