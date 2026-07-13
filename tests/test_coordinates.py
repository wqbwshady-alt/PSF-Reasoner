from pathlib import Path

import pytest

from psf_reasoner.physical.coordinates import CoordinateEvidenceProvider
from psf_reasoner.physical.structure import StructureAnalysisError, StructureParser
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType
from psf_reasoner.schemas.inputs import AnalysisRequest, LigandSpec, MutationSpec, StructureInput


def test_pdb_coordinates_produce_exact_distance_and_contact(structure_file: Path) -> None:
    request = AnalysisRequest(
        structure=StructureInput(path=str(structure_file)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )

    evidence = CoordinateEvidenceProvider().collect(request)

    assert len(evidence) == 2
    distance, contact = evidence
    assert distance.evidence_type is EvidenceType.ATOMIC_DISTANCE
    assert distance.status is EvidenceStatus.COMPUTED
    assert distance.measurement is not None
    assert distance.measurement.value == 2.5
    assert distance.entities == ("A:VAL82", "B:MK1902", "A:VAL82:CG1", "B:MK1902:C1")
    assert contact.evidence_type is EvidenceType.RESIDUE_CONTACT
    assert contact.status is EvidenceStatus.COMPUTED
    assert contact.supports == (distance.id,)


def test_1hsg_mmcif_localizes_both_v82_residues() -> None:
    request = AnalysisRequest(
        structure=StructureInput(path="examples/data/1hsg.cif"),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A"),
    )

    evidence = CoordinateEvidenceProvider().collect(request)

    distances = [item for item in evidence if item.evidence_type is EvidenceType.ATOMIC_DISTANCE]
    contacts = [item for item in evidence if item.evidence_type is EvidenceType.RESIDUE_CONTACT]
    assert len(distances) == 2
    assert len(contacts) == 2
    assert {item.entities[0] for item in distances} == {"A:VAL82", "B:VAL82"}
    assert {item.measurement.value for item in distances if item.measurement is not None} == {
        3.635,
        3.905,
    }


def test_parser_reports_wild_type_mismatch(structure_file: Path) -> None:
    parsed = StructureParser().parse(StructureInput(path=str(structure_file)))

    with pytest.raises(StructureAnalysisError, match="expects residue A"):
        parsed.locate_mutation_residues(MutationSpec(notation="A82V", chain="A"))


def test_parser_locates_the_unique_ligand_instance(structure_file: Path) -> None:
    parsed = StructureParser().parse(StructureInput(path=str(structure_file)))

    assert parsed.locate_ligand(LigandSpec(identifier="MK1")).identity.label == "B:MK1902"


def test_parser_requires_disambiguation_for_multiple_ligand_instances(
    structure_file: Path,
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "duplicate_ligands.pdb"
    duplicate.write_text(
        structure_file.read_text(encoding="ascii").replace(
            "END\n",
            "HETATM    6  C1  MK1 C 903       8.000   0.000   0.000  1.00 20.00           C\nEND\n",
        ),
        encoding="ascii",
    )
    parsed = StructureParser().parse(StructureInput(path=str(duplicate)))

    with pytest.raises(StructureAnalysisError, match="is ambiguous"):
        parsed.locate_ligand(LigandSpec(identifier="MK1"))
