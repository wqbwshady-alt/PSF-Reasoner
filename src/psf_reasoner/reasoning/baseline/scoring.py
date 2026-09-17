"""Shared scoring primitives for the baseline reasoning rules."""

from psf_reasoner.schemas.common import (
    Provenance,
    ProvenanceKind,
    QualitativeConfidence,
    ScoreBreakdown,
    ScoreType,
)


def _rule_provenance(rule: str) -> tuple[Provenance, ...]:
    return (
        Provenance(
            kind=ProvenanceKind.BUILTIN_PRIOR,
            source="PSF baseline rules v1",
            method=rule,
        ),
    )


def _bounded(value: float) -> float:
    return round(max(0.0, min(0.95, value)), 3)


def _qualitative(value: float) -> QualitativeConfidence:
    """Map a heuristic numeric score to a qualitative label (V3 P0)."""
    if value >= 0.70:
        return QualitativeConfidence.STRONG
    if value >= 0.45:
        return QualitativeConfidence.MODERATE
    if value >= 0.25:
        return QualitativeConfidence.WEAK
    return QualitativeConfidence.INSUFFICIENT


def _make_score_breakdown(
    score_type: ScoreType,
    raw_score: float,
    supporting: int = 0,
    conflicting: int = 0,
    missing: int = 0,
    quality_factor: float = 1.0,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        score_type=score_type,
        raw_score=round(_bounded(raw_score), 3),
        supporting_evidence_count=supporting,
        conflicting_evidence_count=conflicting,
        missing_evidence_count=missing,
        evidence_quality_factor=round(quality_factor, 3),
    )
