"""Complete PSF report contract."""

from datetime import UTC, datetime

from pydantic import Field

from psf_reasoner.schemas.common import CalibrationStatus, Confidence, ScientificModel
from psf_reasoner.schemas.consistency import ConsistencyCheck
from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.function import FunctionalHypothesis, ReverseCandidate
from psf_reasoner.schemas.inputs import AnalysisMode, AnalysisRequest
from psf_reasoner.schemas.mechanisms import StructuralMechanism
from psf_reasoner.schemas.preparation import StructurePreparation, StructureQCReport
from psf_reasoner.schemas.validation import MissingEvidence, ValidationPlan


class ReportRuntime(ScientificModel):
    """Which engines and tools actually produced this report.

    Records the reasoning engine, mutation modeler, cloud adapter, LLM
    provider and external tool versions in effect at run time, so every
    report is reproducible with respect to its software environment.
    """

    reasoning_engine: str
    mutation_modeler: str
    llm_provider: str | None = None
    cloud_adapter: str | None = None
    external_tools: dict[str, str] = Field(default_factory=dict)
    component_status: dict[str, dict[str, object]] = Field(default_factory=dict)


class PSFReport(ScientificModel):
    schema_version: str = "1.0.0"
    report_id: str = Field(pattern=r"^report-[a-f0-9]{12}$")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    mode: AnalysisMode
    request: AnalysisRequest
    runtime: ReportRuntime | None = None
    structure_preparation: tuple[StructurePreparation, ...] = ()
    structure_qc: StructureQCReport | None = None
    physical_evidence: tuple[PhysicalEvidence, ...] = ()
    structural_mechanisms: tuple[StructuralMechanism, ...] = ()
    functional_hypotheses: tuple[FunctionalHypothesis, ...] = ()
    reverse_candidates: tuple[ReverseCandidate, ...] = ()
    consistency_checks: tuple[ConsistencyCheck, ...] = ()
    missing_evidence: tuple[MissingEvidence, ...] = ()
    validation_plan: ValidationPlan = Field(default_factory=ValidationPlan)
    confidence: Confidence
    calibration_status: CalibrationStatus = CalibrationStatus.HEURISTIC
    overall_agreement_score: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="V2 Pathway Agreement Score — replaces confidence for report-level summary.",
    )
    limitations: tuple[str, ...] = ()
