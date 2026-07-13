"""Complete PSF report contract."""

from datetime import UTC, datetime

from pydantic import Field

from psf_reasoner.schemas.common import Confidence, ScientificModel
from psf_reasoner.schemas.consistency import ConsistencyCheck
from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.function import FunctionalHypothesis, ReverseCandidate
from psf_reasoner.schemas.inputs import AnalysisMode, AnalysisRequest
from psf_reasoner.schemas.mechanisms import StructuralMechanism
from psf_reasoner.schemas.preparation import StructurePreparation
from psf_reasoner.schemas.validation import MissingEvidence, ValidationPlan


class PSFReport(ScientificModel):
    schema_version: str = "1.0.0"
    report_id: str = Field(pattern=r"^report-[a-f0-9]{12}$")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    mode: AnalysisMode
    request: AnalysisRequest
    structure_preparation: tuple[StructurePreparation, ...] = ()
    physical_evidence: tuple[PhysicalEvidence, ...] = ()
    structural_mechanisms: tuple[StructuralMechanism, ...] = ()
    functional_hypotheses: tuple[FunctionalHypothesis, ...] = ()
    reverse_candidates: tuple[ReverseCandidate, ...] = ()
    consistency_checks: tuple[ConsistencyCheck, ...] = ()
    missing_evidence: tuple[MissingEvidence, ...] = ()
    validation_plan: ValidationPlan = Field(default_factory=ValidationPlan)
    confidence: Confidence
    limitations: tuple[str, ...] = ()
