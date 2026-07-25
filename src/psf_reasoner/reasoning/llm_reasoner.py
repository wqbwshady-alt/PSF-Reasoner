"""LLM-powered reasoning engines — implement the same protocols as Baseline."""

from __future__ import annotations

import json

from psf_reasoner.identifiers import make_id
from psf_reasoner.reasoning.evidence_interpreter import (
    format_context_for_llm,
    format_evidence_for_llm,
)
from psf_reasoner.reasoning.ports import LLMProvider
from psf_reasoner.reasoning.results import ForwardResult, ReverseResult
from psf_reasoner.schemas.common import Direction
from psf_reasoner.schemas.consistency import ConsistencyCheck, ConsistencyStatus
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    PhysicalEvidence,
)
from psf_reasoner.schemas.function import FunctionalHypothesis, FunctionType, ReverseCandidate
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import MechanismType, StructuralMechanism
from psf_reasoner.schemas.validation import MissingEvidence, ValidationKind, ValidationStep

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_evidence_type(value: str) -> EvidenceType:
    """Parse an evidence type string from LLM output, with fallback.

    LLMs may confuse ``ValidationKind`` values (e.g. ``"molecular_dynamics"``)
    with ``EvidenceType`` values.  Unknown strings silently fall back to
    ``EvidenceType.ENERGY_COMPONENT`` rather than crashing the pipeline.
    """
    try:
        return EvidenceType(value)
    except ValueError:
        return EvidenceType.ENERGY_COMPONENT


# ---------------------------------------------------------------------------
# JSON Schemas for structured LLM output
# ---------------------------------------------------------------------------

_MECHANISM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "mechanism_type": {
            "type": "string",
            "enum": [m.value for m in MechanismType],
        },
        "direction": {
            "type": "string",
            "enum": [d.value for d in Direction],
        },
        "affected_region": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 0.95},
        "evidence_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "IDs of physical evidence items that support this mechanism",
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "description",
        "mechanism_type",
        "direction",
        "confidence",
        "evidence_ids",
        "limitations",
    ],
    "additionalProperties": False,
}

_HYPOTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "function_type": {
            "type": "string",
            "enum": [f.value for f in FunctionType],
        },
        "direction": {
            "type": "string",
            "enum": [d.value for d in Direction],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 0.95},
        "mechanism_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "description",
        "function_type",
        "direction",
        "confidence",
        "mechanism_ids",
        "limitations",
    ],
    "additionalProperties": False,
}

_CANDIDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "mechanism_type": {
            "type": "string",
            "enum": [m.value for m in MechanismType],
        },
        "expected_evidence_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [e.value for e in EvidenceType],
            },
        },
        "rank": {"type": "integer", "minimum": 1},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 0.95},
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "description",
        "mechanism_type",
        "expected_evidence_types",
        "rank",
        "confidence",
        "limitations",
    ],
    "additionalProperties": False,
}

_MISSING_EVIDENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence_type": {
            "type": "string",
            "enum": [e.value for e in EvidenceType],
        },
        "reason": {"type": "string", "minLength": 1},
        "impact": {"type": "string", "minLength": 1},
    },
    "required": ["evidence_type", "reason", "impact"],
    "additionalProperties": False,
}

_VALIDATION_STEP_SCHEMA = {
    "type": "object",
    "properties": {
        "priority": {"type": "integer", "minimum": 1},
        "kind": {
            "type": "string",
            "enum": [k.value for k in ValidationKind],
        },
        "objective": {"type": "string", "minLength": 1},
        "method": {"type": "string", "minLength": 1},
        "expected_result": {"type": "string", "minLength": 1},
    },
    "required": ["priority", "kind", "objective", "method", "expected_result"],
    "additionalProperties": False,
}

FORWARD_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "mechanisms": {
            "type": "array",
            "items": _MECHANISM_SCHEMA,
            "maxItems": 6,
        },
        "hypotheses": {
            "type": "array",
            "items": _HYPOTHESIS_SCHEMA,
            "maxItems": 4,
        },
        "missing_evidence": {
            "type": "array",
            "items": _MISSING_EVIDENCE_SCHEMA,
            "maxItems": 6,
        },
        "validation_steps": {
            "type": "array",
            "items": _VALIDATION_STEP_SCHEMA,
            "maxItems": 6,
        },
    },
    "required": ["mechanisms", "hypotheses", "missing_evidence", "validation_steps"],
    "additionalProperties": False,
}

