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


def create_default_service() -> AnalysisService:
    """Return an AnalysisService wired with all baseline providers and reasoners.

    Evidence providers are composed in registration order.  The baseline
    reasoner is the only engine active — future LLM / hybrid reasoners will
    be wired here as alternative or complementary implementations of the
    same ForwardReasoner / ReverseReasoner / ConsistencyChecker protocols.
    """
    return AnalysisService(
        evidence_provider=CompositeEvidenceProvider(
            MutationPropertyEvidenceProvider(),
            CoordinateEvidenceProvider(),
            ComparativeEvidenceProvider(),
            PocketNetworkEvidenceProvider(),
            LocalEnergyEvidenceProvider(),
            HIVProteaseCalibrationProvider(),
        ),
        forward_reasoner=BaselineForwardReasoner(),
        reverse_reasoner=BaselineReverseReasoner(),
        consistency_checker=BaselineConsistencyChecker(),
        mutation_modeler=LocalSideChainMutationModeler(),
    )


def create_default_runner(*, persist: bool | None = None) -> AnalysisRunner:
    """Return an AnalysisRunner backed by inline execution.

    By default persistence is in-memory.  When *persist* is ``True`` (or
    unset and the ``PSF_PERSIST`` env var is ``"1"``) reports are stored
    in SQLite under ``.psf_reasoner/reports.db`` so they survive restarts.
    """
    if persist is None:
        persist = os.environ.get("PSF_PERSIST") == "1"

    repository = SqliteReportRepository() if persist else InMemoryReportRepository()

    return AnalysisRunner(
        service=create_default_service(),
        execution=InlineExecutionBackend(),
        reports=repository,
    )
