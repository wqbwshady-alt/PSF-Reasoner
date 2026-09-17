"""Content validation for structure uploads (beyond extension + size)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.uploads import (
    InvalidStructureError,
    validate_structure_file,
)

REPO_ROOT = Path(__file__).parent.parent


def _client(tmp_path: Path) -> TestClient:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    return TestClient(create_app(create_default_runner(), upload_dir=upload_dir))


def _post_file(client: TestClient, name: str, content: bytes, fields: dict | None = None):
    return client.post(
        "/v3/analyze-upload",
        files={"reference_file": (name, content, "chemical/x-pdb")},
        data={**(fields or {}), "ligand": "MK1", "mutation": "V82A", "chain": "A"},
    )


def test_valid_mmcif_upload_accepted(tmp_path: Path) -> None:
    client = _client(tmp_path)
    with open(REPO_ROOT / "examples/data/1sdt.cif", "rb") as f1, open(
        REPO_ROOT / "examples/data/1sdv.cif", "rb"
    ) as f2:
        resp = client.post(
            "/v3/analyze-upload",
            files={
                "reference_file": ("1sdt.cif", f1, "chemical/x-cif"),
                "mutant_file": ("1sdv.cif", f2, "chemical/x-cif"),
            },
            data={"ligand": "MK1", "mutation": "V82A", "chain": "A"},
        )
    assert resp.status_code == 200, resp.text


def test_fake_extension_text_rejected(tmp_path: Path) -> None:
    resp = _post_file(_client(tmp_path), "not_a_structure.pdb", b"hello world, definitely not a PDB")
    assert resp.status_code == 422
    detail = resp.json()["detail"].lower()
    assert "parse" in detail or "structure" in detail or "atom" in detail


def test_empty_file_rejected(tmp_path: Path) -> None:
    resp = _post_file(_client(tmp_path), "empty.pdb", b"")
    assert resp.status_code == 422


def test_zero_atom_structure_rejected(tmp_path: Path) -> None:
    content = b"HEADER    EMPTY STRUCTURE\nEND\n"
    resp = _post_file(_client(tmp_path), "zero.pdb", content)
    assert resp.status_code == 422
    assert "atom" in resp.json()["detail"].lower()


def test_malformed_structure_rejected(tmp_path: Path) -> None:
    resp = _post_file(_client(tmp_path), "malformed.cif", b"\x00\x01\x02garbage\xff\xfe")
    assert resp.status_code == 422


def test_rejected_upload_is_deleted(tmp_path: Path) -> None:
    client = _client(tmp_path)
    upload_dir = tmp_path / ".psf_uploads"
    before = set(upload_dir.iterdir())
    resp = _post_file(client, "bad.pdb", b"not a structure")
    assert resp.status_code == 422
    assert set(upload_dir.iterdir()) == before, "failed upload must not leave files behind"


def test_oversized_upload_rejected(tmp_path: Path) -> None:
    content = b"ATOM" + b" " * (25 * 1024 * 1024)
    resp = _post_file(_client(tmp_path), "big.pdb", content)
    assert resp.status_code == 413


def test_error_detail_hides_server_paths(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = _post_file(client, "bad.pdb", b"not a structure")
    detail = resp.json()["detail"]
    assert str(tmp_path) not in detail
    assert "/Users" not in detail and "/home" not in detail


class TestValidateStructureFile:
    def test_accepts_valid_pdb(self, tmp_path: Path) -> None:
        path = tmp_path / "ok.pdb"
        path.write_text(
            "ATOM      1  N   VAL A  82       0.000   0.000   0.000  1.00 20.00           N\nEND\n",
            encoding="ascii",
        )
        validate_structure_file(path)  # must not raise

    def test_rejects_unparseable(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.pdb"
        path.write_text("certainly not a structure", encoding="ascii")
        with pytest.raises(InvalidStructureError):
            validate_structure_file(path)

    def test_rejects_zero_atoms(self, tmp_path: Path) -> None:
        path = tmp_path / "zero.pdb"
        path.write_text("HEADER    EMPTY\nEND\n", encoding="ascii")
        with pytest.raises(InvalidStructureError, match="atom"):
            validate_structure_file(path)
