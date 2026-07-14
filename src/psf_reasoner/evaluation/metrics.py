"""Evaluation metrics — mechanism ranking and calibration analysis.

All metrics are EXPLORATORY.  Confidence values remain ``uncalibrated``
until the calibration gate criteria are met (see docs/calibration-gates.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from psf_reasoner.evaluation.protocols import BenchmarkCase
from psf_reasoner.schemas.report import PSFReport


@dataclass
class MechanismRankingMetrics:
    """Mechanism-level evaluation metrics for a single case."""

    case_id: str
    top_mechanism_type: str | None = None
    top_mechanism_title: str | None = None
    mechanism_label_match: bool = False
    mean_reciprocal_rank: float = 0.0
    num_mechanisms: int = 0


@dataclass
class CalibrationBin:
    """A single bin in a reliability diagram."""

    bin_center: float
    n_cases: int
    mean_confidence: float
    mean_accuracy: float


@dataclass
class CalibrationAnalysis:
    """Exploratory calibration analysis — NOT a calibration deployment.

    All confidence values remain ``uncalibrated``.  This analysis is for
    diagnostic purposes only.
    """

    benchmark_id: str
    n_cases: int
    n_held_out: int
    bins: list[CalibrationBin]
    brier_score: float | None = None
    ece: float | None = None  # Expected Calibration Error
    note: str = ""


def compute_mechanism_ranking(
    case: BenchmarkCase, report: PSFReport
) -> MechanismRankingMetrics:
    """Evaluate mechanism ranking against a benchmark case's mechanism label.

    Returns ``MechanismRankingMetrics`` with match status and MRR.
    If the case has no mechanism label, ``mechanism_label_match`` is
    always ``False``.
    """
    mechanisms = report.structural_mechanisms
    if not mechanisms:
        return MechanismRankingMetrics(
            case_id=case.case_id, num_mechanisms=0,
        )

    top = mechanisms[0]
    label = case.mechanism_label

    # Simple string overlap check for mechanism label match.
    # This is intentionally lenient — a full semantic comparison
    # requires expert review.
    match = False
    if label and top.title:
        # Check for keyword overlap between mechanism label and top-ranked mechanism
        label_keywords = set(label.lower().split())
        title_keywords = set(top.title.lower().split())
        overlap = label_keywords & title_keywords
        match = len(overlap) >= 2  # arbitrary threshold for pilot analysis

    # Mean Reciprocal Rank: 1/rank for the first matching mechanism
    mrr = 0.0
    for rank, mech in enumerate(mechanisms, start=1):
        if label and mech.title:
            mech_words = set(mech.title.lower().split())
            if len(label_keywords & mech_words) >= 2:
                mrr = 1.0 / rank
                break

    return MechanismRankingMetrics(
        case_id=case.case_id,
        top_mechanism_type=top.mechanism_type.value if top.mechanism_type else None,
        top_mechanism_title=top.title,
        mechanism_label_match=match,
        mean_reciprocal_rank=mrr,
        num_mechanisms=len(mechanisms),
    )


def compute_calibration_analysis(
    results: list[tuple[BenchmarkCase, PSFReport]],
    n_bins: int = 5,
) -> CalibrationAnalysis:
    """Compute exploratory calibration metrics.

    This is a DIAGNOSTIC analysis only.  It does NOT calibrate confidence
    values.  All confidence values remain ``uncalibrated``.

    Returns a ``CalibrationAnalysis`` with reliability bins, Brier score,
    and Expected Calibration Error.
    """
    if not results:
        return CalibrationAnalysis(
            benchmark_id="empty", n_cases=0, n_held_out=0, bins=[],
            note="No results to analyze.",
        )

    # Build (confidence, match) pairs
    pairs: list[tuple[float, int]] = []
    for case, report in results:
        ranking = compute_mechanism_ranking(case, report)
        pairs.append((report.confidence, 1 if ranking.mechanism_label_match else 0))

    # Bin by confidence
    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    bins: list[CalibrationBin] = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        bin_pairs = [(c, a) for c, a in pairs if lo <= c < hi or (i == n_bins - 1 and c >= lo)]
        if bin_pairs:
            mean_conf = sum(c for c, _ in bin_pairs) / len(bin_pairs)
            mean_acc = sum(a for _, a in bin_pairs) / len(bin_pairs)
            bins.append(CalibrationBin(
                bin_center=(lo + hi) / 2,
                n_cases=len(bin_pairs),
                mean_confidence=round(mean_conf, 3),
                mean_accuracy=round(mean_acc, 3),
            ))
        else:
            bins.append(CalibrationBin(
                bin_center=(lo + hi) / 2, n_cases=0,
                mean_confidence=0.0, mean_accuracy=0.0,
            ))

    # Brier score
    n = len(pairs)
    brier = sum((c - a) ** 2 for c, a in pairs) / n if n > 0 else None

    # Expected Calibration Error
    ece = 0.0
    for b in bins:
        if b.n_cases > 0:
            ece += (b.n_cases / n) * abs(b.mean_confidence - b.mean_accuracy)
    ece = round(ece, 4) if n > 0 else None

    held_out = sum(1 for case, _ in results if case.split == "held_out")

    return CalibrationAnalysis(
        benchmark_id="analysis",
        n_cases=n,
        n_held_out=held_out,
        bins=bins,
        brier_score=round(brier, 4) if brier is not None else None,
        ece=ece,
        note=(
            "EXPLORATORY ONLY.  Confidence values are uncalibrated. "
            "≥30 held-out cases with mechanism labels across ≥2 protein "
            "families are required before calibration can be enabled."
        ),
    )
