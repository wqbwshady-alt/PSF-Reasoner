"""Ligand chemical fragment decomposition (V3 P1).

Breaks a ligand into chemically meaningful fragments — rings, charged
groups, H-bond donors/acceptors, hydrophobic regions, rotatable tails —
so the reasoning engine can map mutation effects to specific chemical
features rather than treating the ligand as an opaque blob.
"""

from __future__ import annotations

from dataclasses import dataclass

from psf_reasoner.physical.structure import ResidueRecord


@dataclass
class ChemicalFragment:
    """One chemically meaningful substructure of a ligand."""

    fragment_id: str
    fragment_type: str  # ring, charged_group, hbond_donor, hbond_acceptor, hydrophobic, linker
    atoms: tuple[str, ...]  # atom labels
    description: str = ""
    charge: int = 0
    aromatic: bool = False


@dataclass
class LigandDecomposition:
    """Full chemical decomposition of a ligand into fragments."""

    ligand_identifier: str
    heavy_atom_count: int
    fragments: tuple[ChemicalFragment, ...]
    overall_charge: int = 0
    rotatable_bonds: int = 0
    hbond_donors: int = 0
    hbond_acceptors: int = 0
    logP_estimate: float = 0.0


# ---------------------------------------------------------------------------
# Known ligand decomposition tables (curated for common PDB ligands)
# ---------------------------------------------------------------------------

_KNOWN_LIGANDS: dict[str, LigandDecomposition] = {
    "MK1": LigandDecomposition(
        ligand_identifier="MK1",
        heavy_atom_count=38,
        overall_charge=0,
        rotatable_bonds=6,
        hbond_donors=3,
        hbond_acceptors=6,
        logP_estimate=3.2,
        fragments=(
            ChemicalFragment("MK1_core", "ring", (), "Central hydroxyethylene isostere core", aromatic=False),
            ChemicalFragment("MK1_p1", "ring", (), "P1 phenyl ring (S2 pocket)", aromatic=True),
            ChemicalFragment("MK1_p1prime", "ring", (), "P1' phenyl ring (S1' pocket)", aromatic=True),
            ChemicalFragment(
                "MK1_p2", "ring", (), "P2 t-butyl-carboxamide group (S2 pocket)", aromatic=False
            ),
            ChemicalFragment(
                "MK1_p2prime", "ring", (), "P2' pyridyl-methyl group (S2' pocket)", aromatic=True
            ),
        ),
    ),
    "MTX": LigandDecomposition(
        ligand_identifier="MTX",
        heavy_atom_count=33,
        overall_charge=-2,
        rotatable_bonds=8,
        hbond_donors=5,
        hbond_acceptors=8,
        logP_estimate=-0.2,
        fragments=(
            ChemicalFragment(
                "MTX_pteridine",
                "ring",
                (),
                "2,4-diaminopteridine ring — binds in DHFR active site",
                aromatic=True,
            ),
            ChemicalFragment(
                "MTX_paba",
                "ring",
                (),
                "para-aminobenzoate group — linker between pteridine and glutamate",
                aromatic=True,
            ),
            ChemicalFragment(
                "MTX_glutamate",
                "charged_group",
                (),
                "Glutamate tail — charged carboxylates at physiological pH",
                charge=-2,
            ),
        ),
    ),
}


def decompose_ligand(ligand: ResidueRecord, ligand_identifier: str) -> LigandDecomposition:
    """Decompose a ligand into chemically meaningful fragments.

    Uses a curated table for known ligands; falls back to a heuristic
    decomposition for unknown ligands.
    """
    key = ligand_identifier.upper().strip()
    if key in _KNOWN_LIGANDS:
        decomposition = _KNOWN_LIGANDS[key]
        # Update atom count from actual structure
        heavy = sum(1 for a in ligand.atoms if a.element not in {"D", "H"})
        return LigandDecomposition(
            ligand_identifier=decomposition.ligand_identifier,
            heavy_atom_count=heavy,
            fragments=decomposition.fragments,
            overall_charge=decomposition.overall_charge,
            rotatable_bonds=decomposition.rotatable_bonds,
            hbond_donors=decomposition.hbond_donors,
            hbond_acceptors=decomposition.hbond_acceptors,
            logP_estimate=decomposition.logP_estimate,
        )

    # Fallback heuristic for unknown ligands
    return _heuristic_decomposition(ligand, ligand_identifier)


def _heuristic_decomposition(ligand: ResidueRecord, identifier: str) -> LigandDecomposition:
    """Basic heuristic decomposition for ligands not in the curated table."""
    heavy_atoms = tuple(a for a in ligand.atoms if a.element not in {"D", "H"})
    n_heavy = len(heavy_atoms)
    n_donors = sum(1 for a in heavy_atoms if a.element == "N" or (a.element == "O" and a.formal_charge == 0))
    n_acceptors = sum(1 for a in heavy_atoms if a.element in {"O", "N"})

    return LigandDecomposition(
        ligand_identifier=identifier,
        heavy_atom_count=n_heavy,
        overall_charge=sum(a.formal_charge for a in heavy_atoms),
        rotatable_bonds=0,  # requires bond order — not available from coordinates alone
        hbond_donors=min(n_donors, n_heavy // 3),
        hbond_acceptors=min(n_acceptors, n_heavy // 2),
        fragments=(
            ChemicalFragment(
                f"{identifier}_unknown",
                "ring",
                tuple(a.label for a in heavy_atoms),
                f"Uncurated ligand — {n_heavy} heavy atoms, "
                f"approximate H-bond donors={n_donors}, acceptors={n_acceptors}",
            ),
        ),
    )
