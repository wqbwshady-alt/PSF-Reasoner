"""Composition root — wires default implementations for the application.

Domain modules (physical, reasoning, schemas) never import this module.
Only delivery adapters (CLI, API) and tests should depend on the factory
functions defined here.
"""

from psf_reasoner.application.runner import AnalysisRunner
from psf_reasoner.application.service import AnalysisService
from psf_reasoner.infrastructure.execution import InlineExecutionBackend
from psf_reasoner.infrastructure.repository import InMemoryReportRepository
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


def create_default_runner() -> AnalysisRunner:
    """Return an AnalysisRunner backed by inline execution and in-memory storage.

    Replace the execution backend and repository with queue / database
    adapters when moving beyond single-process local use.
    """
    return AnalysisRunner(
        service=create_default_service(),
        execution=InlineExecutionBackend(),
        reports=InMemoryReportRepository(),
    )
