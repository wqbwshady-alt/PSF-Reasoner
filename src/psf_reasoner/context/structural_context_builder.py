"""Structural Context Builder (V3 P1).

Produces a unified, machine-readable JSON context that replaces raw
PDB coordinates with structured semantic information for the reasoning
engine.  This is the single source of truth that both the causal
mechanism graph and the LLM reasoner consume.

Output schema (StructuralContext):
  - identity: protein, organism, PDB IDs, mutation, ligand
  - mutation_site: functional roles, distances, chemical property changes
  - neighborhoods: 4/6/8 Å residue lists with per-residue annotations
  - ligand_decomposition: chemical fragments (from ligand_fragmenter)
  - structural_differences: atom-level WT vs mutant comparison
  - quality: QC summary
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from psf_reasoner.context.ligand_fragmenter import LigandDecomposition, decompose_ligand
from psf_reasoner.context.residue_role_annotator import (
    ResidueRole,
    annotate_mutation_site,
    classify_residue_role,
)
from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import (
    AtomRecord,
    ParsedStructure,
    ResidueRecord,
    StructureParser,
)
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.preparation import QCGrade, StructureQCReport


@dataclass
class NeighborhoodResidue:
    """A residue in the mutation site's local neighborhood."""

    label: str
    residue_name: str
    chain: str
    number: int
    distance_to_mutation: float  # nearest heavy-atom distance in Å
    distance_to_ligand: float | None
    roles: list[str] = field(default_factory=list)
    is_catalytic: bool = False


@dataclass
class StructuralDifferences:
    """Atom-level WT vs mutant differences at the mutation site."""

    sidechain_volume_change: str = ""       # "increased" | "decreased" | "unchanged"
    polarity_change: str = ""               # "polar_added" | "polar_removed" | "unchanged"
    charge_change: str = ""                 # "+1" | "-1" | "0" | etc.
    aromaticity_change: str = ""            # "aromatic_added" | "aromatic_removed" | "unchanged"
    hbond_donor_change: str = ""            # "gained" | "lost" | "unchanged"
    hbond_acceptor_change: str = ""         # "gained" | "lost" | "unchanged"
    contact_changes: list[dict] = field(default_factory=list)
    interaction_changes: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class StructuralContext:
    """Complete structural context for a single mutation analysis (V3 P1).

    This is the primary output of the Structural Context Builder and
    serves as input to the causal mechanism graph and LLM reasoner.
    """

    # Identity
    protein_name: str = ""
    organism: str = ""
    uniprot_accession: str | None = None
    wt_pdb_id: str = ""
    mutant_pdb_id: str | None = None
    chain: str = ""
    mutation_notation: str = ""
    ligand_identifier: str = ""
    ligand_role: str = "inhibitor"

    # Mutation site annotation
    mutation_site: dict | None = None

    # Multi-scale neighborhoods
    neighborhood_4a: list[dict] = field(default_factory=list)
    neighborhood_6a: list[dict] = field(default_factory=list)
    neighborhood_8a: list[dict] = field(default_factory=list)

    # Ligand chemistry
    ligand_decomposition: dict | None = None

    # Structural differences
    structural_differences: dict | None = None

    # Quality
    qc_grade: str = ""
    qc_notes: list[str] = field(default_factory=list)


