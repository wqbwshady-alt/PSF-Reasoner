"""Composition root — wires default implementations for the application.

Domain modules (physical, reasoning, schemas) never import this module.
Only delivery adapters (CLI, API) and tests should depend on the factory
functions defined here.
"""

from __future__ import annotations

import os

from psf_reasoner.application.runner import AnalysisRunner
from psf_reasoner.application.service import AnalysisService
from psf_reasoner.infrastructure.execution import InlineExecutionBackend
from psf_reasoner.infrastructure.repository import InMemoryReportRepository
from psf_reasoner.infrastructure.sqlite_repository import SqliteReportRepository
from psf_reasoner.physical.base import CompositeEvidenceProvider
from psf_reasoner.physical.baseline import MutationPropertyEvidenceProvider
from psf_reasoner.physical.calibration import HIVProteaseCalibrationProvider
from psf_reasoner.physical.comparison import ComparativeEvidenceProvider
from psf_reasoner.physical.coordinates import CoordinateEvidenceProvider
from psf_reasoner.physical.energy import LocalEnergyEvidenceProvider
from psf_reasoner.physical.modeling import LocalSideChainMutationModeler
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
    else:
        forward_reasoner = BaselineForwardReasoner()
        reverse_reasoner = BaselineReverseReasoner()
        consistency_checker = BaselineConsistencyChecker()

    return AnalysisService(
        evidence_provider=CompositeEvidenceProvider(
            MutationPropertyEvidenceProvider(),
            CoordinateEvidenceProvider(),
            ComparativeEvidenceProvider(),
            PocketNetworkEvidenceProvider(),
            LocalEnergyEvidenceProvider(),
            HIVProteaseCalibrationProvider(),
        ),
        forward_reasoner=forward_reasoner,
        reverse_reasoner=reverse_reasoner,
        consistency_checker=consistency_checker,
        mutation_modeler=LocalSideChainMutationModeler(),
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
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _auto_llm_provider() -> LLMProvider | None:
    """Create an Anthropic provider when ``PSF_LLM=1`` and a key is set."""
    if os.environ.get("PSF_LLM") != "1":
        return None
    try:
        from psf_reasoner.infrastructure.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    except Exception:
        return None
