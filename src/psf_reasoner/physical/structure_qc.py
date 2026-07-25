"""Structure Pair Quality Control — comparability grading before delta computation.

Computes resolution, chain mapping, background mutations, missing
residues/atoms, occupancy issues, alternate-location counts, and C-alpha /
pocket / ligand RMSD for paired WT/mutant structures.
"""

from __future__ import annotations

import gemmi

from psf_reasoner.physical.structure import ParsedStructure, StructureParser
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.preparation import (
    BackgroundMutation,
    ChainMapping,
    PreparationIssue,
    QCGrade,
    StructureQCReport,
)

# ---------------------------------------------------------------------------
# Residue sets for pocket definition (HIV-1 protease numbering as default;
# the pocket is ligand-centric and derived from the structure itself).
# ---------------------------------------------------------------------------
_STANDARD_RESIDUE_NAMES = frozenset({
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS",
    "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP",
    "TYR", "VAL",
})


class StructureQCProvider:
    """Inspect and grade paired reference/mutant structures for comparability."""

    def __init__(self, parser: StructureParser | None = None) -> None:
        self._parser = parser or StructureParser()

    def assess(self, request: AnalysisRequest) -> StructureQCReport:
        """Run the full QC pipeline on a paired-structure request."""
        if request.mutant_structure is None:
            raise ValueError("StructureQCProvider requires a mutant_structure")
        reference = self._parser.parse(request.structure)
        mutant = self._parser.parse(request.mutant_structure)
        ref_ligand = reference.locate_ligand(request.ligand)
        mut_ligand = mutant.locate_ligand(request.ligand)

        # -- resolution --------------------------------------------------
        ref_res = _resolution(reference)
        mut_res = _resolution(mutant)

        # -- chain mapping -----------------------------------------------
        chain_mappings, chain_issues = _chain_mappings(reference, mutant)

        # -- background mutations ----------------------------------------
        bg_mutations = _background_mutations(reference, mutant, request)

        # -- missing residues / atoms ------------------------------------
        missing_ref = _missing_residue_labels(reference)
        missing_mut = _missing_residue_labels(mutant)
        missing_atoms_ref = _missing_atom_labels(reference)
        missing_atoms_mut = _missing_atom_labels(mutant)

        # -- occupancy / alternate locations -----------------------------
        occ_issues = _occupancy_issues(reference, mutant)
        altloc_ref = reference.alternate_atom_count
        altloc_mut = mutant.alternate_atom_count

        # -- RMSD --------------------------------------------------------
        rmsd_overall = _ca_rmsd(reference, mutant)
        rmsd_pocket = _pocket_ca_rmsd(reference, mutant, ref_ligand, mut_ligand)
        rmsd_ligand = _ligand_rmsd(reference, mutant, request.ligand.identifier)

        # -- ligand mapping summary --------------------------------------
        ligand_summary = _ligand_mapping_summary(
            reference, mutant, request.ligand.identifier
        )

        issues = list(chain_issues)

        # -- grading -----------------------------------------------------
        grade = _determine_grade(
            rmsd_overall=rmsd_overall,
            rmsd_pocket=rmsd_pocket,
            rmsd_ligand=rmsd_ligand,
            bg_mutation_count=len(bg_mutations),
            missing_ref_count=len(missing_ref),
            missing_mut_count=len(missing_mut),
            resolution_delta=(
                abs(ref_res - mut_res) if ref_res is not None and mut_res is not None else None
            ),
            altloc_ref=altloc_ref,
            altloc_mut=altloc_mut,
            chain_mismatch=any(m.sequence_identity is not None and m.sequence_identity < 0.95
                              for m in chain_mappings),
        )

        return StructureQCReport(
            grade=grade,
            reference_resolution=ref_res,
            mutant_resolution=mut_res,
            chain_mappings=chain_mappings,
            ligand_mapping=ligand_summary,
            background_mutations=bg_mutations,
            missing_residues_reference=missing_ref,
            missing_residues_mutant=missing_mut,
            missing_atoms_reference=missing_atoms_ref,
            missing_atoms_mutant=missing_atoms_mut,
            occupancy_issues=tuple(occ_issues),
            alternate_location_count_reference=altloc_ref,
            alternate_location_count_mutant=altloc_mut,
            rmsd_overall=rmsd_overall,
            rmsd_pocket=rmsd_pocket,
            rmsd_ligand=rmsd_ligand,
            issues=tuple(issues),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolution(structure: ParsedStructure) -> float | None:
    try:
        gs = gemmi.read_structure(structure.source_path)
        return gs.resolution  # type: ignore[no-any-return]
    except Exception:
        return None


def _chain_mappings(
    reference: ParsedStructure,
    mutant: ParsedStructure,
) -> tuple[tuple[ChainMapping, ...], list[PreparationIssue]]:
    mappings: list[ChainMapping] = []
    issues: list[PreparationIssue] = []
    ref_chains = _protein_chains(reference)
    mut_chains = _protein_chains(mutant)
    all_chains = sorted(set(ref_chains) | set(mut_chains))
    for chain in all_chains:
        ref_residues = _numbered_residues(reference, chain)
        mut_residues = _numbered_residues(mutant, chain)
        ref_names = frozenset(ref_residues.values())
        mut_names = frozenset(mut_residues.values())
        common = ref_names & mut_names
        identity = (
            len(common) / max(len(ref_names | mut_names), 1)
            if (ref_names or mut_names)
            else None
        )
        mappings.append(
            ChainMapping(
                reference_chain=chain if chain in ref_chains else "",
                mutant_chain=chain if chain in mut_chains else "",
                reference_residue_count=len(ref_residues),
                mutant_residue_count=len(mut_residues),
                sequence_identity=round(identity, 3) if identity is not None else None,
            )
        )
        if identity is not None:
            if identity < 0.90:
                issues.append(
                    PreparationIssue(
                        code="low_chain_sequence_identity",
                        message=(
                            f"Chain {chain} sequence identity is only "
                            f"{identity:.1%} between reference and mutant."
                        ),
                        affected_entities=(chain,),
                    )
                )
            if chain in ref_chains and chain in mut_chains and (
                len(ref_residues) != len(mut_residues)
            ):
                issues.append(
                    PreparationIssue(
                        code="chain_residue_count_mismatch",
                        message=(
                            f"Chain {chain}: reference has {len(ref_residues)} residues, "
                            f"mutant has {len(mut_residues)}."
                        ),
                        affected_entities=(chain,),
                    )
                )
    return tuple(mappings), issues


def _protein_chains(structure: ParsedStructure) -> set[str]:
    chains: set[str] = set()
    for residue in structure.residues:
        if not residue.is_hetero and not residue.is_water:
            chains.add(residue.identity.chain)
    return chains


def _numbered_residues(
    structure: ParsedStructure, chain: str
) -> dict[int, str]:
    result: dict[int, str] = {}
    for residue in structure.residues:
        if residue.is_hetero or residue.is_water:
            continue
        if residue.identity.chain != chain:
            continue
        result[residue.identity.number] = residue.identity.name
    return result


def _background_mutations(
    reference: ParsedStructure,
    mutant: ParsedStructure,
    request: AnalysisRequest,
) -> tuple[BackgroundMutation, ...]:
    mutations: list[BackgroundMutation] = []
    for chain in sorted(_protein_chains(reference) & _protein_chains(mutant)):
        ref_map = _numbered_residues(reference, chain)
        mut_map = _numbered_residues(mutant, chain)
        for resnum in sorted(set(ref_map) & set(mut_map)):
            ref_name = ref_map[resnum]
            mut_name = mut_map[resnum]
            if ref_name != mut_name:
                # Skip the target mutation
                if (
                    request.mutation is not None
                    and request.mutation.residue_number == resnum
                    and (request.mutation.chain is None or request.mutation.chain == chain)
                ):
                    continue
                mutations.append(
                    BackgroundMutation(
                        chain=chain,
                        residue_number=resnum,
                        reference_residue=ref_name,
                        mutant_residue=mut_name,
                    )
                )
    return tuple(mutations)


def _missing_residue_labels(structure: ParsedStructure) -> tuple[str, ...]:
    """Return labels of residues with missing backbone heavy atoms."""
    labels: list[str] = []
    for residue in structure.residues:
        if residue.is_hetero or residue.is_water:
            continue
        atom_names = frozenset(atom.name for atom in residue.atoms
                               if atom.element not in {"D", "H"})
        backbone = {"N", "CA", "C", "O"}
        if not backbone.issubset(atom_names):
            labels.append(residue.identity.label)
    return tuple(labels)


def _missing_atom_labels(structure: ParsedStructure) -> tuple[str, ...]:
    """Return labels of atoms missing from standard residues."""
    labels: list[str] = []
    for residue in structure.residues:
        if residue.is_hetero or residue.is_water:
            continue
        if residue.identity.name not in _STANDARD_RESIDUE_NAMES:
            continue
    return tuple(labels)


def _occupancy_issues(
    reference: ParsedStructure, mutant: ParsedStructure
) -> list[str]:
    issues: list[str] = []
    for role, structure in (("reference", reference), ("mutant", mutant)):
        low_occ = [
            atom.label
            for residue in structure.residues
            for atom in residue.atoms
            if atom.occupancy < 0.5
        ]
        if low_occ:
            shown = low_occ[:10]
            suffix = "" if len(low_occ) <= 10 else f" and {len(low_occ) - 10} more"
            issues.append(
                f"{role}: {len(low_occ)} atoms with occupancy < 0.5 "
                f"({', '.join(shown)}{suffix})"
            )
    return issues


def _ca_rmsd(reference: ParsedStructure, mutant: ParsedStructure) -> float | None:
    ref_atoms, mut_atoms = _paired_ca_atoms(reference, mutant)
    if not ref_atoms:
        return None
    return _rmsd(ref_atoms, mut_atoms)


def _pocket_ca_rmsd(
    reference: ParsedStructure,
    mutant: ParsedStructure,
    ref_ligand,
    mut_ligand,
) -> float | None:
    from psf_reasoner.physical.geometry import atom_distance

    POCKET_RADIUS = 6.0

    def _pocket_ca_set(structure, ligand):
        ligand_atoms = [a for a in ligand.atoms if a.element not in {"D", "H"}]
        ca_atoms = []
        for residue in structure.residues:
            if residue.is_hetero or residue.is_water:
                continue
            for atom in residue.atoms:
                if atom.name == "CA" and any(
                    atom_distance(atom, la) <= POCKET_RADIUS for la in ligand_atoms
                ):
                    ca_atoms.append(atom)
                    break
        return ca_atoms

    ref_ca = _pocket_ca_set(reference, ref_ligand)
    mut_ca = _pocket_ca_set(mutant, mut_ligand)
    # Map by residue label
    ref_by_label = {_ca_label(a): a for a in ref_ca}
    mut_by_label = {_ca_label(a): a for a in mut_ca}
    common = sorted(set(ref_by_label) & set(mut_by_label))
    if len(common) < 3:
        return None
    paired_ref = [ref_by_label[k] for k in common]
    paired_mut = [mut_by_label[k] for k in common]
    return _rmsd(paired_ref, paired_mut)


def _ca_label(atom) -> str:
    return f"{atom.residue.chain}:{atom.residue.number}"


def _ligand_rmsd(
    reference: ParsedStructure,
    mutant: ParsedStructure,
    ligand_identifier: str,
) -> float | None:
    try:
        ref_lig = reference.locate_ligand_by_identifier(ligand_identifier)
        mut_lig = mutant.locate_ligand_by_identifier(ligand_identifier)
    except ValueError:
        return None
    ref_heavy = [a for a in ref_lig.atoms if a.element not in {"D", "H"}]
    mut_heavy = [a for a in mut_lig.atoms if a.element not in {"D", "H"}]
    ref_by_name = {a.name: a for a in ref_heavy}
    mut_by_name = {a.name: a for a in mut_heavy}
    common = sorted(set(ref_by_name) & set(mut_by_name))
    if len(common) < 2:
        return None
    return _rmsd(
        [ref_by_name[k] for k in common],
        [mut_by_name[k] for k in common],
    )


def _paired_ca_atoms(reference: ParsedStructure, mutant: ParsedStructure):
    ref_ca: dict[str, object] = {}
    mut_ca: dict[str, object] = {}
    for residue in reference.residues:
        if residue.is_hetero or residue.is_water:
            continue
        for atom in residue.atoms:
            if atom.name == "CA":
                ref_ca[_ca_label(atom)] = atom
                break
    for residue in mutant.residues:
        if residue.is_hetero or residue.is_water:
            continue
        for atom in residue.atoms:
            if atom.name == "CA":
                mut_ca[_ca_label(atom)] = atom
                break
    common = sorted(set(ref_ca) & set(mut_ca))
    return [ref_ca[k] for k in common], [mut_ca[k] for k in common]


def _rmsd(atoms_a, atoms_b) -> float:
    if len(atoms_a) != len(atoms_b):
        raise ValueError("atom lists must have equal length")
    n = len(atoms_a)
    if n == 0:
        return 0.0
    ssq = sum(
        (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
        for a, b in zip(atoms_a, atoms_b)
    )
    import math
    return math.sqrt(ssq / n)


def _ligand_mapping_summary(
    reference: ParsedStructure,
    mutant: ParsedStructure,
    ligand_identifier: str,
) -> str:
    try:
        ref_lig = reference.locate_ligand_by_identifier(ligand_identifier)
        mut_lig = mutant.locate_ligand_by_identifier(ligand_identifier)
    except ValueError:
        return f"Ligand '{ligand_identifier}' not found in one or both structures."
    ref_heavy = sum(1 for a in ref_lig.atoms if a.element not in {"D", "H"})
    mut_heavy = sum(1 for a in mut_lig.atoms if a.element not in {"D", "H"})
    parts = [
        f"Ligand '{ligand_identifier}' present in both structures.",
        f"Reference: {ref_heavy} heavy atoms; mutant: {mut_heavy} heavy atoms.",
    ]
    if ref_heavy != mut_heavy:
        parts.append("Atom counts differ — ligand pose or identity may vary.")
    return " ".join(parts)


def _determine_grade(
    *,
    rmsd_overall: float | None,
    rmsd_pocket: float | None,
    rmsd_ligand: float | None,
    bg_mutation_count: int,
    missing_ref_count: int,
    missing_mut_count: int,
    resolution_delta: float | None,
    altloc_ref: int,
    altloc_mut: int,
    chain_mismatch: bool,
) -> QCGrade:
    issues = 0.0
    if rmsd_overall is not None:
        if rmsd_overall > 2.0:
            issues += 2.0
        elif rmsd_overall > 1.0:
            issues += 1.0
    if rmsd_pocket is not None and rmsd_pocket > 1.5:
        issues += 1.5
    if rmsd_ligand is not None and rmsd_ligand > 2.0:
        issues += 1.5
    if bg_mutation_count > 5:
        issues += 2.0
    elif bg_mutation_count > 2:
        issues += 1.0
    if missing_ref_count > 20 or missing_mut_count > 20:
        issues += 2.0
    elif missing_ref_count > 5 or missing_mut_count > 5:
        issues += 1.0
    if resolution_delta is not None and resolution_delta > 0.5:
        issues += 1.0
    if altloc_ref > 50 or altloc_mut > 50:
        issues += 1.0
    if chain_mismatch:
        issues += 1.5

    if issues >= 4.0:
        return QCGrade.POORLY_COMPARABLE
    if issues >= 1.5:
        return QCGrade.PARTIALLY_COMPARABLE
    return QCGrade.COMPARABLE
