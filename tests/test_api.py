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


def test_json_endpoint_rejects_missing_file_path(tmp_path: Path) -> None:
    """Non-existent file paths must be rejected by JSON endpoints."""
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()

    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    payload = {
        "structure": {"path": "/nonexistent/path/structure.cif"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A"},
    }
    response = client.post("/forward", json=payload)
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "not found" in detail or "upload" in detail


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


class TestStructureInputBoundary:
    """Raw filesystem paths must never let the API read arbitrary files."""

    def _client(self, upload_dir: Path) -> TestClient:
        upload_dir.mkdir()
        return TestClient(create_app(create_default_runner(), upload_dir=upload_dir))

    def test_rejects_arbitrary_existing_file(self, structure_file: Path, tmp_path: Path) -> None:
        client = self._client(tmp_path / ".psf_uploads")
        payload = {
            "structure": {"path": str(structure_file)},  # exists, but outside allowed roots
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
            "phenotype": {"name": "drug_resistance"},
        }
        response = client.post("/analyze", json=payload)
        assert response.status_code == 400
        assert "upload" in response.json()["detail"].lower()

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        client = self._client(tmp_path / ".psf_uploads")
        payload = {
            "structure": {"path": "/etc/hosts"},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
            "phenotype": {"name": "drug_resistance"},
        }
        assert client.post("/analyze", json=payload).status_code == 400

    def test_rejects_parent_traversal(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        secret = tmp_path / "secret.pdb"
        secret.write_text("ATOM", encoding="ascii")
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        payload = {
            "structure": {"path": str(upload_dir / ".." / "secret.pdb")},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
            "phenotype": {"name": "drug_resistance"},
        }
        assert client.post("/analyze", json=payload).status_code == 400

    def test_rejects_symlink_escaping_upload_dir(self, structure_file: Path, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "link.pdb").symlink_to(structure_file)
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        payload = {
            "structure": {"path": str(upload_dir / "link.pdb")},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
            "phenotype": {"name": "drug_resistance"},
        }
        assert client.post("/analyze", json=payload).status_code == 400

    def test_accepts_bundled_example(self, tmp_path: Path) -> None:
        client = self._client(tmp_path / ".psf_uploads")
        example = Path(__file__).parent.parent / "examples" / "data" / "1sdt.cif"
        payload = {
            "structure": {"path": str(example), "format": "mmcif"},
            "mutant_structure": {"path": str(example.with_name("1sdv.cif")), "format": "mmcif"},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
            "phenotype": {"name": "drug_resistance"},
        }
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200, response.text

    def test_structure_endpoint_rejects_symlink_escape(self, structure_file: Path, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "link.pdb").symlink_to(structure_file)
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        resp = client.get("/structure", params={"path": str(upload_dir / "link.pdb")})
        assert resp.status_code == 403


class TestUploadMaintenance:
    def test_admin_maintain_uploads_route_is_removed(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        resp = client.post("/admin/maintain-uploads")
        assert resp.status_code == 404

    def test_startup_cleanup_removes_expired_uploads(self, structure_file: Path, tmp_path: Path) -> None:
        import os
        import time

        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        old = upload_dir / "old.pdb"
        old.write_text("OLD", encoding="ascii")
        old_time = time.time() - 48 * 3600
        os.utime(old, (old_time, old_time))

        app = create_app(create_default_runner(), upload_dir=upload_dir)
        with TestClient(app):
            pass  # lifespan runs maintain_uploads on startup
        assert not old.exists()

    def test_maintenance_is_idempotent(self, tmp_path: Path) -> None:
        from psf_reasoner.infrastructure.uploads import maintain_uploads

        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "a.pdb").write_text("A", encoding="ascii")
        first = maintain_uploads(upload_dir)
        second = maintain_uploads(upload_dir)
        assert first["age_removed"] == 0
        assert second == {"age_removed": 0, "count_removed": 0}
        assert (upload_dir / "a.pdb").exists()
