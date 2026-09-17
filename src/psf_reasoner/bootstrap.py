"""Composition root — wires default implementations for the application.

Domain modules (physical, reasoning, schemas) never import this module.
Only delivery adapters (CLI, API) and tests should depend on the factory
functions defined here.
"""

from __future__ import annotations

import logging
import os
import shutil
from functools import partial

from psf_reasoner.application.runner import AnalysisRunner
from psf_reasoner.application.service import AnalysisService
from psf_reasoner.infrastructure.cloud_compute import HttpCloudAdapter
from psf_reasoner.component_status import ComponentStatus, component_registry
from psf_reasoner.infrastructure.execution import InlineExecutionBackend
from psf_reasoner.infrastructure.repository import InMemoryReportRepository
from psf_reasoner.infrastructure.sqlite_repository import SqliteReportRepository
from psf_reasoner.physical.base import CompositeEvidenceProvider
from psf_reasoner.physical.baseline import MutationPropertyEvidenceProvider
from psf_reasoner.physical.calibration import HIVProteaseCalibrationProvider
from psf_reasoner.physical.cloud_provider import CloudEvidenceProvider
from psf_reasoner.physical.comparison import ComparativeEvidenceProvider
from psf_reasoner.physical.coordinates import CoordinateEvidenceProvider
from psf_reasoner.physical.energy import LocalEnergyEvidenceProvider
from psf_reasoner.physical.modeling import (
    FoldXMutationModeler,
    LocalSideChainMutationModeler,
)
from psf_reasoner.physical.pocket import PocketNetworkEvidenceProvider
from psf_reasoner.reasoning.baseline import (
    BaselineConsistencyChecker,
    BaselineForwardReasoner,
    BaselineReverseReasoner,
)
from psf_reasoner.reasoning.llm_reasoner import (
    LLMConsistencyChecker,
    LLMForwardReasoner,
    LLMReverseReasoner,
)
from psf_reasoner.reasoning.ports import LLMProvider
from psf_reasoner.schemas.report import ReportRuntime

logger = logging.getLogger(__name__)


def create_default_service(
    *,
    llm_provider: LLMProvider | None = None,
) -> AnalysisService:
    """Return an AnalysisService wired with all baseline providers and reasoners.

    When *llm_provider* is given (or ``PSF_LLM=1`` is set and an
    ``ANTHROPIC_API_KEY`` is available), the LLM reasoning engine is used
    instead of the deterministic baseline.  Otherwise the baseline engine
    serves as the default.
    """
    if llm_provider is None:
        llm_provider = _auto_llm_provider()

    if llm_provider is not None:
        forward_reasoner = LLMForwardReasoner(llm_provider)
        reverse_reasoner = LLMReverseReasoner(llm_provider)
        consistency_checker = LLMConsistencyChecker(llm_provider)
        component_registry.set(
            ComponentStatus(
                "reasoning_engine",
                enabled=True,
                available=True,
                implementation=f"llm:{_llm_provider_name()}",
            )
        )
    else:
        forward_reasoner = BaselineForwardReasoner()
        reverse_reasoner = BaselineReverseReasoner()
        consistency_checker = BaselineConsistencyChecker()
        component_registry.set(
            ComponentStatus(
                "reasoning_engine",
                enabled=False,
                available=True,
                implementation="baseline",
                detail="deterministic local rules (default; set PSF_LLM=1 for LLM reasoning)",
            )
        )

    modeler = _mutation_modeler()
    cloud_adapter = _cloud_adapter()
    component_registry.set(
        ComponentStatus(
            "cloud_adapter",
            enabled=cloud_adapter is not None,
            available=cloud_adapter is not None,
            implementation=cloud_adapter._base_url if cloud_adapter else "disabled",
            detail="set PSF_CLOUD_URL to offload FPocket/coulombic computation",
        )
    )

    return AnalysisService(
        evidence_provider=CompositeEvidenceProvider(
            MutationPropertyEvidenceProvider(),
            CoordinateEvidenceProvider(),
            ComparativeEvidenceProvider(),
            PocketNetworkEvidenceProvider(),
            LocalEnergyEvidenceProvider(),
            HIVProteaseCalibrationProvider(),
            CloudEvidenceProvider(adapter=cloud_adapter),
        ),
        forward_reasoner=forward_reasoner,
        reverse_reasoner=reverse_reasoner,
        consistency_checker=consistency_checker,
        mutation_modeler=modeler,
    )


