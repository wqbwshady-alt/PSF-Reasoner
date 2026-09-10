"""API-level regression tests for the V3 integrated analysis + exports."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner

REPO_ROOT = Path(__file__).parent.parent


def _client(tmp_path: Path) -> TestClient:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    return TestClient(create_app(create_default_runner(), upload_dir=upload_dir))


def _v82a_payload() -> dict:
    return {
        "structure": {"path": str(REPO_ROOT / "examples/data/1sdt.cif"), "format": "mmcif"},
        "mutant_structure": {"path": str(REPO_ROOT / "examples/data/1sdv.cif"), "format": "mmcif"},
        "ligand": {"identifier": "MK1"},
        "mutation": {"notation": "V82A", "chain": "A"},
    }


def test_v3_analyze_includes_identity_from_structure(tmp_path: Path) -> None:
    response = _client(tmp_path).post("/v3/analyze", json=_v82a_payload())
    assert response.status_code == 200, response.text
    data = response.json()

    identity = data["protein_identity"]
    assert identity["family_hint"] == "HIV-1_PROTEASE", identity
    assert data["v3_literature"]["total_entries"] > 0
    # All attached literature must be HIV-1 protease evidence.
    for grade_entries in data["v3_literature"]["by_grade"].values():
        for entry in grade_entries:
            assert entry["evidence_id"].startswith("HIV_"), entry

    # Localization data must point at the real mutation site.
    loc = data["evidence_localization"]
    assert loc["mutation_residue_number"] == 82
    assert loc["mutation_chain"] == "A"
    assert loc["ligand"] == "MK1"
    assert loc["neighborhood_4a"], "expected a non-empty 4A neighborhood"


def test_v3_analyze_requires_mutation(tmp_path: Path) -> None:
    payload = _v82a_payload()
    del payload["mutation"]
    response = _client(tmp_path).post("/v3/analyze", json=payload)
    assert response.status_code == 422


def test_v3_export_json_csv_pymol_roundtrip(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post("/v3/analyze", json=_v82a_payload())
    assert response.status_code == 200, response.text
    report_id = response.json()["report_id"]

    # JSON export must be valid JSON and contain the same report id.
    r = client.get(f"/export/{report_id}", params={"format": "json"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    exported = json.loads(r.text)
    assert exported["report_id"] == report_id
    assert exported["v2_report"]["report_id"] == report_id

    # CSV export must parse and carry evidence rows.
    r = client.get(f"/export/{report_id}", params={"format": "csv"})
    assert r.status_code == 200
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert rows, "CSV export must not be empty"
    assert any(row["kind"] == "physical_evidence" for row in rows)

    # PyMOL export must be a usable script highlighting the mutation site.
    r = client.get(f"/export/{report_id}", params={"format": "pymol"})
    assert r.status_code == 200
    assert "load " in r.text
    assert "mutation_site" in r.text
    assert "resi 82" in r.text


def test_export_unknown_report_404(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/export/does-not-exist", params={"format": "json"})
    assert response.status_code == 404


def test_export_rejects_unknown_format(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post("/v3/analyze", json=_v82a_payload())
    report_id = response.json()["report_id"]
    r = client.get(f"/export/{report_id}", params={"format": "docx"})
    assert r.status_code == 400


def test_v3_upload_endpoint_multipart(tmp_path: Path) -> None:
    client = _client(tmp_path)
    with (
        open(REPO_ROOT / "examples/data/1sdt.cif", "rb") as f1,
        open(REPO_ROOT / "examples/data/1sdv.cif", "rb") as f2,
    ):
        response = client.post(
            "/v3/analyze-upload",
            files={
                "reference_file": ("1sdt.cif", f1, "chemical/x-cif"),
                "mutant_file": ("1sdv.cif", f2, "chemical/x-cif"),
            },
            data={"ligand": "MK1", "mutation": "V82A", "chain": "A"},
        )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["protein_identity"]["family_hint"] == "HIV-1_PROTEASE"
    # Uploads must be viewable through /structure.
    upload_id = data["v2_report"]["request"]["structure"]["upload_id"]
    r = client.get("/structure", params={"upload_id": upload_id})
    assert r.status_code == 200


def test_v3_status_reports_review_statuses(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/v3/status")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset"]["accepted"] > 0
    assert data["dataset"]["rejected"] > 0


def test_example_structure_serving(tmp_path: Path) -> None:
    # The bundled example structures must be servable for the 3D viewer.
    client = _client(tmp_path)
    r = client.get("/structure", params={"path": str(REPO_ROOT / "examples/data/1sdt.cif")})
    assert r.status_code == 200
    assert r.text.startswith("ATOM") or r.text.startswith("HETATM") or "ATOM" in r.text
