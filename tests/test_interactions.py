from psf_reasoner.physical.interactions import analyze_typed_interactions, count_typed_interactions
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
