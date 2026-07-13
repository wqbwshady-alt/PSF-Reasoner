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
You are a structural biology reasoning assistant. Your task is to analyse
computed physical evidence for a protein mutation and propose:

1. **Structural mechanisms** — how the mutation changes the protein's
   structure at the ligand binding site.  Consider pocket packing,
   hydrogen-bond networks, hydrophobic contacts, water bridges, salt
   bridges, pi interactions, residue-network rewiring, electrostatic
   changes, and conformational preferences.  Every mechanism MUST cite
   specific evidence IDs.

2. **Functional hypotheses** — what biological consequences follow from
   the structural mechanisms.  Consider ligand affinity, catalytic
   activity, protein stability, drug resistance, ligand selectivity,
   and allosteric regulation.  Every hypothesis MUST cite mechanism IDs.

3. **Missing evidence** — what critical data is unavailable that limits
   confidence.  Be specific about why each gap matters.

4. **Validation steps** — what experiments or computations would test
   the proposed mechanisms, ordered by priority.

Rules:
- Only use evidence types and mechanism types from the provided enums.
- Confidence must be 0.0-0.95 (never 1.0 - absolute certainty is not
  achievable from computation alone).
- Distinguish clearly between "supported by evidence" and "inferred".
- Be conservative: when evidence is low-quality or ambiguous, say so
  rather than over-interpreting.
- Output valid JSON conforming to the schema."""

_REVERSE_SYSTEM = """\
You are a structural biology reasoning assistant.  Given a functional
phenotype (e.g. drug resistance), work backwards to propose:

1. **Candidate structural mechanisms** — what structural changes could
   explain the observed phenotype.  Rank by plausibility.

2. **Required evidence types** — what physical evidence would need to
   be observed for each candidate mechanism to be supported.

3. **Missing evidence** — what is currently unavailable and why it
   matters for discriminating between candidates.

4. **Validation steps** — what experiments or computations would
   distinguish between the candidates, ordered by priority.

Rules:
- Only use evidence types and mechanism types from the provided enums.
- Confidence must be 0.0-0.95.
- Acknowledge when multiple mechanisms could produce the same phenotype.
- Output valid JSON conforming to the schema."""

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
                evidence_type=EvidenceType(item["evidence_type"]),
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
                priority=item["priority"],
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
                evidence_type=EvidenceType(et),
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
                evidence_type=EvidenceType(item["evidence_type"]),
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
                priority=item["priority"],
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
You are checking consistency between two independent reasoning paths:
- Forward: mutation → physical evidence → structural mechanisms → functional hypotheses
- Reverse: functional phenotype → candidate structural mechanisms → required evidence

Compare the mechanism types and determine whether the two paths converge,
diverge, or address different aspects.  Output JSON."""

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