class StructuralContextBuilder:
    """Build a StructuralContext from an AnalysisRequest.

    Usage::

        builder = StructuralContextBuilder()
        context = builder.build(request)
        # context is a dataclass; use dataclasses.asdict() for JSON
    """

    def __init__(self, parser: StructureParser | None = None) -> None:
        self._parser = parser or StructureParser()

    def build(
        self,
        request: AnalysisRequest,
        qc_report: StructureQCReport | None = None,
        protein_family_hint: str = "",
    ) -> StructuralContext:
        """Produce the full structural context for *request*."""
        if request.mutant_structure is None:
            raise ValueError("StructuralContextBuilder requires paired WT/mutant structures")

        reference = self._parser.parse(request.structure)
        mutant = self._parser.parse(request.mutant_structure)
        ref_ligand = reference.locate_ligand(request.ligand)
        mut_ligand = mutant.locate_ligand(request.ligand)

        ctx = StructuralContext(
            protein_name=protein_family_hint or "unknown",
            wt_pdb_id=request.structure.path,
            mutant_pdb_id=request.mutant_structure.path,
            chain=request.mutation.chain if request.mutation else "",
            mutation_notation=request.mutation.notation if request.mutation else "",
            ligand_identifier=request.ligand.identifier,
        )

        # -- QC -----------------------------------------------------------
        if qc_report:
            ctx.qc_grade = qc_report.grade.value
            ctx.qc_notes = [i.message for i in qc_report.issues]

        # -- Mutation site -------------------------------------------------
        if request.mutation:
            ref_sites = reference.locate_mutation_residues(request.mutation)
            mut_sites = mutant.locate_mutant_residues(request.mutation)
            if ref_sites and mut_sites:
                ctx.mutation_site = annotate_mutation_site(
                    ref_sites[0], ref_ligand,
                    protein_family_hint=protein_family_hint,
                )
                # Add mutant residue info
                if ctx.mutation_site:
                    ctx.mutation_site["mutant_residue_name"] = mut_sites[0].identity.name

        # -- Neighborhoods -------------------------------------------------
        if request.mutation and ref_sites:
            mutation_residue = ref_sites[0]
            ctx.neighborhood_4a = self._build_neighborhood(
                reference, mutation_residue, ref_ligand, 4.0, protein_family_hint
            )
            ctx.neighborhood_6a = self._build_neighborhood(
                reference, mutation_residue, ref_ligand, 6.0, protein_family_hint
            )
            ctx.neighborhood_8a = self._build_neighborhood(
                reference, mutation_residue, ref_ligand, 8.0, protein_family_hint
            )

        # -- Ligand decomposition ------------------------------------------
        decomp = decompose_ligand(ref_ligand, request.ligand.identifier)
        ctx.ligand_decomposition = {
            "identifier": decomp.ligand_identifier,
            "heavy_atom_count": decomp.heavy_atom_count,
            "overall_charge": decomp.overall_charge,
            "hbond_donors": decomp.hbond_donors,
            "hbond_acceptors": decomp.hbond_acceptors,
            "rotatable_bonds": decomp.rotatable_bonds,
            "logP_estimate": decomp.logP_estimate,
            "fragments": [
                {
                    "id": f.fragment_id,
                    "type": f.fragment_type,
                    "description": f.description,
                    "charge": f.charge,
                    "aromatic": f.aromatic,
                }
                for f in decomp.fragments
            ],
        }

        # -- Structural differences ----------------------------------------
        if request.mutation and ref_sites and mut_sites:
            ctx.structural_differences = self._compare_residues(
                ref_sites[0], mut_sites[0],
                reference, mutant, ref_ligand, mut_ligand,
            )

        return ctx

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_neighborhood(
        self,
        structure: ParsedStructure,
        center: ResidueRecord,
        ligand: ResidueRecord,
        radius: float,
        protein_family_hint: str,
    ) -> list[dict]:
        """Return residues within *radius* Å of *center*, annotated."""
        center_atoms = [a for a in center.atoms if a.element not in {"D", "H"}]
        ligand_atoms = [a for a in ligand.atoms if a.element not in {"D", "H"}]
        results: list[NeighborhoodResidue] = []
        seen: set[str] = set()

        for residue in structure.residues:
            if residue.is_hetero or residue.is_water:
                continue
            label = residue.identity.label
            if label == center.identity.label or label in seen:
                continue
            seen.add(label)

            res_atoms = [a for a in residue.atoms if a.element not in {"D", "H"}]
            if not res_atoms or not center_atoms:
                continue

            min_dist = min(
                atom_distance(ra, ca)
                for ra in res_atoms
                for ca in center_atoms
            )
            if min_dist > radius:
                continue

            # Distance to ligand
            lig_dist = None
            if ligand_atoms:
                lig_dist = min(
                    atom_distance(ra, la)
                    for ra in res_atoms
                    for la in ligand_atoms
                )

            roles = classify_residue_role(
                residue, ligand,
                protein_family_hint=protein_family_hint,
            )

            results.append(NeighborhoodResidue(
                label=label,
                residue_name=residue.identity.name,
                chain=residue.identity.chain,
                number=residue.identity.number,
                distance_to_mutation=round(min_dist, 3),
                distance_to_ligand=round(lig_dist, 3) if lig_dist is not None else None,
                roles=sorted(r.value for r in roles),
                is_catalytic=ResidueRole.CATALYTIC in roles,
            ))

        results.sort(key=lambda r: r.distance_to_mutation)
        return [
            {
                "label": r.label,
                "residue_name": r.residue_name,
                "chain": r.chain,
                "number": r.number,
                "distance_to_mutation": r.distance_to_mutation,
                "distance_to_ligand": r.distance_to_ligand,
                "roles": r.roles,
                "is_catalytic": r.is_catalytic,
            }
            for r in results
        ]

    @staticmethod
    def _compare_residues(
        ref_res: ResidueRecord,
        mut_res: ResidueRecord,
        ref_structure: ParsedStructure,
        mut_structure: ParsedStructure,
        ref_ligand: ResidueRecord,
        mut_ligand: ResidueRecord,
    ) -> dict:
        """Compare WT and mutant residues at atomic level."""
        ref_heavy = {a.name: a for a in ref_res.atoms if a.element not in {"D", "H"}}
        mut_heavy = {a.name: a for a in mut_res.atoms if a.element not in {"D", "H"}}

        # Chemical property changes
        ref_props = _residue_properties(ref_res.identity.name)
        mut_props = _residue_properties(mut_res.identity.name)

        differences: dict[str, Any] = {
            "wild_type": ref_res.identity.name,
            "mutant": mut_res.identity.name,
            "site_label": ref_res.identity.label,
        }

        # Volume
        vol_change = mut_props.get("volume", 0) - ref_props.get("volume", 0)
        if vol_change > 10:
            differences["sidechain_volume_change"] = "increased"
        elif vol_change < -10:
            differences["sidechain_volume_change"] = "decreased"
        else:
            differences["sidechain_volume_change"] = "unchanged"
        differences["volume_delta"] = vol_change

        # Polarity
        ref_polar = ref_props.get("polar", False)
        mut_polar = mut_props.get("polar", False)
        if mut_polar and not ref_polar:
            differences["polarity_change"] = "polar_added"
        elif ref_polar and not mut_polar:
            differences["polarity_change"] = "polar_removed"
        else:
            differences["polarity_change"] = "unchanged"

        # Charge
        ref_charge = ref_props.get("charge", 0)
        mut_charge = mut_props.get("charge", 0)
        charge_delta = mut_charge - ref_charge
        differences["charge_change"] = f"{'+' if charge_delta > 0 else ''}{charge_delta}"

        # Aromaticity
        ref_arom = ref_props.get("aromatic", False)
        mut_arom = mut_props.get("aromatic", False)
        if mut_arom and not ref_arom:
            differences["aromaticity_change"] = "aromatic_added"
        elif ref_arom and not mut_arom:
            differences["aromaticity_change"] = "aromatic_removed"
        else:
            differences["aromaticity_change"] = "unchanged"

        # H-bond capability
        ref_donor = ref_props.get("hbond_donor", False)
        mut_donor = mut_props.get("hbond_donor", False)
        if mut_donor and not ref_donor:
            differences["hbond_donor_change"] = "gained"
        elif ref_donor and not mut_donor:
            differences["hbond_donor_change"] = "lost"
        else:
            differences["hbond_donor_change"] = "unchanged"

        ref_acc = ref_props.get("hbond_acceptor", False)
        mut_acc = mut_props.get("hbond_acceptor", False)
        if mut_acc and not ref_acc:
            differences["hbond_acceptor_change"] = "gained"
        elif ref_acc and not mut_acc:
            differences["hbond_acceptor_change"] = "lost"
        else:
            differences["hbond_acceptor_change"] = "unchanged"

        # Atom-level changes
        gained_atoms = sorted(set(mut_heavy) - set(ref_heavy))
        lost_atoms = sorted(set(ref_heavy) - set(mut_heavy))
        differences["gained_atoms"] = gained_atoms
        differences["lost_atoms"] = lost_atoms

        # Contact changes with ligand
        ref_lig_atoms = [a for a in ref_ligand.atoms if a.element not in {"D", "H"}]
        mut_lig_atoms = [a for a in mut_ligand.atoms if a.element not in {"D", "H"}]

        ref_contacts = []
        for ra in ref_heavy.values():
            for la in ref_lig_atoms:
                d = atom_distance(ra, la)
                if d <= 4.0:
                    ref_contacts.append((ra.label, la.label, round(d, 3)))

        mut_contacts = []
        for ma in mut_heavy.values():
            for la in mut_lig_atoms:
                d = atom_distance(ma, la)
                if d <= 4.0:
                    mut_contacts.append((ma.label, la.label, round(d, 3)))

        differences["reference_contacts"] = [
            {"residue_atom": c[0], "ligand_atom": c[1], "distance": c[2]}
            for c in ref_contacts
        ]
        differences["mutant_contacts"] = [
            {"residue_atom": c[0], "ligand_atom": c[1], "distance": c[2]}
            for c in mut_contacts
        ]
        differences["contact_count_delta"] = len(mut_contacts) - len(ref_contacts)

        return differences


