"""Tests for port protocols, boundary exceptions, and dependency direction."""

import pytest

from psf_reasoner.application.ports import (
    AnalysisError,
    ExecutionBackend,
    ReportLookupError,
    ReportNotFoundError,
    ReportRepository,
    StructureInputError,
)
from psf_reasoner.reasoning.ports import LLMCompletion, LLMUsage
from psf_reasoner.schemas.common import Provenance, ProvenanceKind

# ---------------------------------------------------------------------------
# Application boundary exceptions
# ---------------------------------------------------------------------------


class TestApplicationExceptions:
    def test_structure_input_error_is_analysis_error(self) -> None:
        with pytest.raises(AnalysisError):
            raise StructureInputError("bad structure")

    def test_report_lookup_error_is_analysis_error(self) -> None:
        with pytest.raises(AnalysisError):
            raise ReportLookupError("missing")

    def test_report_not_found_is_lookup_error(self) -> None:
        err = ReportNotFoundError("report-abc123")
        assert isinstance(err, LookupError)
        assert str(err) == "report-abc123"


# ---------------------------------------------------------------------------
# Application ports are protocols (structural, not runtime)
# ---------------------------------------------------------------------------


class TestApplicationPorts:
    def test_execution_backend_is_protocol(self) -> None:
        assert hasattr(ExecutionBackend, "execute")

    def test_report_repository_is_protocol(self) -> None:
        assert hasattr(ReportRepository, "save")
        assert hasattr(ReportRepository, "get")


# ---------------------------------------------------------------------------
# LLMCompletion provenance — scalar token fields (no nested dicts)
# ---------------------------------------------------------------------------


class TestLLMCompletionProvenance:
    def test_provenance_with_usage_expands_tokens_to_scalars(self) -> None:
        usage = LLMUsage(prompt_tokens=150, completion_tokens=80, total_tokens=230)
        completion = LLMCompletion(
            content={"mechanisms": []},
            model="test-model-v1",
            usage=usage,
            finish_reason="stop",
        )

        result = completion.provenance("test-method")

        assert len(result) == 1
        prov = result[0]
        assert prov.kind == ProvenanceKind.COMPUTATION
        assert prov.source == "LLM (test-model-v1)"
        assert prov.method == "test-method"

        params = prov.parameters
        # All values must be valid ParameterValue (scalars only, no nested dicts)
        assert params["finish_reason"] == "stop"
        assert params["prompt_tokens"] == 150
        assert params["completion_tokens"] == 80
        assert params["total_tokens"] == 230
        for value in params.values():
            assert isinstance(value, str | int | float | bool | type(None))

    def test_provenance_without_usage_uses_none_tokens(self) -> None:
        completion = LLMCompletion(
            content={},
            model="no-usage-model",
            usage=None,
        )

        result = completion.provenance("bare-method")
        params = result[0].parameters

        assert params["prompt_tokens"] is None
        assert params["completion_tokens"] is None
        assert params["total_tokens"] is None

    def test_provenance_parameters_are_serializable(self) -> None:
        """Provenance must survive a Pydantic model_dump round-trip."""
        completion = LLMCompletion(
            content={"key": "value"},
            model="roundtrip-model",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        provenance = completion.provenance("serialize-test")

        for prov in provenance:
            dumped = prov.model_dump(mode="json")
            reloaded = Provenance(**dumped)
            assert reloaded == prov


# ---------------------------------------------------------------------------
# Dependency direction: core modules must not import infrastructure
# ---------------------------------------------------------------------------


class TestDependencyDirection:
    """Verify that core domain packages do not depend on infrastructure."""

    CORE_PACKAGES = (
        "src/psf_reasoner/schemas/",
        "src/psf_reasoner/physical/",
        "src/psf_reasoner/reasoning/",
        "src/psf_reasoner/application/service.py",
    )

    @pytest.mark.parametrize("package", CORE_PACKAGES)
    def test_core_module_never_imports_infrastructure(self, package: str) -> None:
        import ast
        from pathlib import Path

        root = Path(__file__).parent.parent
        target = root / package
        py_files = [target] if target.is_file() else sorted(target.rglob("*.py"))

        violations: list[str] = []
        for path in py_files:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module is not None
                    and node.module.startswith("psf_reasoner.infrastructure")
                ):
                    violations.append(f"{path}: from {node.module} import ...")

        assert not violations, "Core modules must not import infrastructure:\n" + "\n".join(violations)

    def test_delivery_never_imports_physical_or_infrastructure_directly(self) -> None:
        """CLI and API should use application ports, not domain internals."""
        import ast
        from pathlib import Path

        root = Path(__file__).parent.parent
        delivery_files = [
            root / "src/psf_reasoner/cli.py",
            root / "src/psf_reasoner/api/app.py",
        ]

        forbidden = {
            "psf_reasoner.physical.structure",
            "psf_reasoner.infrastructure.repository",
            "psf_reasoner.infrastructure.execution",
        }

        violations: list[str] = []
        for path in delivery_files:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module is not None and node.module in forbidden:
                    violations.append(f"{path}: from {node.module} import ...")

        assert not violations, (
            "Delivery must not import physical or infrastructure exceptions directly:\n"
            + "\n".join(violations)
        )
