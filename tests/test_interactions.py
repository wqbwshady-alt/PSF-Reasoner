from psf_reasoner.physical.interactions import (
    _ligand_bond_graph,
    _type_ligand_atom,
    analyze_typed_interactions,
    count_typed_interactions,
)
from psf_reasoner.physical.structure import AtomRecord, ResidueIdentity, ResidueRecord


def test_typed_lysine_to_charged_ligand_oxygen_forms_hydrogen_bond_and_salt_bridge() -> None:
    lysine = _residue(
        ResidueIdentity(chain="A", name="LYS", number=82, insertion_code=None),
        ("NZ", "N", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("O1", "O", 3.0, 0.0, 0.0, -1),
        is_hetero=True,
    )

    counts = count_typed_interactions(lysine, ligand, ())

    assert counts.hydrogen_bonds == 1
    assert counts.salt_bridges == 1


def test_aromatic_ligand_ring_forms_pi_interaction_with_phenylalanine() -> None:
    phe = _residue(
        ResidueIdentity(chain="A", name="PHE", number=82, insertion_code=None),
        ("CG", "C", 0.0, 0.0, 0.0, 0),
        ("CD1", "C", 1.0, 0.0, 0.0, 0),
        ("CD2", "C", 0.0, 1.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("C1", "C", 0.0, 0.0, 4.5, 0),
        ("C2", "C", 1.0, 0.0, 4.5, 0),
        ("C3", "C", 0.0, 1.0, 4.5, 0),
        is_hetero=True,
    )

    analysis = analyze_typed_interactions(phe, ligand, ())

    assert analysis.counts.pi_interactions == 1
    assert any(item.interaction_type == "pi_interaction" for item in analysis.interactions)


def test_salt_bridge_between_lysine_and_negatively_charged_ligand() -> None:
    lysine = _residue(
        ResidueIdentity(chain="A", name="LYS", number=82, insertion_code=None),
        ("NZ", "N", 0.0, 0.0, 0.0, 1),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("O1", "O", 3.0, 0.0, 0.0, -1),
        is_hetero=True,
    )

    counts = count_typed_interactions(lysine, ligand, ())

    assert counts.salt_bridges == 1
    assert counts.hydrogen_bonds == 1  # NZ is both donor and positive


def test_hydrophobic_contact_between_carbon_atoms() -> None:
    valine = _residue(
        ResidueIdentity(chain="A", name="VAL", number=82, insertion_code=None),
        ("CG1", "C", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("C1", "C", 3.5, 0.0, 0.0, 0),
        is_hetero=True,
    )

    counts = count_typed_interactions(valine, ligand, ())

    assert counts.hydrophobic_contacts == 1


def test_ligand_hydroxyl_requires_explicit_hydrogen_to_be_a_donor() -> None:
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("C1", "C", 0.0, 0.0, 0.0, 0),
        ("OH", "O", 1.43, 0.0, 0.0, 0),
        ("H1", "H", 2.39, 0.0, 0.0, 0),
        ("C2", "C", 5.0, 0.0, 0.0, 0),
        ("OX", "O", 6.24, 0.0, 0.0, 0),
        is_hetero=True,
    )
    graph = _ligand_bond_graph(ligand.atoms)
    hydroxyl, carbonyl = ligand.atoms[1], ligand.atoms[4]
    assert _type_ligand_atom(hydroxyl, graph).donor
    without_h = _ligand_bond_graph(tuple(atom for atom in ligand.atoms if atom.element != "H"))
    assert not _type_ligand_atom(hydroxyl, without_h).donor
    assert not _type_ligand_atom(carbonyl, graph).donor


def test_water_bridge_mediated_interaction() -> None:
    lysine = _residue(
        ResidueIdentity(chain="A", name="LYS", number=82, insertion_code=None),
        ("NZ", "N", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("O1", "O", 0.0, 0.0, 6.0, 0),
        is_hetero=True,
    )
    water = _residue(
        ResidueIdentity(chain="A", name="HOH", number=201, insertion_code=None),
        ("O", "O", 0.0, 0.0, 3.0, 0),
        is_hetero=True,
    )

    counts = count_typed_interactions(lysine, ligand, (water,))

    assert counts.water_bridges == 1


def test_no_interactions_when_too_far_apart() -> None:
    lysine = _residue(
        ResidueIdentity(chain="A", name="LYS", number=82, insertion_code=None),
        ("NZ", "N", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("O1", "O", 10.0, 0.0, 0.0, -1),
        is_hetero=True,
    )

    counts = count_typed_interactions(lysine, ligand, ())

    assert counts.hydrogen_bonds == 0
    assert counts.salt_bridges == 0
    assert counts.hydrophobic_contacts == 0


def test_no_interactions_with_empty_waters() -> None:
    lysine = _residue(
        ResidueIdentity(chain="A", name="LYS", number=82, insertion_code=None),
        ("NZ", "N", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("O1", "O", 3.0, 0.0, 0.0, -1),
        is_hetero=True,
    )

    counts = count_typed_interactions(lysine, ligand, ())

    assert counts.water_bridges == 0
    assert counts.hydrogen_bonds > 0  # direct interaction still detected


def test_no_pi_interaction_without_aromatic_rings() -> None:
    alanine = _residue(
        ResidueIdentity(chain="A", name="ALA", number=82, insertion_code=None),
        ("CB", "C", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("C1", "C", 0.0, 0.0, 4.5, 0),
        is_hetero=True,
    )

    analysis = analyze_typed_interactions(alanine, ligand, ())

    assert analysis.counts.pi_interactions == 0


def test_negative_glutamate_to_positive_ligand_forms_salt_bridge() -> None:
    glutamate = _residue(
        ResidueIdentity(chain="A", name="GLU", number=82, insertion_code=None),
        ("OE1", "O", 0.0, 0.0, 0.0, 0),
    )
    ligand = _residue(
        ResidueIdentity(chain="B", name="LIG", number=901, insertion_code=None),
        ("N1", "N", 3.0, 0.0, 0.0, 1),
        is_hetero=True,
    )

    counts = count_typed_interactions(glutamate, ligand, ())

    assert counts.salt_bridges == 1


def _residue(
    identity: ResidueIdentity,
    *atoms: tuple[str, str, float, float, float, int],
    is_hetero: bool = False,
) -> ResidueRecord:
    return ResidueRecord(
        identity=identity,
        one_letter_code=None,
        is_hetero=is_hetero,
        atoms=tuple(
            AtomRecord(
                residue=identity,
                name=name,
                element=element,
                x=x,
                y=y,
                z=z,
                occupancy=1.0,
                altloc=None,
                formal_charge=charge,
            )
            for name, element, x, y, z, charge in atoms
        ),
    )
