from pathlib import Path

from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner


def test_bidirectional_api_and_report_lookup(structure_file: Path) -> None:
    runner = create_default_runner()
    client = TestClient(create_app(runner))
    payload = {
        "structure": {"path": str(structure_file)},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A", "chain": "A"},
        "phenotype": {"name": "drug_resistance"},
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 200
    report = response.json()
    stored = client.get(f"/reports/{report['report_id']}")
    assert stored.status_code == 200
    assert stored.json()["report_id"] == report["report_id"]


def test_forward_endpoint_rejects_bidirectional_request(structure_file: Path) -> None:
    client = TestClient(create_app(create_default_runner()))
    payload = {
        "structure": {"path": str(structure_file)},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A"},
        "phenotype": {"name": "drug_resistance"},
    }

    response = client.post("/forward", json=payload)

    assert response.status_code == 422


def test_forward_endpoint_reports_missing_structure_clearly() -> None:
    client = TestClient(create_app(create_default_runner()))
    payload = {
        "structure": {"path": "missing_complex.pdb"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A"},
    }

    response = client.post("/forward", json=payload)

    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]


def test_forward_endpoint_accepts_paired_structures(
    structure_file: Path,
    mutant_structure_file: Path,
) -> None:
    client = TestClient(create_app(create_default_runner()))
    payload = {
        "structure": {"path": str(structure_file)},
        "mutant_structure": {"path": str(mutant_structure_file)},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A", "chain": "A"},
    }

    response = client.post("/forward", json=payload)

    assert response.status_code == 200
    assert any(item["evidence_type"] == "pocket_geometry" for item in response.json()["physical_evidence"])


def test_upload_endpoint_analyzes_local_reference_and_mutant_files(
    structure_file: Path,
    mutant_structure_file: Path,
) -> None:
    client = TestClient(create_app(create_default_runner()))
    with structure_file.open("rb") as reference_handle, mutant_structure_file.open("rb") as mutant_handle:
        response = client.post(
            "/analyze-upload",
            data={
                "ligand": "MK1",
                "mutation": "V82A",
                "chain": "A",
                "phenotype": "drug_resistance",
            },
            files={
                "reference_file": ("reference.pdb", reference_handle, "chemical/x-pdb"),
                "mutant_file": ("mutant.pdb", mutant_handle, "chemical/x-pdb"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["structure_preparation"][0]["role"] == "reference"
    assert any(item["evidence_type"] == "salt_bridge" for item in payload["physical_evidence"])


def test_workbench_is_served_at_root() -> None:
    client = TestClient(create_app(create_default_runner()))

    response = client.get("/")

    assert response.status_code == 200
    assert "PSF-Reasoner" in response.text
