"""External interaction validation — compare PSF-Reasoner against PLIP.

PLIP (Protein-Ligand Interaction Profiler) is a well-established tool for
detecting non-covalent protein-ligand interactions.  This module runs both
PSF-Reasoner's interaction engine and PLIP on the same structures and
reports agreement rates and systematic differences.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from psf_reasoner.physical.interactions import (
    InteractionCounts,
    count_typed_interactions,
)


@dataclass
class PerTypeAgreement:
    """Agreement metrics for a single interaction type."""

    interaction_type: str
    psf_count: int
    plip_count: int
    match: bool = False
    notes: str = ""


@dataclass
class InteractionComparison:
    """Side-by-side comparison of PSF-Reasoner vs PLIP on one structure."""

    pdb_path: str
    ligand_id: str
    psf_counts: InteractionCounts
    plip_counts: dict[str, int] = field(default_factory=dict)
    by_type: list[PerTypeAgreement] = field(default_factory=list)
    psf_hydrophobic_residues: frozenset[str] = frozenset()
    plip_hydrophobic_residues: frozenset[str] = frozenset()

    @property
    def total_agreement_rate(self) -> float:
        """Fraction of categories with equal raw counts, not scientific accuracy."""
        matching = sum(1 for a in self.by_type if a.match)
        return matching / len(self.by_type) if self.by_type else 0.0

    @property
    def hydrophobic_residue_precision(self) -> float | None:
        """Fraction of PSF-positive protein residues also found by PLIP."""
        if not self.psf_hydrophobic_residues:
            return None
        return len(self.psf_hydrophobic_residues & self.plip_hydrophobic_residues) / len(
            self.psf_hydrophobic_residues
        )

    @property
    def hydrophobic_residue_recall(self) -> float | None:
        """Fraction of PLIP-positive protein residues also found by PSF."""
        if not self.plip_hydrophobic_residues:
            return None
        return len(self.psf_hydrophobic_residues & self.plip_hydrophobic_residues) / len(
            self.plip_hydrophobic_residues
        )


def run_plip_on_structure(pdb_path: Path, ligand_id: str) -> dict[str, int]:
    """Run PLIP on a PDB file and return interaction counts by type.

    Requires PLIP to be installed: ``pip install plip``.

    Returns a dict mapping PLIP interaction type names to integer counts.
    PLIP types are mapped to PSF-Reasoner-compatible keys:
      - hydrogen_bond (hbonds_pdon + hbonds_ldon)
      - hydrophobic_contact (hydrophobic_contacts)
      - salt_bridge (saltbridge_lneg + saltbridge_pneg)
      - pi_stacking (pistacking)
      - pi_cation (pication_laro + pication_paro)
      - water_bridge (water_bridges)
      - halogen_bond (halogen_bonds)
    """
    counts, _ = _run_plip_with_residues(pdb_path, ligand_id)
    return counts


def _run_plip_with_residues(pdb_path: Path, ligand_id: str) -> tuple[dict[str, int], frozenset[str]]:
    """Return PLIP event counts and protein residues with hydrophobic contacts."""
    try:
        from plip.structure.preparation import PDBComplex
    except ImportError as error:
        raise ImportError(
            "PLIP is required for external validation.  Install with: pip install plip"
        ) from error

    mol = PDBComplex()
    mol.load_pdb(str(pdb_path))
    mol.analyze()

    # PLIP identifies ligands by "RES:CHAIN:NUM" (e.g., "MK1:B:902").
    # Match by residue name prefix.
    matching = [v for k, v in mol.interaction_sets.items() if k.split(":")[0].upper() == ligand_id.upper()]
    if not matching:
        raise ValueError(f"PLIP did not identify ligand {ligand_id} in {pdb_path}")
    if len(matching) > 1:
        raise ValueError(f"PLIP identified multiple {ligand_id} ligands in {pdb_path}; select one")
    interactions = matching[0]

    counts = {
        "hydrogen_bond": (len(interactions.hbonds_pdon) + len(interactions.hbonds_ldon)),
        "hydrophobic_contact": len(interactions.hydrophobic_contacts),
        "salt_bridge": (len(interactions.saltbridge_lneg) + len(interactions.saltbridge_pneg)),
        "pi_stacking": len(interactions.pistacking),
        "pi_cation": (len(interactions.pication_laro) + len(interactions.pication_paro)),
        "water_bridge": len(interactions.water_bridges),
        "halogen_bond": len(interactions.halogen_bonds),
    }
    hydrophobic_residues = frozenset(
        f"{event.reschain}:{event.restype}{event.resnr}" for event in interactions.hydrophobic_contacts
    )
    return counts, hydrophobic_residues


_SYSTEMATIC_DIFFERENCES: dict[str, str] = {
    "hydrogen_bond": (
        "PSF uses a 3.5 A donor-acceptor cutoff and inferred donor typing; "
        "PLIP uses OpenBabel protonation and may report longer donor-acceptor distances. "
        "Compare atom pairs and geometry before interpreting count differences."
    ),
    "hydrophobic_contact": (
        "PSF counts every qualifying atom pair within 4.0 A. PLIP filters "
        "hydrophobic events differently. Compare residue presence as well as raw counts."
    ),
    "salt_bridge": ("PSF uses charged atom pairs within 5.5 A; PLIP uses charge-group centers."),
    "pi_interaction": (
        "PSF uses a single 'pi_interaction' category based on aromatic residue atom "
        "tables and centroid distance (5.5 A). PLIP distinguishes pi-stacking "
        "(face-to-face and edge-to-face) from pi-cation interactions, and uses "
        "ring perception via OpenBabel. PSF's name-based aromaticity is less "
        "accurate than PLIP's SMARTS-based detection."
    ),
    "water_bridge": (
        "PSF uses distance-only partner selection (water O within 3.5 A of both "
        "protein and ligand donor/acceptor atoms). PLIP uses hydrogen-bond "
        "geometry on both sides of the water. PSF may over-count water bridges."
    ),
}


def _parse_structure_with_gemmi(path: Path):
    """Parse a PDB/mmCIF file into PSF-Reasoner residue records via gemmi."""
    import gemmi

    from psf_reasoner.physical.structure import AtomRecord, ResidueIdentity, ResidueRecord

    structure = gemmi.read_structure(str(path))
    model = structure[0]
    residues = []
    for chain in model:
        for residue in chain:
            # gemmi's make_minimal_pdb() may prepend chain ID to residue
            # names in PDB format (3-char limit).  Use the residue name
            # from gemmi's own data model, which is always correct.
            res_name = residue.name
            identity = ResidueIdentity(
                chain=chain.name,
                name=res_name,
                number=int(residue.seqid.num),
                insertion_code=residue.seqid.icode.strip() or None,
            )
            atoms = tuple(
                AtomRecord(
                    residue=identity,
                    name=atom.name,
                    element=atom.element.name.upper(),
                    x=atom.pos.x,
                    y=atom.pos.y,
                    z=atom.pos.z,
                    occupancy=atom.occ,
                    altloc=atom.altloc,
                    formal_charge=atom.charge,
                )
                for atom in residue
            )
            residues.append(
                ResidueRecord(
                    identity=identity,
                    one_letter_code=None,
                    is_hetero=(residue.het_flag == "H"),
                    atoms=atoms,
                )
            )
    return residues


def compare_interactions(pdb_path: Path, ligand_id: str) -> InteractionComparison:
    """Run PSF-Reasoner and PLIP on the same structure and compare results.

    Returns an ``InteractionComparison`` with per-type agreement metrics.
    """
    if not pdb_path.is_file():
        raise FileNotFoundError(pdb_path)
    # --- PSF-Reasoner ---
    residues = _parse_structure_with_gemmi(pdb_path)

    # Locate ligand residue
    ligand_residues = [r for r in residues if r.identity.name.upper() == ligand_id.upper()]
    if not ligand_residues:
        raise ValueError(f"PSF did not identify ligand {ligand_id} in {pdb_path}")
    if len(ligand_residues) > 1:
        raise ValueError(f"PSF identified multiple {ligand_id} ligands in {pdb_path}; select one")

    ligand = ligand_residues[0]
    waters = tuple(r for r in residues if r.is_water)

    # Collect interactions for all protein residues near the ligand
    total_hb = 0
    total_hp = 0
    total_sb = 0
    total_pi = 0
    total_wb = 0
    psf_hydrophobic_residues: set[str] = set()
    for residue in residues:
        if residue.is_hetero or residue.is_water:
            continue
        counts = count_typed_interactions(residue, ligand, waters)
        total_hb += counts.hydrogen_bonds
        total_hp += counts.hydrophobic_contacts
        total_sb += counts.salt_bridges
        total_pi += counts.pi_interactions
        total_wb += counts.water_bridges
        if counts.hydrophobic_contacts:
            psf_hydrophobic_residues.add(
                f"{residue.identity.chain}:{residue.identity.name}{residue.identity.number}"
            )

    psf_counts = InteractionCounts(
        hydrogen_bonds=total_hb,
        hydrophobic_contacts=total_hp,
        salt_bridges=total_sb,
        pi_interactions=total_pi,
        water_bridges=total_wb,
    )

    # --- PLIP (requires PDB format) ---
    # PLIP only supports PDB format. Convert CIF/mmCIF to PDB if needed.
    suffix = pdb_path.suffix.lower()
    if suffix in {".cif", ".mmcif"}:
        import tempfile as _tmp

        import gemmi as _gemmi

        _structure = _gemmi.read_structure(str(pdb_path))
        _pdb_text = _structure.make_minimal_pdb()
        _lines = [line for line in _pdb_text.splitlines() if not line.startswith("ANISOU")]
        if _lines and not _lines[-1].startswith("END"):
            _lines.append("END")
        with _tmp.NamedTemporaryFile(suffix=".pdb", mode="w", delete=False) as _f:
            _f.write("\n".join(_lines) + "\n")
            _pdb_path = Path(_f.name)
        try:
            plip_counts, plip_hydrophobic_residues = _run_plip_with_residues(_pdb_path, ligand_id)
        finally:
            _pdb_path.unlink(missing_ok=True)
    else:
        plip_counts, plip_hydrophobic_residues = _run_plip_with_residues(pdb_path, ligand_id)

    # --- Compare ---
    by_type = [
        PerTypeAgreement(
            interaction_type="hydrogen_bond",
            psf_count=psf_counts.hydrogen_bonds,
            plip_count=plip_counts.get("hydrogen_bond", 0),
            match=psf_counts.hydrogen_bonds == plip_counts.get("hydrogen_bond", -1),
            notes=_SYSTEMATIC_DIFFERENCES["hydrogen_bond"]
            if psf_counts.hydrogen_bonds != plip_counts.get("hydrogen_bond", -1)
            else "",
        ),
        PerTypeAgreement(
            interaction_type="hydrophobic_contact",
            psf_count=psf_counts.hydrophobic_contacts,
            plip_count=plip_counts.get("hydrophobic_contact", 0),
            match=psf_counts.hydrophobic_contacts == plip_counts.get("hydrophobic_contact", -1),
            notes="",
        ),
        PerTypeAgreement(
            interaction_type="salt_bridge",
            psf_count=psf_counts.salt_bridges,
            plip_count=plip_counts.get("salt_bridge", 0),
            match=psf_counts.salt_bridges == plip_counts.get("salt_bridge", -1),
            notes="",
        ),
        PerTypeAgreement(
            interaction_type="pi_interaction",
            psf_count=psf_counts.pi_interactions,
            plip_count=plip_counts.get("pi_stacking", 0) + plip_counts.get("pi_cation", 0),
            match=psf_counts.pi_interactions
            == plip_counts.get("pi_stacking", 0) + plip_counts.get("pi_cation", 0),
            notes=_SYSTEMATIC_DIFFERENCES["pi_interaction"],
        ),
        PerTypeAgreement(
            interaction_type="water_bridge",
            psf_count=psf_counts.water_bridges,
            plip_count=plip_counts.get("water_bridge", 0),
            match=psf_counts.water_bridges == plip_counts.get("water_bridge", -1),
            notes=_SYSTEMATIC_DIFFERENCES["water_bridge"]
            if psf_counts.water_bridges != plip_counts.get("water_bridge", -1)
            else "",
        ),
    ]

    return InteractionComparison(
        pdb_path=str(pdb_path),
        ligand_id=ligand_id,
        psf_counts=psf_counts,
        plip_counts=plip_counts,
        by_type=by_type,
        psf_hydrophobic_residues=frozenset(psf_hydrophobic_residues),
        plip_hydrophobic_residues=plip_hydrophobic_residues,
    )