def create_default_runner(
    *,
    persist: bool | None = None,
    llm_provider: LLMProvider | None = None,
) -> AnalysisRunner:
    """Return an AnalysisRunner backed by inline execution.

    By default persistence is in-memory.  When *persist* is ``True`` (or
    unset and the ``PSF_PERSIST`` env var is ``"1"``) reports are stored
    in SQLite under ``.psf_reasoner/reports.db`` so they survive restarts.
    """
    if persist is None:
        persist = os.environ.get("PSF_PERSIST") == "1"

    repository = SqliteReportRepository() if persist else InMemoryReportRepository()

    return AnalysisRunner(
        service=create_default_service(llm_provider=llm_provider),
        execution=InlineExecutionBackend(),
        reports=repository,
        runtime_factory=partial(_build_runtime),
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _cloud_adapter() -> HttpCloudAdapter | None:
    """Return an HTTP cloud adapter when PSF_CLOUD_URL is set."""
    cloud_url = os.environ.get("PSF_CLOUD_URL", "")
    if not cloud_url:
        return None
    return HttpCloudAdapter(base_url=cloud_url)


def _mutation_modeler():
    """Select the mutation modeler.

    Default: local side-chain truncation modeler (honest, deterministic).
    With ``PSF_FOLDX=1``: FoldX BuildModel adapter — it detects whether a
    ``foldx`` binary is available and falls back to the local modeler when
    it is not.  No modelling claims are made beyond what the selected
    engine actually computed.
    """
    if os.environ.get("PSF_FOLDX") == "1":
        return FoldXMutationModeler()
    component_registry.set(
        ComponentStatus(
            "mutation_modeler",
            enabled=False,
            available=True,
            implementation="local_side_chain",
            detail="deterministic side-chain truncation (default; set PSF_FOLDX=1 for FoldX)",
        )
    )
    return LocalSideChainMutationModeler()


def _auto_llm_provider() -> LLMProvider | None:
    """Create an LLM provider when ``PSF_LLM=1``.

    Provider selection (env ``PSF_LLM_PROVIDER``):
    - ``deepseek`` (default) — DeepSeek API, needs ``DEEPSEEK_API_KEY``
    - ``anthropic`` — Anthropic Claude, needs ``ANTHROPIC_API_KEY``
    """
    if os.environ.get("PSF_LLM") != "1":
        return None

    provider_name = os.environ.get("PSF_LLM_PROVIDER", "deepseek")

    try:
        if provider_name == "anthropic":
            from psf_reasoner.infrastructure.anthropic_provider import AnthropicProvider

            provider = AnthropicProvider()
        elif provider_name == "deepseek":
            from psf_reasoner.infrastructure.deepseek_provider import DeepSeekProvider

            provider = DeepSeekProvider()
        else:
            # Unknown provider names must not silently become deepseek.
            raise ValueError(f"unknown PSF_LLM_PROVIDER: {provider_name!r}")
    except Exception as exc:
        # Log the degradation reason (never credentials) and surface it in
        # the component registry instead of silently falling back.
        logger.warning("LLM provider %r unavailable, falling back to baseline: %s", provider_name, exc)
        component_registry.set(
            ComponentStatus(
                "llm",
                enabled=True,
                available=False,
                implementation="baseline",
                detail=f"{provider_name} unavailable: {type(exc).__name__}",
            )
        )
        return None

    component_registry.set(
        ComponentStatus(
            "llm",
            enabled=True,
            available=True,
            implementation=f"llm:{provider_name}",
        )
    )
    return provider


def _llm_provider_name() -> str:
    return os.environ.get("PSF_LLM_PROVIDER", "deepseek")


def _build_runtime() -> ReportRuntime:
    """Snapshot the component registry into the report's runtime record."""
    import gemmi

    reasoning = component_registry.get("reasoning_engine")
    modeler = component_registry.get("mutation_modeler")
    foldx = component_registry.get("foldx")
    tools = {
        "gemmi": getattr(gemmi, "__version__", "unknown"),
        "fpocket": "available" if shutil.which("fpocket") else "not-installed",
    }
    if foldx is not None:
        tools["foldx"] = foldx.detail or ("available" if foldx.available else "not-installed")
    return ReportRuntime(
        reasoning_engine=reasoning.implementation if reasoning else "unknown",
        mutation_modeler=modeler.implementation if modeler else "unknown",
        llm_provider=_llm_provider_name() if os.environ.get("PSF_LLM") == "1" else None,
        cloud_adapter=os.environ.get("PSF_CLOUD_URL") or None,
        external_tools=tools,
        component_status=component_registry.snapshot(),
    )