# ---------------------------------------------------------------------------
# Residue property table (volume in Å³, approximate)
# ---------------------------------------------------------------------------

_RESIDUE_PROPERTIES: dict[str, dict] = {
    "ALA": {"volume": 88.6, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
    "ARG": {"volume": 173.4, "polar": True, "charge": 1, "aromatic": False, "hbond_donor": True, "hbond_acceptor": False},
    "ASN": {"volume": 114.1, "polar": True, "charge": 0, "aromatic": False, "hbond_donor": True, "hbond_acceptor": True},
    "ASP": {"volume": 111.1, "polar": True, "charge": -1, "aromatic": False, "hbond_donor": False, "hbond_acceptor": True},
    "CYS": {"volume": 108.5, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": True, "hbond_acceptor": False},
    "GLN": {"volume": 143.8, "polar": True, "charge": 0, "aromatic": False, "hbond_donor": True, "hbond_acceptor": True},
    "GLU": {"volume": 138.4, "polar": True, "charge": -1, "aromatic": False, "hbond_donor": False, "hbond_acceptor": True},
    "GLY": {"volume": 60.1, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
    "HIS": {"volume": 153.2, "polar": True, "charge": 0, "aromatic": True, "hbond_donor": True, "hbond_acceptor": True},
    "ILE": {"volume": 166.7, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
    "LEU": {"volume": 166.7, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
    "LYS": {"volume": 168.6, "polar": True, "charge": 1, "aromatic": False, "hbond_donor": True, "hbond_acceptor": False},
    "MET": {"volume": 162.9, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
    "PHE": {"volume": 189.9, "polar": False, "charge": 0, "aromatic": True, "hbond_donor": False, "hbond_acceptor": False},
    "PRO": {"volume": 112.7, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
    "SER": {"volume": 89.0, "polar": True, "charge": 0, "aromatic": False, "hbond_donor": True, "hbond_acceptor": True},
    "THR": {"volume": 116.1, "polar": True, "charge": 0, "aromatic": False, "hbond_donor": True, "hbond_acceptor": True},
    "TRP": {"volume": 227.8, "polar": False, "charge": 0, "aromatic": True, "hbond_donor": True, "hbond_acceptor": False},
    "TYR": {"volume": 193.6, "polar": True, "charge": 0, "aromatic": True, "hbond_donor": True, "hbond_acceptor": True},
    "VAL": {"volume": 140.0, "polar": False, "charge": 0, "aromatic": False, "hbond_donor": False, "hbond_acceptor": False},
}


def _residue_properties(residue_name: str) -> dict:
    return _RESIDUE_PROPERTIES.get(residue_name.upper().strip(), {})
