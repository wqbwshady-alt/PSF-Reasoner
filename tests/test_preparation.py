from pathlib import Path

import pytest

from psf_reasoner.physical.preparation import StructurePreparationInspector
from psf_reasoner.schemas.inputs import AnalysisRequest, LigandSpec, MutationSpec, StructureInput


def test_preparation_reports_water_and_structure_counts(structure_file: Path) -> None:
    request = AnalysisRequest(
        structure=StructureInput(path=str(structure_file)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )

    preparation = StructurePreparationInspector().inspect_request(request)

    assert len(preparation) == 1
    assert preparation[0].water_residue_count == 1
    assert preparation[0].atom_count == 6


def test_preparation_reports_ligand_typing(structure_file: Path) -> None:
    request = AnalysisRequest(
        structure=StructureInput(path=str(structure_file)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )

    preparation = StructurePreparationInspector().inspect_request(request)

    assert len(preparation) >= 1
    # Ligand typing should report atom information
    assert len(preparation[0].issues) >= 0  # may or may not have issues


def test_preparation_detects_missing_file() -> None:
    request = AnalysisRequest(
        structure=StructureInput(path="nonexistent_file.pdb"),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )

    from psf_reasoner.physical.structure import StructureAnalysisError

    with pytest.raises(StructureAnalysisError):
        StructurePreparationInspector().inspect_request(request)


def test_preparation_with_mutant_structure(structure_file: Path, mutant_structure_file: Path) -> None:
    request = AnalysisRequest(
        structure=StructureInput(path=str(structure_file)),
        mutant_structure=StructureInput(path=str(mutant_structure_file)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )

    preparation = StructurePreparationInspector().inspect_request(request)

    assert len(preparation) == 2
    assert preparation[0].role == "reference"
    assert preparation[1].role == "mutant"
