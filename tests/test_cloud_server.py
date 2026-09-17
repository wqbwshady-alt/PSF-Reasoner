"""Security tests for the cloud compute service (cloud/server.py).

cloud/server.py is a standalone module (not part of the psf_reasoner
package); tests load it via importlib so its env-var configuration can
be controlled per test by loading a fresh module instance.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

CLOUD_DIR = Path(__file__).parent.parent / "cloud"
SERVER_PATH = CLOUD_DIR / "server.py"

_VALID_PDB = (
    "ATOM      1  N   VAL A  82       0.000   0.000   0.000  1.00 20.00           N\n"
    "ATOM      2  CA  VAL A  82       1.000   0.000   0.000  1.00 20.00           C\n"
    "HETATM    4  C1  MK1 B 902       4.000   0.000   0.000  1.00 20.00           C\n"
    "END\n"
)


def _load_server() -> Any:
    spec = importlib.util.spec_from_file_location("cloud_server_under_test", SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PSF_CLOUD_SECRET", "test-secret-token")
    monkeypatch.setenv("PSF_RATE_LIMIT_BURST", "10")
    monkeypatch.setenv("PSF_RATE_LIMIT_RPS", "0.1")
    return _load_server()


@pytest.fixture
def client(server_module: Any) -> TestClient:
    return TestClient(server_module.app)


def _auth(**kwargs: Any) -> dict[str, str]:
    return {"X-API-Key": "test-secret-token", **kwargs}


def test_health_is_public_without_key(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_compute_requires_api_key(client: TestClient) -> None:
    resp = client.post("/compute/coulomb", json={"pdb_data": _VALID_PDB})
    assert resp.status_code == 401


def test_compute_rejects_wrong_api_key(client: TestClient) -> None:
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": _VALID_PDB},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401


def test_compute_accepts_valid_key_and_structure(client: TestClient) -> None:
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": _VALID_PDB},
        headers=_auth(),
    )
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert items and items[0]["evidence_type"] == "energy_component"


def test_compute_fail_closed_when_secret_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PSF_CLOUD_SECRET", raising=False)
    module = _load_server()
    client = TestClient(module.app)
    resp = client.post("/compute/coulomb", json={"pdb_data": _VALID_PDB})
    assert resp.status_code == 503
    resp_health = client.get("/health")
    assert resp_health.status_code == 200


def test_compute_rejects_invalid_structure(client: TestClient) -> None:
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": "this is not a structure"},
        headers=_auth(),
    )
    assert resp.status_code == 422


def test_oversized_body_is_rejected(client: TestClient) -> None:
    big = "A" * (50 * 1024 * 1024 + 1)
    resp = client.post(
        "/compute/coulomb",
        content=big,
        headers={"X-API-Key": "test-secret-token", "Content-Type": "application/json"},
    )
    assert resp.status_code == 413


def test_oversized_pdb_data_is_rejected(server_module: Any, client: TestClient) -> None:
    big = "A" * (server_module.MAX_PDB_DATA_CHARS + 1)
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": big},
        headers=_auth(),
    )
    assert resp.status_code == 422


def test_rate_limit_rejects_burst(client: TestClient) -> None:
    # Burst capacity is 10 (fixture env) with negligible refill: the 11th
    # request within the window must be throttled.
    statuses = []
    for _ in range(11):
        resp = client.post(
            "/compute/coulomb",
            json={"pdb_data": _VALID_PDB},
            headers=_auth(),
        )
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_fpocket_endpoint_reports_unavailable(client: TestClient) -> None:
    """fpocket binary absent in CI → 501, not a crash."""
    resp = client.post(
        "/compute/fpocket",
        json={"pdb_data": _VALID_PDB},
        headers=_auth(),
    )
    assert resp.status_code == 501


def test_cloud_request_model_has_no_structure_path(server_module: Any) -> None:
    """The arbitrary filesystem read vector must stay removed."""
    fields = server_module.CloudComputeRequest.model_fields
    assert "structure_path" not in fields
    assert "pdb_data" in fields


_SAMPLE_EVIDENCE = {
    "id": "evidence_test-aaaaaaaaaaaa",
    "title": "Test evidence",
    "description": "Produced by the mock transport.",
    "confidence": 0.9,
    "evidence_type": "pocket_geometry",
    "status": "computed",
}


def test_http_cloud_adapter_sends_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The local adapter must authenticate with PSF_CLOUD_SECRET automatically."""
    import httpx

    from psf_reasoner.infrastructure.cloud_compute import HttpCloudAdapter
    from psf_reasoner.schemas.inputs import StructureInput

    structure = tmp_path / "input.pdb"
    structure.write_text(_VALID_PDB, encoding="ascii")
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["x-api-key"] = request.headers.get("x-api-key", "")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json=[_SAMPLE_EVIDENCE])

    monkeypatch.setenv("PSF_CLOUD_SECRET", "adapter-secret")
    adapter = HttpCloudAdapter(
        base_url="http://cloud.test",
        timeout=5.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    try:
        items = adapter.fpocket(StructureInput(path=str(structure)))
    finally:
        adapter.close()

    assert captured["x-api-key"] == "adapter-secret"
    assert len(items) == 1
    assert items[0].evidence_type.value == "pocket_geometry"
    import json

    assert json.loads(captured["body"])["pdb_data"] == _VALID_PDB