REVERSE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": _CANDIDATE_SCHEMA,
            "maxItems": 5,
        },
        "required_evidence_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [e.value for e in EvidenceType],
            },
            "maxItems": 6,
        },
        "missing_evidence": {
            "type": "array",
            "items": _MISSING_EVIDENCE_SCHEMA,
            "maxItems": 6,
        },
        "validation_steps": {
            "type": "array",
            "items": _VALIDATION_STEP_SCHEMA,
            "maxItems": 6,
        },
    },
    "required": ["candidates", "required_evidence_types", "missing_evidence", "validation_steps"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_FORWARD_SYSTEM = """\
你是一位结构生物学推理助手。你的任务是分析蛋白质突变的物理计算证据，并提出：

1. **结构机制** — 突变如何改变配体结合位点的蛋白质结构。
   考虑口袋堆积、氢键网络、疏水接触、水桥、盐桥、
   π相互作用、残基网络重构、静电变化和构象偏好。
   每个机制必须引用具体的证据 ID。

2. **功能假设** — 从结构机制推导出什么生物学后果。
   考虑配体亲和力、催化活性、蛋白质稳定性、耐药性、
   配体选择性和别构调控。每个假设必须引用机制 ID。

3. **缺失证据** — 哪些关键数据缺失限制了置信度。
   具体说明每个缺失为什么重要。

4. **验证步骤** — 哪些实验或计算可以测试提出的机制，
   按优先级排序。

规则：
- 只使用提供的枚举中的证据类型和机制类型。
- 置信度必须在 0.0-0.95 之间（永远不要用 1.0 —
  仅凭计算无法达到绝对确定）。
- 清楚区分"由证据支持"和"推断"。
- 保持保守：当证据质量低或模糊时，如实说明，
  不要过度解读。
- 用中文输出 title 和 description 字段。
- 输出符合 JSON Schema 的有效 JSON。"""

_REVERSE_SYSTEM = """\
你是一位结构生物学推理助手。给定一个功能表型（如耐药性），
反向推理提出：

1. **候选结构机制** — 哪些结构变化可以解释观察到的表型。
   按合理性排序。

2. **需要的证据类型** — 每个候选机制需要观察到什么
   物理证据才能得到支持。

3. **缺失证据** — 目前缺少什么，为什么对区分候选机制
   很重要。

4. **验证步骤** — 哪些实验或计算可以区分候选机制，
   按优先级排序。

规则：
- 只使用提供的枚举中的证据类型和机制类型。
- 置信度必须在 0.0-0.95 之间。
- 承认多种机制可能产生相同表型。
- 用中文输出 title 和 description 字段。
- 输出符合 JSON Schema 的有效 JSON。"""

# ---------------------------------------------------------------------------
# Reasoner implementations
# ---------------------------------------------------------------------------


class LLMForwardReasoner:
    """Forward reasoning (P→S→F) powered by a structured LLM completion."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def reason(
        self,
        request: AnalysisRequest,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> ForwardResult:
        if request.mutation is None:
            return ForwardResult()

        user_prompt = format_evidence_for_llm(request, evidence)
        completion = self._provider.complete(
            system_prompt=_FORWARD_SYSTEM,
            user_prompt=user_prompt,
            output_schema=FORWARD_OUTPUT_SCHEMA,
            temperature=0.0,
            max_tokens=4096,
        )
        data = completion.content
        context = format_context_for_llm(request)
        prov_entries = completion.provenance("LLM forward reasoning")

        mechanisms = tuple(
            StructuralMechanism(
                id=make_id("mechanism", "llm_forward", item["mechanism_type"], context),
                title=item["title"],
                description=item["description"],
                mechanism_type=MechanismType(item["mechanism_type"]),
                direction=Direction(item["direction"]),
                affected_region=item.get("affected_region"),
                confidence=_bounded(item["confidence"]),
                provenance=(*prov_entries,),
                supports=tuple(item.get("evidence_ids", [])),
                limitations=tuple(item.get("limitations", [])),
            )
            for item in data.get("mechanisms", [])
        )
        mechanism_ids = tuple(m.id for m in mechanisms)

        hypotheses = tuple(
            FunctionalHypothesis(
                id=make_id("hypothesis", "llm_forward", item["function_type"], context),
                title=item["title"],
                description=item["description"],
                function_type=FunctionType(item["function_type"]),
                direction=Direction(item["direction"]),
                confidence=_bounded(item["confidence"]),
                provenance=(*prov_entries,),
                supports=tuple(item.get("mechanism_ids", [])),
                limitations=tuple(item.get("limitations", [])),
            )
            for item in data.get("hypotheses", [])
        )

        missing = tuple(
            MissingEvidence(
                id=make_id("missing", "llm_forward", item["evidence_type"], context),
                evidence_type=_safe_evidence_type(item["evidence_type"]),
                reason=item["reason"],
                impact=item["impact"],
                related_claims=mechanism_ids,
            )
            for item in data.get("missing_evidence", [])
        )
        missing_ids = tuple(m.id for m in missing)

        steps = tuple(
            ValidationStep(
                id=make_id("validation", "llm_forward", str(item["priority"]), context),
                priority=max(1, min(5, item["priority"])),
                kind=ValidationKind(item["kind"]),
                objective=item["objective"],
                method=item["method"],
                expected_result=item["expected_result"],
                addresses=missing_ids,
            )
            for item in data.get("validation_steps", [])
        )

        return ForwardResult(
            mechanisms=mechanisms,
            hypotheses=hypotheses,
            missing_evidence=missing,
            validation_steps=steps,
        )


class LLMReverseReasoner:
    """Reverse reasoning (F→S→P) powered by a structured LLM completion."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def reason(
        self,
        request: AnalysisRequest,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> ReverseResult:
        phenotype = request.phenotype
        if phenotype is None:
            return ReverseResult()

        user_prompt = format_evidence_for_llm(request, evidence)
        completion = self._provider.complete(
            system_prompt=_REVERSE_SYSTEM,
            user_prompt=user_prompt,
            output_schema=REVERSE_OUTPUT_SCHEMA,
            temperature=0.0,
            max_tokens=4096,
        )
        data = completion.content
        context = format_context_for_llm(request)
        prov_entries = completion.provenance("LLM reverse reasoning")

        candidates = tuple(
            ReverseCandidate(
                id=make_id("candidate", "llm_reverse", item["mechanism_type"], context),
                title=item["title"],
                description=item["description"],
                mechanism_type=MechanismType(item["mechanism_type"]),
                expected_evidence=tuple(
                    make_id("evidence", "required", "llm_reverse", et, context)
                    for et in item.get("expected_evidence_types", [])
                ),
                rank=item["rank"],
                confidence=_bounded(item["confidence"]),
                provenance=(*prov_entries,),
                limitations=tuple(item.get("limitations", [])),
            )
            for item in data.get("candidates", [])
        )
        candidate_ids = tuple(c.id for c in candidates)

        required_evidence = tuple(
            PhysicalEvidence(
                id=make_id("evidence", "required", "llm_reverse", et, context),
                title=f"Required: {et}",
                description=f"Reverse-predicted {et} evidence needed to test candidate mechanisms.",
                evidence_type=_safe_evidence_type(et),
                status=EvidenceStatus.REQUIRED,
                entities=(phenotype.name,),
                confidence=0.55,
                provenance=(*prov_entries,),
                limitations=("This is an LLM-generated prediction to test.",),
            )
            for et in data.get("required_evidence_types", [])
        )

        missing = tuple(
            MissingEvidence(
                id=make_id("missing", "llm_reverse", item["evidence_type"], context),
                evidence_type=_safe_evidence_type(item["evidence_type"]),
                reason=item["reason"],
                impact=item["impact"],
                related_claims=candidate_ids,
            )
            for item in data.get("missing_evidence", [])
        )
        missing_ids = tuple(m.id for m in missing)

        steps = tuple(
            ValidationStep(
                id=make_id("validation", "llm_reverse", str(item["priority"]), context),
                priority=max(1, min(5, item["priority"])),
                kind=ValidationKind(item["kind"]),
                objective=item["objective"],
                method=item["method"],
                expected_result=item["expected_result"],
                addresses=missing_ids,
            )
            for item in data.get("validation_steps", [])
        )

        return ReverseResult(
            candidates=candidates,
            required_evidence=required_evidence,
            missing_evidence=missing,
            validation_steps=steps,
            mechanisms=(),
        )


class LLMConsistencyChecker:
    """Cross-validate forward and reverse reasoning results via LLM."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def check(
        self,
        forward: ForwardResult,
        reverse: ReverseResult,
        evidence: tuple[PhysicalEvidence, ...],
    ) -> tuple[ConsistencyCheck, ...]:
        if not forward.mechanisms or not reverse.candidates:
            return (
                ConsistencyCheck(
                    id=make_id("check", "llm_insufficient"),
                    title="Bidirectional comparison unavailable",
                    description="Both forward and reverse results are needed for LLM consistency checking.",
                    status=ConsistencyStatus.INSUFFICIENT_EVIDENCE,
                    compared_claims=tuple(item.id for item in (*forward.mechanisms, *reverse.candidates)),
                    confidence=1.0,
                ),
            )

        forward_text = json.dumps(
            [{"id": m.id, "type": m.mechanism_type.value, "title": m.title} for m in forward.mechanisms],
            indent=2,
        )
        reverse_text = json.dumps(
            [{"id": c.id, "type": c.mechanism_type.value, "title": c.title} for c in reverse.candidates],
            indent=2,
        )

        system_prompt = """\
你正在检查两条独立推理路径的一致性：
- 正向：突变 → 物理证据 → 结构机制 → 功能假设
- 反向：功能表型 → 候选结构机制 → 需要的证据

比较机制类型，判断两条路径是收敛、发散还是解决不同方面的问题。
用中文输出 title 和 description 字段。输出 JSON。"""

        output_schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [s.value for s in ConsistencyStatus],
                },
                "title": {"type": "string"},
                "description": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 0.95},
                "shared_mechanism_types": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["status", "title", "description", "confidence", "shared_mechanism_types"],
            "additionalProperties": False,
        }

        user_prompt = f"## Forward mechanisms\n{forward_text}\n\n## Reverse candidates\n{reverse_text}"

        completion = self._provider.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            temperature=0.0,
            max_tokens=1024,
        )
        data = completion.content

        forward_by_type = {m.mechanism_type: m for m in forward.mechanisms}
        reverse_by_type = {c.mechanism_type: c for c in reverse.candidates}
        shared = set(data.get("shared_mechanism_types", []))

        if not shared:
            return (
                ConsistencyCheck(
                    id=make_id("check", "llm_consistency"),
                    title=data.get("title", "LLM consistency check"),
                    description=data.get("description", ""),
                    status=ConsistencyStatus(data.get("status", "conflict")),
                    compared_claims=tuple(item.id for item in (*forward.mechanisms, *reverse.candidates)),
                    confidence=_bounded(data.get("confidence", 0.5)),
                    provenance=(*completion.provenance("LLM consistency check"),),
                ),
            )

        checks: list[ConsistencyCheck] = []
        for mt_str in shared:
            mt = MechanismType(mt_str)
            fwd = forward_by_type.get(mt)
            rev = reverse_by_type.get(mt)
            claims = tuple(item.id for item in (fwd, rev) if item is not None)
            if not claims:
                continue
            checks.append(
                ConsistencyCheck(
                    id=make_id("check", "llm_consistency", mt_str),
                    title=f"Forward and reverse paths converge on {mt.value}",
                    description=data.get("description", ""),
                    status=ConsistencyStatus.CONSISTENT
                    if fwd and rev
                    else ConsistencyStatus.INSUFFICIENT_EVIDENCE,
                    compared_claims=claims,
                    confidence=_bounded(data.get("confidence", 0.5)),
                    provenance=(*completion.provenance("LLM consistency check"),),
                    supports=claims,
                )
            )

        return (
            tuple(checks)
            if checks
            else (
                ConsistencyCheck(
                    id=make_id("check", "llm_consistency"),
                    title=data.get("title", "LLM consistency check"),
                    description=data.get("description", ""),
                    status=ConsistencyStatus(data.get("status", "conflict")),
                    compared_claims=tuple(item.id for item in (*forward.mechanisms, *reverse.candidates)),
                    confidence=_bounded(data.get("confidence", 0.5)),
                    provenance=(*completion.provenance("LLM consistency check"),),
                ),
            )
        )


def _bounded(value: float) -> float:
    return round(max(0.0, min(0.95, value)), 3)
