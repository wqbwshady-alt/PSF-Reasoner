"""Format physical evidence for LLM consumption (Chinese output)."""

from __future__ import annotations

from psf_reasoner.schemas.evidence import EvidenceStatus, PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest


def format_evidence_for_llm(
    request: AnalysisRequest,
    evidence: tuple[PhysicalEvidence, ...],
) -> str:
    """Produce a structured Chinese text block describing all available evidence."""
    computed = [e for e in evidence if e.status is EvidenceStatus.COMPUTED]
    inferred = [e for e in evidence if e.status is EvidenceStatus.INFERRED]
    required = [e for e in evidence if e.status is EvidenceStatus.REQUIRED]
    other = [
        e
        for e in evidence
        if e.status not in {EvidenceStatus.COMPUTED, EvidenceStatus.INFERRED, EvidenceStatus.REQUIRED}
    ]

    lines: list[str] = [
        "## 分析上下文",
        f"配体: {request.ligand.identifier}",
    ]
    if request.mutation is not None:
        lines.append(f"突变: {request.mutation.notation}")
        if request.mutation.chain:
            lines.append(f"链: {request.mutation.chain}")
    if request.phenotype is not None:
        lines.append(f"表型: {request.phenotype.name}")
    if request.study_context:
        lines.append(f"研究背景: {request.study_context}")
    lines.append("")

    if computed:
        lines.append("## 计算得到的物理证据")
        lines.append("")
        for i, item in enumerate(computed, start=1):
            lines.append(_format_item(i, item))

    if inferred:
        lines.append("## 推断证据（基于先验知识）")
        lines.append("")
        for i, item in enumerate(inferred, start=1):
            lines.append(_format_item(i, item))

    if required:
        lines.append("## 需要的证据（反向预测，尚未测量）")
        lines.append("")
        for i, item in enumerate(required, start=1):
            lines.append(_format_item(i, item))

    if other:
        lines.append("## 其他证据")
        for i, item in enumerate(other, start=1):
            lines.append(_format_item(i, item))

    return "\n".join(lines)


def format_context_for_llm(request: AnalysisRequest) -> str:
    """Brief context for the system prompt."""
    parts = []
    if request.mutation is not None:
        parts.append(f"分析突变 {request.mutation.notation}")
    if request.ligand is not None:
        parts.append(f"配体 {request.ligand.identifier}")
    if request.phenotype is not None:
        parts.append(f"表型={request.phenotype.name}")
    if request.study_context:
        parts.append(f"背景: {request.study_context}")
    return "; ".join(parts) if parts else "蛋白质-配体分析"


def _format_item(index: int, item: PhysicalEvidence) -> str:
    measurement = ""
    if item.measurement is not None:
        m = item.measurement
        parts = [f"{m.name}: {m.value}"]
        if m.unit:
            parts.append(f" {m.unit}")
        if m.direction is not None:
            parts.append(f" (方向: {m.direction.value})")
        if m.reference_value is not None:
            parts.append(f" [参考值: {m.reference_value}]")
        measurement = "".join(parts)

    lines = [
        f"### {index}. {item.title}",
        f"类型: {item.evidence_type.value}",
        f"状态: {item.status.value}",
        f"置信度: {item.confidence}",
    ]
    if measurement:
        lines.append(f"测量值: {measurement}")
    lines.append(f"描述: {item.description}")
    if item.limitations:
        lines.append(f"局限性: {'; '.join(item.limitations)}")
    lines.append("")
    return "\n".join(lines)
