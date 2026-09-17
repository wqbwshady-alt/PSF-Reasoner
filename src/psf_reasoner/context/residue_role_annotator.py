"""Residue functional role annotation (V3 P1).

Classifies each residue in a structure by its functional role relative
to the ligand, using geometric criteria and sequence-level annotations.
"""

from __future__ import annotations

from enum import StrEnum

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import ResidueRecord


class ResidueRole(StrEnum):
    """Functional role of a residue in the structure."""

    LIGAND_CONTACT = "ligand_contact"  # within 4 Å of ligand
    POCKET_LINING = "pocket_lining"  # within 6 Å of ligand
    POCKET_SHELL = "pocket_shell"  # within 8 Å of ligand
    CATALYTIC = "catalytic"  # known catalytic residue
    DIMER_INTERFACE = "dimer_interface"  # at protein-protein interface
    SURFACE = "surface"  # solvent-exposed, not in pocket
    BURIED = "buried"  # low SASA, not in pocket
    METAL_BINDING = "metal_binding"  # coordinates a metal ion
    UNKNOWN = "unknown"


# Known catalytic residue patterns for common protein families.
# Keyed by (PDB residue name, expected role).  These are curated annotations
# that supplement geometric classification.
_CATALYTIC_MOTIFS: dict[str, frozenset[str]] = {
    # HIV-1 protease catalytic dyad
    "HIV_PROTEASE": frozenset({"ASP25"}),
    # DHFR — catalytic aspartate (protonates substrate)
    "DHFR": frozenset({"ASP27", "GLU30"}),
    # Serine protease catalytic triad
    "TRYPSIN": frozenset({"HIS57", "ASP102", "SER195"}),
    # Kinase catalytic residues (HRD motif + DFG motif)
    "KINASE": frozenset({"ASP166", "LYS168", "ASP184", "PHE185"}),
    # β-lactamase catalytic serine
    "BETA_LACTAMASE": frozenset({"SER70", "LYS73", "SER130", "GLU166"}),
}


def classify_residue_role(
    residue: ResidueRecord,
    ligand: ResidueRecord | None = None,
    metals: tuple[ResidueRecord, ...] = (),
    dimer_chains: frozenset[str] = frozenset(),
    protein_family_hint: str = "",
) -> set[ResidueRole]:
    """Classify a single residue's functional role(s).

    A residue can have multiple roles (e.g., catalytic + ligand_contact).
    Returns an empty set only when the role cannot be determined.
    """
    roles: set[ResidueRole] = set()

    if residue.is_hetero or residue.is_water:
        return roles

    residue_label = residue.identity.label

    # -- Catalytic annotation from curated motifs -------------------------
    for family, catalytic_set in _CATALYTIC_MOTIFS.items():
        if (
            protein_family_hint.upper() == family or _matches_family(residue_label, family)
        ) and _residue_name_matches(residue_label, catalytic_set):
            roles.add(ResidueRole.CATALYTIC)

    # -- Metal binding ----------------------------------------------------
    for metal in metals:
        metal_atoms = [a for a in metal.atoms if a.element not in {"D", "H"}]
        residue_atoms = [a for a in residue.atoms if a.element not in {"D", "H"}]
        if any(atom_distance(ra, ma) <= 3.0 for ra in residue_atoms for ma in metal_atoms):
            roles.add(ResidueRole.METAL_BINDING)

    # -- Ligand proximity classification ----------------------------------
    if ligand is not None:
        ligand_atoms = [a for a in ligand.atoms if a.element not in {"D", "H"}]
        residue_atoms = [a for a in residue.atoms if a.element not in {"D", "H"}]
        min_dist = (
            min(atom_distance(ra, la) for ra in residue_atoms for la in ligand_atoms)
            if residue_atoms and ligand_atoms
            else float("inf")
        )

        if min_dist <= 4.0:
            roles.add(ResidueRole.LIGAND_CONTACT)
        if min_dist <= 6.0:
            roles.add(ResidueRole.POCKET_LINING)
        if min_dist <= 8.0:
            roles.add(ResidueRole.POCKET_SHELL)

    # -- Dimer interface --------------------------------------------------
    if residue.identity.chain in dimer_chains:
        roles.add(ResidueRole.DIMER_INTERFACE)

    if not roles:
        roles.add(ResidueRole.UNKNOWN)

    return roles


def annotate_mutation_site(
    residue: ResidueRecord,
    ligand: ResidueRecord | None = None,
    metals: tuple[ResidueRecord, ...] = (),
    **kwargs,
) -> dict:
    """Produce a detailed annotation dict for the mutation site (V3 P1).

    Returns a structured dict suitable for JSON serialisation in the
    Structural Context output.
    """
    roles = classify_residue_role(residue, ligand, metals, **kwargs)
    residue_atoms = [a for a in residue.atoms if a.element not in {"D", "H"}]
    ligand_atoms = [a for a in ligand.atoms if a.element not in {"D", "H"}] if ligand else []

    # Nearest ligand atom and distance
    nearest_dist = None
    nearest_pair = None
    if ligand_atoms and residue_atoms:
        for ra in residue_atoms:
            for la in ligand_atoms:
                d = atom_distance(ra, la)
                if nearest_dist is None or d < nearest_dist:
                    nearest_dist = d
                    nearest_pair = (ra.label, la.label)

    return {
        "residue_label": residue.identity.label,
        "residue_name": residue.identity.name,
        "chain": residue.identity.chain,
        "residue_number": residue.identity.number,
        "roles": sorted(r.value for r in roles),
        "is_catalytic": ResidueRole.CATALYTIC in roles,
        "is_ligand_contact": ResidueRole.LIGAND_CONTACT in roles,
        "is_pocket_lining": ResidueRole.POCKET_LINING in roles,
        "nearest_ligand_distance": round(nearest_dist, 3) if nearest_dist else None,
        "nearest_ligand_atom_pair": nearest_pair,
        "heavy_atom_count": len(residue_atoms),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _matches_family(residue_label: str, family: str) -> bool:
    """Heuristic family matching from residue label patterns (not used
    when protein_family_hint is provided)."""
    return False  # relies on explicit protein_family_hint


def _residue_name_matches(label: str, candidates: frozenset[str]) -> bool:
    """Check if *label* (e.g. 'A:ASP25') matches any candidate (e.g. 'ASP25')."""
    return any(label.endswith(":" + candidate) or label == candidate for candidate in candidates)
