import json
from pathlib import Path

from typer.testing import CliRunner

from psf_reasoner.cli import app


def test_forward_command_emits_json(structure_file: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "forward",
            "--structure",
            str(structure_file),
            "--ligand",
            "MK1",
            "--mutation",
            "V82A",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "forward"
    assert payload["functional_hypotheses"]


def test_forward_command_accepts_a_mutant_structure(
    structure_file: Path,
    mutant_structure_file: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "forward",
            "--structure",
            str(structure_file),
            "--mutant-structure",
            str(mutant_structure_file),
            "--ligand",
            "MK1",
            "--mutation",
            "V82A",
            "--chain",
            "A",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert any(item["evidence_type"] == "solvent_exposure" for item in payload["physical_evidence"])
