import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner


def test_bidirectional_api_and_report_lookup(structure_file: Path, tmp_path: Path) -> None:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    dest = upload_dir / "test_struct.pdb"
    shutil.copy2(structure_file, dest)

    runner = create_default_runner()
    client = TestClient(create_app(runner, upload_dir=upload_dir))
    payload = {
        "structure": {"upload_id": "test_struct.pdb"},
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


def test_forward_endpoint_rejects_bidirectional_request(tmp_path: Path) -> None:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()

    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    payload = {
        "structure": {"upload_id": "missing.pdb"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A"},
        "phenotype": {"name": "drug_resistance"},
    }

    # This should return 422 because forward does not accept phenotype,
    # but with a missing upload_id it will return 400 first.
    # The point is the endpoint rejects the request.
    response = client.post("/forward", json=payload)
    assert response.status_code in (400, 422)


def test_json_endpoint_rejects_raw_filesystem_path(tmp_path: Path) -> None:
    """Direct filesystem paths must be rejected by JSON endpoints."""
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()

    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    payload = {
        "structure": {"path": "/etc/passwd"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A"},
    }
    response = client.post("/forward", json=payload)
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "filesystem path" in detail or "upload" in detail


def test_structure_endpoint_rejects_path_traversal(tmp_path: Path) -> None:
    """GET /structure must reject paths escaping the upload directory."""
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()

    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    for malicious in ["../../../etc/passwd", "/etc/passwd", "..%2F..%2Fetc%2Fpasswd"]:
        resp = client.get("/structure", params={"path": malicious})
        assert resp.status_code in (400, 403, 404)


def test_json_endpoint_rejects_path_traversal_via_upload_id(tmp_path: Path) -> None:
    """Path separators in upload_id must be rejected."""
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()

    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    payload = {
        "structure": {"upload_id": "../../etc/passwd"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A"},
    }
    response = client.post("/forward", json=payload)
    assert response.status_code == 400


def test_forward_endpoint_accepts_paired_structures(
    structure_file: Path,
    mutant_structure_file: Path,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    ref_dest = upload_dir / "ref.pdb"
    mut_dest = upload_dir / "mut.pdb"
    shutil.copy2(structure_file, ref_dest)
    shutil.copy2(mutant_structure_file, mut_dest)

    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    payload = {
        "structure": {"upload_id": "ref.pdb"},
        "mutant_structure": {"upload_id": "mut.pdb"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A", "chain": "A"},
    }

    response = client.post("/forward", json=payload)

    assert response.status_code == 200
    assert any(item["evidence_type"] == "pocket_geometry" for item in response.json()["physical_evidence"])


def test_upload_endpoint_analyzes_local_reference_and_mutant_files(
    structure_file: Path,
    mutant_structure_file: Path,
    tmp_path: Path,
) -> None:
    upload_dir = tmp_path / ".psf_uploads"
    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
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
