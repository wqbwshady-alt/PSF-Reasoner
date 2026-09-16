"""Atom-typed, conservative interaction classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees

from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import AtomRecord, ResidueRecord

HYDROGEN_BOND_CUTOFF_ANGSTROM = 3.5
HYDROPHOBIC_CUTOFF_ANGSTROM = 4.0
SALT_BRIDGE_CUTOFF_ANGSTROM = 5.5  # aligned with PLIP (was 4.0)
PI_CENTROID_CUTOFF_ANGSTROM = 5.5
HYDROGEN_BOND_MIN_ANGLE_DEGREES = 100.0  # aligned with PLIP (was 110.0)

AROMATIC_RESIDUE_ATOMS = {
    "PHE": frozenset({"CG", "CD1", "CD2", "CE1", "CE2", "CZ"}),
    "TYR": frozenset({"CG", "CD1", "CD2", "CE1", "CE2", "CZ"}),
    "TRP": frozenset({"CG", "CD1", "CD2", "NE1", "CE2", "CE3", "CZ2", "CZ3", "CH2"}),
    "HIS": frozenset({"CG", "ND1", "CD2", "CE1", "NE2"}),
}
DONOR_ATOMS = {
    "ARG": frozenset({"NE", "NH1", "NH2"}),
    "ASN": frozenset({"ND2"}),
    "CYS": frozenset({"SG"}),
    "GLN": frozenset({"NE2"}),
    "HIS": frozenset({"ND1", "NE2"}),
    "LYS": frozenset({"NZ"}),
    "SER": frozenset({"OG"}),
    "THR": frozenset({"OG1"}),
    "TRP": frozenset({"NE1"}),
    "TYR": frozenset({"OH"}),
}
# Polar carbon atoms — carbons bonded to O/N in side chains.
# These should NOT be counted as hydrophobic (aligns with PLIP's sp3-C-only rule).
POLAR_CARBON_ATOMS: dict[str, frozenset[str]] = {
    "ARG": frozenset({"CZ"}),
    "ASN": frozenset({"CG"}),
    "ASP": frozenset({"CG"}),
    "GLN": frozenset({"CD"}),
    "GLU": frozenset({"CD"}),
}

ACCEPTOR_ATOMS = {
    "ASN": frozenset({"OD1"}),
    "ASP": frozenset({"OD1", "OD2"}),
    "CYS": frozenset({"SG"}),
    "GLN": frozenset({"OE1"}),
    "GLU": frozenset({"OE1", "OE2"}),
    "HIS": frozenset({"ND1", "NE2"}),
    "MET": frozenset({"SD"}),
    "SER": frozenset({"OG"}),
    "THR": frozenset({"OG1"}),
    "TYR": frozenset({"OH"}),
}
POSITIVE_ATOMS = {
    "ARG": frozenset({"NE", "NH1", "NH2"}),
    "HIS": frozenset({"ND1", "NE2"}),
    "LYS": frozenset({"NZ"}),
}
NEGATIVE_ATOMS = {
    "ASP": frozenset({"OD1", "OD2"}),
    "GLU": frozenset({"OE1", "OE2"}),
}


@dataclass(frozen=True, slots=True)
class AtomTyping:
    donor: bool = False
    acceptor: bool = False
    positive: bool = False
    negative: bool = False
    aromatic: bool = False
    hydrophobic: bool = False
    confidence: float = 1.0
    reason: str = ""


@dataclass(frozen=True, slots=True)
class InteractionCounts:
    hydrogen_bonds: int
    hydrophobic_contacts: int
    salt_bridges: int
    pi_interactions: int
    water_bridges: int


@dataclass(frozen=True, slots=True)
class Interaction:
    interaction_type: str
    protein_atom: str
    ligand_atom: str
    distance_angstrom: float
    geometry: str
    confidence: float
    mediator: str | None = None


@dataclass(frozen=True, slots=True)
class InteractionAnalysis:
    interactions: tuple[Interaction, ...]

    @property
    def counts(self) -> InteractionCounts:
        return InteractionCounts(
            hydrogen_bonds=sum(item.interaction_type == "hydrogen_bond" for item in self.interactions),
            hydrophobic_contacts=sum(
                item.interaction_type == "hydrophobic_contact" for item in self.interactions
            ),
            salt_bridges=sum(item.interaction_type == "salt_bridge" for item in self.interactions),
            pi_interactions=sum(item.interaction_type == "pi_interaction" for item in self.interactions),
            water_bridges=sum(item.interaction_type == "water_bridge" for item in self.interactions),
        )


def count_typed_interactions(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    waters: tuple[ResidueRecord, ...],
) -> InteractionCounts:
    return analyze_typed_interactions(residue, ligand, waters).counts


def analyze_typed_interactions(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    waters: tuple[ResidueRecord, ...],
) -> InteractionAnalysis:
    protein_atoms = _heavy_atoms(residue)
    ligand_atoms = _heavy_atoms(ligand)
    ligand_graph = _ligand_bond_graph(ligand.atoms)
    interactions: list[Interaction] = []
    for protein_atom in protein_atoms:
        protein_type = _type_protein_atom(protein_atom)
        for ligand_atom in ligand_atoms:
            ligand_type = _type_ligand_atom(ligand_atom, ligand_graph)
            distance = atom_distance(protein_atom, ligand_atom)
            if (
                distance <= HYDROGEN_BOND_CUTOFF_ANGSTROM
                and _forms_hydrogen_bond(protein_type, ligand_type)
                and _passes_hydrogen_bond_geometry(
                    protein_atom, ligand_atom, residue, ligand, protein_type, ligand_type
                )
            ):
                interactions.append(
                    Interaction(
                        interaction_type="hydrogen_bond",
                        protein_atom=protein_atom.label,
                        ligand_atom=ligand_atom.label,
                        distance_angstrom=round(distance, 3),
                        geometry="donor-acceptor pair with distance/angle geometry check",
                        confidence=round(min(protein_type.confidence, ligand_type.confidence, 0.82), 3),
                    )
                )
            if (
                distance <= HYDROPHOBIC_CUTOFF_ANGSTROM
                and protein_type.hydrophobic
                and ligand_type.hydrophobic
            ):
                interactions.append(
                    Interaction(
                        interaction_type="hydrophobic_contact",
                        protein_atom=protein_atom.label,
                        ligand_atom=ligand_atom.label,
                        distance_angstrom=round(distance, 3),
                        geometry="heavy-atom hydrophobic contact cutoff",
                        confidence=round(min(protein_type.confidence, ligand_type.confidence, 0.75), 3),
                    )
                )
            if distance <= SALT_BRIDGE_CUTOFF_ANGSTROM and _forms_salt_bridge(protein_type, ligand_type):
                interactions.append(
                    Interaction(
                        interaction_type="salt_bridge",
                        protein_atom=protein_atom.label,
                        ligand_atom=ligand_atom.label,
                        distance_angstrom=round(distance, 3),
                        geometry="oppositely charged atom-pair cutoff",
                        confidence=round(min(protein_type.confidence, ligand_type.confidence, 0.85), 3),
                    )
                )
    pi_interaction = _pi_interaction(residue, ligand, protein_atoms, ligand_atoms, ligand_graph)
    if pi_interaction is not None:
        interactions.append(pi_interaction)
    interactions.extend(_water_bridge_events(waters, protein_atoms, ligand_atoms, ligand_graph))
    return InteractionAnalysis(tuple(interactions))


def _type_protein_atom(atom: AtomRecord) -> AtomTyping:
    residue_name = atom.residue.name
    atom_name = atom.name
    if atom_name == "O" or atom_name == "OXT":
        return AtomTyping(acceptor=True, reason="protein backbone oxygen")
    if atom_name == "N":
        return AtomTyping(
            donor=residue_name != "PRO",
            reason="protein backbone amide nitrogen",
        )
    is_polar_carbon = atom_name in POLAR_CARBON_ATOMS.get(residue_name, frozenset())
    return AtomTyping(
        donor=atom_name in DONOR_ATOMS.get(residue_name, frozenset()),
        acceptor=atom_name in ACCEPTOR_ATOMS.get(residue_name, frozenset()),
        positive=atom_name in POSITIVE_ATOMS.get(residue_name, frozenset()),
        negative=atom_name in NEGATIVE_ATOMS.get(residue_name, frozenset()),
        aromatic=atom_name in AROMATIC_RESIDUE_ATOMS.get(residue_name, frozenset()),
        hydrophobic=(
            (atom.element == "C" and atom_name not in {"C", "CA"} and not is_polar_carbon)
            or atom.element == "S"
        ),
        reason="residue-template atom typing",
    )


def _type_ligand_atom(
    atom: AtomRecord,
    bond_graph: dict[str, tuple[AtomRecord, ...]] | None = None,
) -> AtomTyping:
    neighbors = bond_graph.get(atom.label, ()) if bond_graph is not None else ()
    heavy_neighbors = tuple(neighbor for neighbor in neighbors if neighbor.element not in {"D", "H"})
    is_oxygen = atom.element == "O"
    is_sulfur = atom.element == "S"
    is_carbon = atom.element == "C"
    is_nitrogen = atom.element == "N"
    bonded_hydrogen = any(neighbor.element in {"D", "H"} for neighbor in neighbors)
    aromatic = is_carbon and _looks_like_ligand_aromatic_atom(atom, neighbors)
    confidence = (
        0.95
        if atom.formal_charge
        else 0.78
        if neighbors
        else 0.70
        if is_oxygen
        else 0.50
        if is_sulfur
        else 0.45
        if aromatic
        else 0.30
    )
    # Crystal structures frequently lack explicit H.  For nitrogen with
    # 1–2 heavy-atom neighbours (sp/sp²), assume donor capability — the
    # missing H is likely present but unresolved.  Nitrogen with ≥3
    # heavy neighbours is fully substituted and cannot donate.
    # Oxygen/sulfur are conservative: only donors with explicit H or
    # formal charge (carbonyl/ether are almost never donors).
    n_donor = is_nitrogen and (
        bonded_hydrogen or atom.formal_charge > 0 or (bool(heavy_neighbors) and len(heavy_neighbors) < 3)
    )
    os_donor = (is_oxygen or is_sulfur) and (bonded_hydrogen or atom.formal_charge > 0)
    likely_donor = n_donor or os_donor
    # Carbons bonded to O/N are polar, not hydrophobic (aligned with PLIP)
    ligand_hydrophobic = (
        is_carbon and not any(neighbor.element in {"O", "N"} for neighbor in neighbors)
    ) or atom.element in {"CL", "BR", "I", "F"}
    # Nitrogen with <3 heavy neighbours is protonatable → potential positive
    # (aligned with PLIP's OpenBabel-based charge assignment at phys. pH)
    n_protonatable = is_nitrogen and bool(heavy_neighbors) and len(heavy_neighbors) < 3
    return AtomTyping(
        donor=likely_donor,
        acceptor=is_oxygen or is_sulfur,
        positive=(atom.formal_charge > 0) or n_protonatable,
        negative=atom.formal_charge < 0,
        aromatic=aromatic,
        hydrophobic=ligand_hydrophobic,
        confidence=confidence,
        reason=(
            "explicit formal charge with element typing"
            if atom.formal_charge
            else "distance-perceived ligand bond environment"
            if neighbors
            else "element-only ligand oxygen typing"
            if is_oxygen
            else "element-only ligand sulfur typing"
            if is_sulfur
            else "element-only ligand carbon typing"
            if is_carbon
            else "ligand nitrogen protonation and bond order unknown"
            if atom.element == "N"
            else "no ligand atom-typing rule"
        ),
    )


def describe_ligand_atom_types(ligand: ResidueRecord) -> tuple[str, ...]:
    ligand_atoms = _heavy_atoms(ligand)
    graph = _ligand_bond_graph(ligand.atoms)
    return tuple(
        (
            f"{atom.label}: donor={typing.donor}, acceptor={typing.acceptor}, "
            f"positive={typing.positive}, negative={typing.negative}, aromatic={typing.aromatic}, "
            f"hydrophobic={typing.hydrophobic}, confidence={typing.confidence:.2f}"
        )
        for atom in ligand_atoms
        for typing in (_type_ligand_atom(atom, graph),)
    )


def _forms_hydrogen_bond(first: AtomTyping, second: AtomTyping) -> bool:
    return (first.donor and second.acceptor) or (second.donor and first.acceptor)


def _forms_salt_bridge(first: AtomTyping, second: AtomTyping) -> bool:
    return (first.positive and second.negative) or (first.negative and second.positive)


def _pi_interaction(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    protein_atoms: tuple[AtomRecord, ...],
    ligand_atoms: tuple[AtomRecord, ...],
    ligand_graph: dict[str, tuple[AtomRecord, ...]],
) -> Interaction | None:
    del residue, ligand
    protein_ring = tuple(atom for atom in protein_atoms if _type_protein_atom(atom).aromatic)
    ligand_ring = tuple(atom for atom in ligand_atoms if _type_ligand_atom(atom, ligand_graph).aromatic)
    if not protein_ring or not ligand_ring:
        return None
    distance = _centroid_distance(protein_ring, ligand_ring)
    if distance > PI_CENTROID_CUTOFF_ANGSTROM:
        return None
    return Interaction(
        interaction_type="pi_interaction",
        protein_atom=",".join(atom.label for atom in protein_ring),
        ligand_atom=",".join(atom.label for atom in ligand_ring),
        distance_angstrom=round(distance, 3),
        geometry="aromatic ring centroid cutoff",
        confidence=0.55,
    )


def _water_bridge_events(
    waters: tuple[ResidueRecord, ...],
    protein_atoms: tuple[AtomRecord, ...],
    ligand_atoms: tuple[AtomRecord, ...],
    ligand_graph: dict[str, tuple[AtomRecord, ...]],
) -> tuple[Interaction, ...]:
    interactions: list[Interaction] = []
    for water in waters:
        for water_atom in (atom for atom in water.atoms if atom.element == "O"):
            protein_partner = next(
                (
                    protein_atom
                    for protein_atom in protein_atoms
                    if atom_distance(water_atom, protein_atom) <= HYDROGEN_BOND_CUTOFF_ANGSTROM
                    and (_type_protein_atom(protein_atom).donor or _type_protein_atom(protein_atom).acceptor)
                ),
                None,
            )
            ligand_partner = next(
                (
                    ligand_atom
                    for ligand_atom in ligand_atoms
                    if atom_distance(water_atom, ligand_atom) <= HYDROGEN_BOND_CUTOFF_ANGSTROM
                    and (
                        _type_ligand_atom(ligand_atom, ligand_graph).donor
                        or _type_ligand_atom(ligand_atom, ligand_graph).acceptor
                    )
                ),
                None,
            )
            if protein_partner is not None and ligand_partner is not None:
                interactions.append(
                    Interaction(
                        interaction_type="water_bridge",
                        protein_atom=protein_partner.label,
                        ligand_atom=ligand_partner.label,
                        distance_angstrom=round(
                            atom_distance(water_atom, protein_partner)
                            + atom_distance(water_atom, ligand_partner),
                            3,
                        ),
                        geometry="resolved water within donor/acceptor cutoffs to protein and ligand",
                        confidence=0.60,
                        mediator=water_atom.label,
                    )
                )
    return tuple(interactions)


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


def _ligand_bond_graph(atoms: tuple[AtomRecord, ...]) -> dict[str, tuple[AtomRecord, ...]]:
    graph: dict[str, list[AtomRecord]] = {atom.label: [] for atom in atoms}
    for index, atom in enumerate(atoms):
        for other in atoms[index + 1 :]:
            if _likely_bonded(atom, other):
                graph[atom.label].append(other)
                graph[other.label].append(atom)
    return {label: tuple(neighbors) for label, neighbors in graph.items()}


def _likely_bonded(first: AtomRecord, second: AtomRecord) -> bool:
    cutoff = 1.25 if first.element in {"D", "H"} or second.element in {"D", "H"} else 1.90
    return atom_distance(first, second) <= cutoff


def _looks_like_ligand_aromatic_atom(atom: AtomRecord, neighbors: tuple[AtomRecord, ...]) -> bool:
    if atom.element != "C":
        return False
    carbon_like_neighbors = sum(neighbor.element in {"C", "N"} for neighbor in neighbors)
    aromatic_name_hint = atom.name.upper().startswith(("C", "CA", "CB", "CG", "CD", "CE", "CZ"))
    return carbon_like_neighbors >= 2 or (aromatic_name_hint and len(neighbors) >= 2)


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


# ---------------------------------------------------------------------------
# Cutoff Sensitivity Analysis (V2 Phase 2A)
# ---------------------------------------------------------------------------


def _classify_stability(counts: tuple[int, ...]) -> str:
    """Classify a cutoff-count series as robust / threshold-sensitive / unstable."""
    if len(counts) < 2:
        return "robust"
    max_val = max(counts)
    min_val = min(counts)
    if max_val == 0 and min_val == 0:
        return "robust"
    spread = (max_val - min_val) / max(1, max_val)
    # Count how many transitions (sign changes) there are
    transitions = sum(1 for i in range(len(counts) - 1) if counts[i] != counts[i + 1])
    if transitions == 0:
        return "robust"
    if spread < 0.25:
        return "robust"
    if transitions <= 2 and spread < 0.5:
        return "threshold_sensitive"
    return "unstable"


def cutoff_sensitivity_analysis(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    waters: tuple[ResidueRecord, ...],
    *,
    hbond_cutoffs: tuple[float, ...] = (3.0, 3.5, 4.0, 4.5, 5.0),
    hydrophobic_cutoffs: tuple[float, ...] = (3.5, 4.0, 4.5, 5.0),
    salt_bridge_cutoffs: tuple[float, ...] = (4.0, 4.5, 5.0, 5.5, 6.0),
    pi_cutoffs: tuple[float, ...] = (4.5, 5.0, 5.5, 6.0),
) -> dict[str, tuple[tuple[float, ...], tuple[int, ...]]]:
    """Sweep cutoff parameters and return per-class (cutoff_values, counts) pairs.

    Returns a dict keyed by interaction class name, each value a pair of
    ``(cutoff_values, count_per_cutoff)`` suitable for constructing
    ``CutoffSensitivityReport``.
    """
    global HYDROGEN_BOND_CUTOFF_ANGSTROM, HYDROPHOBIC_CUTOFF_ANGSTROM
    global SALT_BRIDGE_CUTOFF_ANGSTROM, PI_CENTROID_CUTOFF_ANGSTROM

    original_hbond = HYDROGEN_BOND_CUTOFF_ANGSTROM
    original_hydrophobic = HYDROPHOBIC_CUTOFF_ANGSTROM
    original_salt = SALT_BRIDGE_CUTOFF_ANGSTROM
    original_pi = PI_CENTROID_CUTOFF_ANGSTROM

    hbond_counts: list[int] = []
    hydrophobic_counts: list[int] = []
    salt_counts: list[int] = []
    pi_counts: list[int] = []

    try:
        for cutoff in hbond_cutoffs:
            HYDROGEN_BOND_CUTOFF_ANGSTROM = cutoff
            # Re-run analysis for this residue-ligand pair
            result = analyze_typed_interactions(residue, ligand, waters)
            hbond_counts.append(sum(item.interaction_type == "hydrogen_bond" for item in result.interactions))

        for cutoff in hydrophobic_cutoffs:
            HYDROPHOBIC_CUTOFF_ANGSTROM = cutoff
            result = analyze_typed_interactions(residue, ligand, waters)
            hydrophobic_counts.append(
                sum(item.interaction_type == "hydrophobic_contact" for item in result.interactions)
            )

        for cutoff in salt_bridge_cutoffs:
            SALT_BRIDGE_CUTOFF_ANGSTROM = cutoff
            result = analyze_typed_interactions(residue, ligand, waters)
            salt_counts.append(sum(item.interaction_type == "salt_bridge" for item in result.interactions))

        for cutoff in pi_cutoffs:
            PI_CENTROID_CUTOFF_ANGSTROM = cutoff
            result = analyze_typed_interactions(residue, ligand, waters)
            pi_counts.append(sum(item.interaction_type == "pi_interaction" for item in result.interactions))
    finally:
        HYDROGEN_BOND_CUTOFF_ANGSTROM = original_hbond
        HYDROPHOBIC_CUTOFF_ANGSTROM = original_hydrophobic
        SALT_BRIDGE_CUTOFF_ANGSTROM = original_salt
        PI_CENTROID_CUTOFF_ANGSTROM = original_pi

    return {
        "hydrogen_bond": (hbond_cutoffs, tuple(hbond_counts)),
        "hydrophobic_contact": (hydrophobic_cutoffs, tuple(hydrophobic_counts)),
        "salt_bridge": (salt_bridge_cutoffs, tuple(salt_counts)),
        "pi_interaction": (pi_cutoffs, tuple(pi_counts)),
    }
