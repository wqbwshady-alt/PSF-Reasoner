"""Persistence tests for V3 analysis payloads."""

from __future__ import annotations

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.v3_repository import (
    V3ReportNotFoundError,
    V3ReportRepository,
)

REPO_ROOT = Path(__file__).parent.parent


def _payload(report_id: str = "report-aaaaaaaaaaaa") -> dict:
    return {
        "report_id": report_id,
        "v2_report": {"report_id": report_id, "schema_version": "1.0.0"},
        "protein_identity": {"family_hint": "TEST"},
        "v3_context": {"mutation_site": {}},
        "v3_causal_graph": None,
        "v3_literature": {"total_entries": 0},
        "evidence_localization": {},
    }


class TestV3Repository:
    def test_survives_repository_recreation(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        V3ReportRepository(db).save(_payload())
        # A brand-new instance over the same file must see the report —
        # this is the restart-recovery property.
        restored = V3ReportRepository(db).get("report-aaaaaaaaaaaa")
        assert restored["report_id"] == "report-aaaaaaaaaaaa"

    def test_missing_report_raises(self, tmp_path: Path) -> None:
        with pytest.raises(V3ReportNotFoundError):
            V3ReportRepository(tmp_path / "reports.db").get("nope")

    def test_delete(self, tmp_path: Path) -> None:
        repo = V3ReportRepository(tmp_path / "reports.db")
        repo.save(_payload())
        assert repo.delete("report-aaaaaaaaaaaa") is True
        assert repo.delete("report-aaaaaaaaaaaa") is False
        assert repo.count() == 0

    def test_prune_old_removes_expired(self, tmp_path: Path) -> None:
        repo = V3ReportRepository(tmp_path / "reports.db")
        repo.save(_payload("report-old"))
        repo.save(_payload("report-fresh"))
        # Age the old row directly.
        cutoff = time.time() - 48 * 3600
        aged = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(cutoff))
        with sqlite3.connect(str(tmp_path / "reports.db")) as conn:
            conn.execute(
                "UPDATE v3_reports SET generated_at = ? WHERE report_id = ?",
                (aged, "report-old"),
            )
        assert repo.prune_old(max_age_seconds=3600) == 1
        with pytest.raises(V3ReportNotFoundError):
            repo.get("report-old")
        assert repo.get("report-fresh")["report_id"] == "report-fresh"

    def test_schema_version_recorded(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        V3ReportRepository(db).save(_payload())
        V3ReportRepository(db)  # re-open: migrations must be idempotent
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
        assert row and int(row[0]) >= 1

    def test_concurrent_save_and_get(self, tmp_path: Path) -> None:
        repo = V3ReportRepository(tmp_path / "reports.db")

        def write(i: int) -> str:
            rid = f"report-{i:012d}"
            repo.save(_payload(rid))
            return rid

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(write, range(16)))
        for rid in ids:
            assert repo.get(rid)["report_id"] == rid
        assert repo.count() == 16


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            create_default_runner(),
            upload_dir=tmp_path / ".psf_uploads",
            v3_store=V3ReportRepository(tmp_path / "reports.db"),
        )
    )


_V82A_PAYLOAD = {
    "structure": {"path": str(REPO_ROOT / "examples/data/1sdt.cif"), "format": "mmcif"},
    "mutant_structure": {"path": str(REPO_ROOT / "examples/data/1sdv.cif"), "format": "mmcif"},
    "ligand": {"identifier": "MK1"},
    "mutation": {"notation": "V82A", "chain": "A"},
}


class TestV3ApiPersistence:
    def test_export_survives_app_recreation(self, tmp_path: Path) -> None:
        first = _client(tmp_path)
        resp = first.post("/v3/analyze", json=_V82A_PAYLOAD)
        assert resp.status_code == 200, resp.text
        report_id = resp.json()["report_id"]

        # A completely new app instance (new runner, new store object,
        # same db file) must still export the report.
        second = _client(tmp_path)
        r = second.get(f"/export/{report_id}", params={"format": "json"})
        assert r.status_code == 200
        assert json.loads(r.text)["report_id"] == report_id

    def test_export_csv_and_pymol_after_recreation(self, tmp_path: Path) -> None:
        report_id = _client(tmp_path).post("/v3/analyze", json=_V82A_PAYLOAD).json()["report_id"]
        second = _client(tmp_path)
        r = second.get(f"/export/{report_id}", params={"format": "csv"})
        assert r.status_code == 200
        r = second.get(f"/export/{report_id}", params={"format": "pymol"})
        assert r.status_code == 200
        assert "mutation_site" in r.text

    def test_delete_report(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        report_id = client.post("/v3/analyze", json=_V82A_PAYLOAD).json()["report_id"]
        resp = client.delete(f"/v3/reports/{report_id}")
        assert resp.status_code == 200
        assert client.get(f"/export/{report_id}").status_code == 404

    def test_export_unknown_report_404(self, tmp_path: Path) -> None:
        assert _client(tmp_path).get("/export/does-not-exist").status_code == 404

    def test_no_process_level_cache(self) -> None:
        import psf_reasoner.api.app as app_module

        assert not hasattr(app_module, "_V3_RESULTS")
