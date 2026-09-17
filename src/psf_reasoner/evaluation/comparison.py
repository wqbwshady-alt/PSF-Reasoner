"""Reasoning comparison — Baseline vs LLM side-by-side evaluation.

Compares mechanism rankings, confidence distributions, and agreement
metrics between the Baseline and LLM reasoning engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psf_reasoner.evaluation.protocols import BenchmarkCase
from psf_reasoner.schemas.report import PSFReport


@dataclass
class ReasonerOutput:
    """Output of a single reasoner on a single case."""

    case_id: str
    engine: str  # "baseline" | "llm"
    num_mechanisms: int = 0
    num_hypotheses: int = 0
    num_candidates: int = 0
    top_mechanism_type: str | None = None
    top_mechanism_title: str | None = None
    confidence: float = 0.0
    error: str | None = None


@dataclass
class ComparisonResult:
    """Side-by-side comparison of two reasoners on one case."""

    case_id: str
    baseline: ReasonerOutput | None = None
    llm: ReasonerOutput | None = None
    mechanism_types_match: bool = False
    top_mechanism_jaccard: float = 0.0
    notes: str = ""


def extract_reasoner_output(case: BenchmarkCase, report: PSFReport, engine: str) -> ReasonerOutput:
    """Extract key outputs from a PSFReport for comparison."""
    mechanisms = report.structural_mechanisms
    return ReasonerOutput(
        case_id=case.case_id,
        engine=engine,
        num_mechanisms=len(mechanisms),
        num_hypotheses=len(report.functional_hypotheses),
        num_candidates=len(report.reverse_candidates),
        top_mechanism_type=mechanisms[0].mechanism_type.value
        if mechanisms and mechanisms[0].mechanism_type
        else None,
        top_mechanism_title=mechanisms[0].title if mechanisms else None,
        confidence=report.confidence,
    )


def compare_reasoners(
    case: BenchmarkCase,
    baseline_report: PSFReport,
    llm_report: PSFReport | None,
) -> ComparisonResult:
    """Compare Baseline and LLM outputs on a single case.

    If *llm_report* is ``None`` (LLM not configured), only Baseline
    output is populated.
    """
    baseline = extract_reasoner_output(case, baseline_report, "baseline")
    llm = extract_reasoner_output(case, llm_report, "llm") if llm_report is not None else None

    mechanism_types_match = False
    jaccard = 0.0
    notes = ""

    if baseline and llm:
        # Compare top mechanism types
        mechanism_types_match = baseline.top_mechanism_type == llm.top_mechanism_type

        # Jaccard similarity of mechanism titles (simple token overlap)
        if baseline.top_mechanism_title and llm.top_mechanism_title:
            baseline_tokens = set(baseline.top_mechanism_title.lower().split())
            llm_tokens = set(llm.top_mechanism_title.lower().split())
            intersection = baseline_tokens & llm_tokens
            union = baseline_tokens | llm_tokens
            jaccard = round(len(intersection) / len(union), 3) if union else 0.0

        if not mechanism_types_match:
            notes = (
                f"Mechanism type mismatch: baseline={baseline.top_mechanism_type}, "
                f"llm={llm.top_mechanism_type}"
            )
    elif llm is None:
        notes = "LLM not configured — comparison unavailable"

    return ComparisonResult(
        case_id=case.case_id,
        baseline=baseline,
        llm=llm,
        mechanism_types_match=mechanism_types_match,
        top_mechanism_jaccard=jaccard,
        notes=notes,
    )


@dataclass
class ComparisonSummary:
    """Aggregate comparison across multiple cases."""

    n_cases: int = 0
    n_llm_available: int = 0
    mechanism_type_agreement_rate: float = 0.0
    mean_jaccard: float = 0.0
    baseline_mean_confidence: float = 0.0
    llm_mean_confidence: float = 0.0
    results: list[ComparisonResult] = field(default_factory=list)
    note: str = ""


def summarize_comparison(results: list[ComparisonResult]) -> ComparisonSummary:
    """Aggregate per-case comparisons into a summary."""
    if not results:
        return ComparisonSummary(note="No results to summarize.")

    llm_available = [r for r in results if r.llm is not None]
    type_matches = sum(1 for r in llm_available if r.mechanism_types_match)
    jaccards = [r.top_mechanism_jaccard for r in llm_available if r.top_mechanism_jaccard > 0]

    return ComparisonSummary(
        n_cases=len(results),
        n_llm_available=len(llm_available),
        mechanism_type_agreement_rate=(round(type_matches / len(llm_available), 3) if llm_available else 0.0),
        mean_jaccard=round(sum(jaccards) / len(jaccards), 3) if jaccards else 0.0,
        baseline_mean_confidence=round(
            sum(r.baseline.confidence for r in results if r.baseline) / len(results), 3
        )
        if results
        else 0.0,
        llm_mean_confidence=round(sum(r.llm.confidence for r in llm_available) / len(llm_available), 3)
        if llm_available
        else 0.0,
        results=results,
        note=(
            "EXPLORATORY ONLY.  Requires frozen benchmark with mechanism labels "
            "and validated physical evidence before quantitative conclusions."
        ),
    )
