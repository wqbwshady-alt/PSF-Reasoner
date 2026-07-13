from pathlib import Path

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
