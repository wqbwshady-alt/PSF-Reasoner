"""Shared value objects used across scientific layers."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
ParameterValue = str | int | float | bool | None


class ScientificModel(BaseModel):
    """Strict immutable base for report data."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ProvenanceKind(StrEnum):
    INPUT = "input"
    BUILTIN_PRIOR = "builtin_prior"
    STRUCTURE = "structure"
    COMPUTATION = "computation"
    EXPERIMENT = "experiment"
    LITERATURE = "literature"


class Provenance(ScientificModel):
    kind: ProvenanceKind
    source: str = Field(min_length=1)
    method: str | None = None
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)
    notes: str | None = None


class Direction(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    CHANGE = "change"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# V2 Scoring System (Phase 1B) — defined before Claim to avoid forward-ref
# ---------------------------------------------------------------------------


class CalibrationStatus(StrEnum):
    """Whether a confidence score is calibrated against experimental data (V3 P0)."""

    HEURISTIC = "heuristic"
    CALIBRATED = "calibrated"


class QualitativeConfidence(StrEnum):
    """Qualitative confidence levels replacing uncalibrated percentages (V3 P0)."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class ScoreType(StrEnum):
    """Semantic category for a score value — disambiguates what the number means."""

    MECHANISM_SUPPORT = "mechanism_support"
    EVIDENCE_COVERAGE = "evidence_coverage"
    PATHWAY_AGREEMENT = "pathway_agreement"
    VALIDATION_PRIORITY = "validation_priority"


class ScoreBreakdown(ScientificModel):
    """Transparent score decomposition attached to every Claim in V2.

    Replaces the opaque single ``confidence`` number with a structured
    breakdown that shows *why* a score is what it is.
    """

    score_type: ScoreType
    raw_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence_count: int = Field(default=0, ge=0)
    conflicting_evidence_count: int = Field(default=0, ge=0)
    missing_evidence_count: int = Field(default=0, ge=0)
    evidence_quality_factor: float = Field(default=1.0, ge=0.0, le=1.0,
                                           description="QC discount factor, 1.0 = no penalty")


class Claim(ScientificModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*-[a-f0-9]{12}$")
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    confidence: Confidence
    provenance: tuple[Provenance, ...] = ()
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    score_breakdown: ScoreBreakdown | None = None
    calibration_status: CalibrationStatus = CalibrationStatus.HEURISTIC
    qualitative_confidence: QualitativeConfidence | None = None
