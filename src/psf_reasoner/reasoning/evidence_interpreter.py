"""Format physical evidence for LLM consumption."""

from __future__ import annotations

from psf_reasoner.schemas.evidence import EvidenceStatus, PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest


def format_evidence_for_llm(
    request: AnalysisRequest,
    evidence: tuple[PhysicalEvidence, ...],
) -> str:
    """Produce a structured text block describing all available evidence.

    The output is designed to be included in an LLM user prompt.  Each
    evidence item is rendered with its status, type, measurement, and
    confidence so the model can weigh conflicting or low-quality signals.
    """
    computed = [e for e in evidence if e.status is EvidenceStatus.COMPUTED]
    inferred = [e for e in evidence if e.status is EvidenceStatus.INFERRED]
    required = [e for e in evidence if e.status is EvidenceStatus.REQUIRED]
    other = [
        e
        for e in evidence
        if e.status not in {EvidenceStatus.COMPUTED, EvidenceStatus.INFERRED, EvidenceStatus.REQUIRED}
    ]

    lines: list[str] = [
        "## Analysis Context",
        f"Ligand: {request.ligand.identifier}",
    ]
    if request.mutation is not None:
        lines.append(f"Mutation: {request.mutation.notation}")
        if request.mutation.chain:
            lines.append(f"Chain: {request.mutation.chain}")
    if request.phenotype is not None:
        lines.append(f"Phenotype: {request.phenotype.name}")
    if request.study_context:
        lines.append(f"Study context: {request.study_context}")
    lines.append("")

    if computed:
        lines.append("## Computed Physical Evidence")
        lines.append("")
        for i, item in enumerate(computed, start=1):
            lines.append(_format_item(i, item))

    if inferred:
        lines.append("## Inferred Evidence (prior-based)")
        lines.append("")
        for i, item in enumerate(inferred, start=1):
            lines.append(_format_item(i, item))

    if required:
        lines.append("## Required Evidence (reverse-predicted, not yet measured)")
        lines.append("")
        for i, item in enumerate(required, start=1):
            lines.append(_format_item(i, item))

    if other:
        lines.append("## Other Evidence")
        for i, item in enumerate(other, start=1):
            lines.append(_format_item(i, item))

    return "\n".join(lines)


def format_context_for_llm(request: AnalysisRequest) -> str:
    """Brief protein/ligand/mutation context for the system prompt."""
    parts = []
    if request.mutation is not None:
        parts.append(f"analysing mutation {request.mutation.notation}")
    if request.ligand is not None:
        parts.append(f"ligand {request.ligand.identifier}")
    if request.phenotype is not None:
        parts.append(f"phenotype={request.phenotype.name}")
    if request.study_context:
        parts.append(f"context: {request.study_context}")
    return "; ".join(parts) if parts else "protein-ligand analysis"


def _format_item(index: int, item: PhysicalEvidence) -> str:
    measurement = ""
    if item.measurement is not None:
        m = item.measurement
        parts = [f"{m.name}: {m.value}"]
        if m.unit:
            parts.append(f" {m.unit}")
        if m.direction is not None:
            parts.append(f" (direction: {m.direction.value})")
        if m.reference_value is not None:
            parts.append(f" [reference: {m.reference_value}]")
        measurement = "".join(parts)

    lines = [
        f"### {index}. {item.title}",
        f"Type: {item.evidence_type.value}",
        f"Status: {item.status.value}",
        f"Confidence: {item.confidence}",
    ]
    if measurement:
        lines.append(f"Measurement: {measurement}")
    lines.append(f"Description: {item.description}")
    if item.limitations:
        lines.append(f"Limitations: {'; '.join(item.limitations)}")
    lines.append("")
    return "\n".join(lines)
