from pathlib import Path

import pytest

from psf_reasoner.schemas.inputs import (
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    PhenotypeSpec,
    StructureInput,
)


@pytest.fixture
def structure_file(tmp_path: Path) -> Path:
    path = tmp_path / "complex.pdb"
    path.write_text(
        """HEADER    TEST STRUCTURE
ATOM      1  N   VAL A  82       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  VAL A  82       1.000   0.000   0.000  1.00 20.00           C
ATOM      3  CG1 VAL A  82       1.500   0.000   0.000  1.00 20.00           C
HETATM    4  C1  MK1 B 902       4.000   0.000   0.000  1.00 20.00           C
HETATM    5  O1  MK1 B 902      -3.000   0.000   0.000  1.00 20.00           O
HETATM    6  O   HOH A 201      -1.500   0.000   0.000  1.00 20.00           O
END
""",
        encoding="ascii",
    )
    return path


@pytest.fixture
def mutant_structure_file(tmp_path: Path) -> Path:
    path = tmp_path / "complex_v82a.pdb"
    path.write_text(
        """HEADER    TEST MUTANT STRUCTURE
ATOM      1  N   ALA A  82       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A  82       1.000   0.000   0.000  1.00 20.00           C
ATOM      3  CB  ALA A  82       1.500   0.000   0.000  1.00 20.00           C
HETATM    4  C1  MK1 B 902       6.000   0.000   0.000  1.00 20.00           C
HETATM    5  O1  MK1 B 902      -7.000   0.000   0.000  1.00 20.00           O
HETATM    6  O   HOH A 201      -1.500   0.000   0.000  1.00 20.00           O
END
""",
        encoding="ascii",
    )
    return path


@pytest.fixture
def bidirectional_request(structure_file: Path) -> AnalysisRequest:
    return AnalysisRequest(
        structure=StructureInput(path=str(structure_file)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
        phenotype=PhenotypeSpec(name="drug_resistance"),
    )
