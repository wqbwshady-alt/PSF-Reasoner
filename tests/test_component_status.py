"""Optional-component status, degradation logging, and report runtime info."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.component_status import (
    ComponentStatus,
    component_registry,
)
from psf_reasoner.schemas.inputs import (
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    StructureInput,
)


def _simple_request(structure_path: Path) -> AnalysisRequest:
    return AnalysisRequest(
        structure=StructureInput(path=str(structure_path)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )


def test_registry_set_get_snapshot() -> None:
    component_registry.set(ComponentStatus("x", True, False, "impl-a", "detail"))
    assert component_registry.get("x").implementation == "impl-a"  # type: ignore[union-attr]
    snap = component_registry.snapshot()
    assert snap["x"]["implementation"] == "impl-a"


def test_invalid_llm_provider_logs_and_falls_back(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    from psf_reasoner import bootstrap

    monkeypatch.setenv("PSF_LLM", "1")
    monkeypatch.setenv("PSF_LLM_PROVIDER", "no-such-provider")
    with caplog.at_level(logging.WARNING, logger="psf_reasoner.bootstrap"):
        provider = bootstrap._auto_llm_provider()
    assert provider is None
    assert "no-such-provider" in caplog.text
    assert "DEEPSEEK_API_KEY" not in caplog.text
    status = component_registry.get("llm")
    assert status is not None and status.available is False


def test_default_runner_is_baseline_and_status_reflected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PSF_LLM", raising=False)
    monkeypatch.delenv("PSF_CLOUD_URL", raising=False)
    create_default_runner()
    status = component_registry.get("reasoning_engine")
    assert status is not None and status.implementation == "baseline"
    modeler = component_registry.get("mutation_modeler")
    assert modeler is not None and modeler.implementation == "local_side_chain"


def test_report_records_runtime_components(
    structure_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PSF_LLM", raising=False)
    monkeypatch.delenv("PSF_CLOUD_URL", raising=False)
    runner = create_default_runner()
    report = runner.run(_simple_request(structure_file))
    runtime = report.runtime
    assert runtime is not None
    assert runtime.reasoning_engine == "baseline"
    assert runtime.mutation_modeler == "local_side_chain"
    assert runtime.llm_provider is None
    assert "gemmi" in runtime.external_tools


def test_health_reports_component_status(tmp_path: Path) -> None:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "components" in data
    assert "reasoning_engine" in data["components"]


def test_cloud_provider_failure_is_logged_not_suppressed(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    from psf_reasoner.physical.cloud_provider import CloudEvidenceProvider

    class BrokenAdapter:
        def fpocket(self, structure):
            raise RuntimeError("boom: http://cloud.internal")

        def coulomb(self, structure):
            raise RuntimeError("also broken")

    provider = CloudEvidenceProvider(adapter=BrokenAdapter())
    with caplog.at_level(logging.WARNING, logger="psf_reasoner.physical.cloud_provider"):
        items = provider.collect(_simple_request(Path("/nonexistent.pdb")))
    assert items == ()
    assert "fpocket" in caplog.text or "cloud" in caplog.text.lower()
    # The failure reason must be logged, but never structure contents.
    assert "ATOM" not in caplog.text


def test_foldx_unavailable_is_logged_and_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    from psf_reasoner.physical.modeling import FoldXMutationModeler

    with caplog.at_level(logging.INFO, logger="psf_reasoner.physical.modeling"):
        modeler = FoldXMutationModeler(foldx_binary="definitely-not-installed-binary")
    assert modeler._foldx_available is False
    status = component_registry.get("foldx")
    assert status is not None and status.available is False
