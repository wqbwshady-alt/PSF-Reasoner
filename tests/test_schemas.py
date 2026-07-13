import pytest
from pydantic import ValidationError

from psf_reasoner.schemas.inputs import (
    AnalysisMode,
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    StructureInput,
)


def test_mutation_notation_is_parsed() -> None:
    mutation = MutationSpec(notation="V82A", chain="A")

    assert mutation.wild_type == "V"
    assert mutation.residue_number == 82
    assert mutation.mutant == "A"
    assert mutation.insertion_code is None


def test_request_requires_a_reasoning_anchor() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        AnalysisRequest(
            structure=StructureInput(path="complex.pdb"),
            ligand=LigandSpec(identifier="MK1"),
        )


def test_forward_mode_is_derived() -> None:
    request = AnalysisRequest(
        structure=StructureInput(path="complex.pdb"),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A"),
    )

    assert request.mode is AnalysisMode.FORWARD
