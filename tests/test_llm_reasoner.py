"""Tests for LLM reasoning engines — use a deterministic mock provider."""

from __future__ import annotations

import pytest

from psf_reasoner.reasoning.llm_reasoner import (
    LLMConsistencyChecker,
    LLMForwardReasoner,
    LLMReverseReasoner,
)
from psf_reasoner.reasoning.ports import LLMCompletion, LLMUsage
from psf_reasoner.schemas.consistency import ConsistencyStatus
from psf_reasoner.schemas.evidence import EvidenceType
from psf_reasoner.schemas.function import FunctionType
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.mechanisms import MechanismType

# ---------------------------------------------------------------------------
# Mock LLM provider — returns pre-canned structured responses
# ---------------------------------------------------------------------------


class _MockProvider:
    def __init__(self, canned: dict | None = None) -> None:
        self._canned = canned or _default_forward_output()
        self.calls: list[dict] = []

    def complete(self, system_prompt: str, user_prompt: str, output_schema: dict, **kwargs) -> LLMCompletion:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "output_schema_keys": tuple(output_schema.get("properties", {}).keys()),
            }
        )
        return LLMCompletion(
            content=self._canned,
            model="mock-model",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            finish_reason="stop",
        )


def _default_forward_output() -> dict:
    return {
        "mechanisms": [
            {
                "title": "V82A 导致口袋堆积减弱",
                "description": "V82A 截断减少了侧链体积，削弱了与 MK1 的疏水接触。",
                "mechanism_type": "pocket_packing",
                "direction": "decrease",
                "affected_region": "V82-MK1 接触壳层",
                "confidence": 0.72,
                "evidence_ids": ["evidence-dummy-001"],
                "limitations": ["未采样构象系综效应。"],
            },
            {
                "title": "配体锚定保持稳定",
                "description": "MK1 与催化天冬氨酸之间的关键氢键未受 V82A 影响。",
                "mechanism_type": "ligand_anchoring",
                "direction": "unchanged",
                "affected_region": "催化位点",
                "confidence": 0.68,
                "evidence_ids": ["evidence-dummy-002"],
                "limitations": ["氢原子位置为推断值。"],
            },
        ],
        "hypotheses": [
            {
                "title": "MK1 亲和力中度下降",
                "description": "疏水堆积丧失而无极性接触补偿，提示结合减弱。",
                "function_type": "ligand_affinity",
                "direction": "decrease",
                "confidence": 0.58,
                "mechanism_ids": ["mechanism-placeholder-001"],
                "limitations": ["熵补偿效应未知。"],
            },
        ],
        "missing_evidence": [
            {
                "evidence_type": "energy_component",
                "reason": "无可用的结合自由能计算。",
                "impact": "无法量化亲和力变化。",
            },
        ],
        "validation_steps": [
            {
                "priority": 1,
                "kind": "binding_assay",
                "objective": "测量 WT 与 V82A 的 MK1 结合亲和力。",
                "method": "在匹配条件下进行 ITC 或 SPR 实验。",
                "expected_result": "如果堆积假设正确，V82A 应显示中等程度的亲和力降低。",
            },
        ],
    }


def _default_reverse_output() -> dict:
    return {
        "candidates": [
            {
                "title": "口袋堆积破坏",
                "description": "结合口袋中 V82A 可能削弱抑制剂接触。",
                "mechanism_type": "pocket_packing",
                "expected_evidence_types": ["residue_contact", "pocket_geometry", "energy_component"],
                "rank": 1,
                "confidence": 0.65,
                "limitations": ["其他耐药机制未被排除。"],
            },
        ],
        "required_evidence_types": ["residue_contact", "pocket_geometry", "energy_component"],
        "missing_evidence": [
            {
                "evidence_type": "energy_component",
                "reason": "结合能量未计算。",
                "impact": "无法确认耐药机制。",
            },
        ],
        "validation_steps": [
            {
                "priority": 1,
                "kind": "mutant_modelling",
                "objective": "比较 WT 和突变体接触图谱。",
                "method": "MD 弛豫 + 接触分析。",
                "expected_result": "接触改变将支持堆积机制。",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def forward_request() -> AnalysisRequest:
    from psf_reasoner.schemas.inputs import LigandSpec, MutationSpec, StructureInput

    return AnalysisRequest(
        structure=StructureInput(path="/tmp/test.pdb"),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )


@pytest.fixture
def reverse_request() -> AnalysisRequest:
    from psf_reasoner.schemas.inputs import LigandSpec, PhenotypeSpec, StructureInput

    return AnalysisRequest(
        structure=StructureInput(path="/tmp/test.pdb"),
        ligand=LigandSpec(identifier="MK1"),
        phenotype=PhenotypeSpec(name="drug_resistance"),
    )


# ---------------------------------------------------------------------------
# Forward reasoning
# ---------------------------------------------------------------------------


class TestLLMForwardReasoner:
    def test_generates_mechanisms_from_evidence(self, forward_request: AnalysisRequest) -> None:
        reasoner = LLMForwardReasoner(_MockProvider())
        result = reasoner.reason(forward_request, ())

        assert len(result.mechanisms) == 2
        assert result.mechanisms[0].mechanism_type == MechanismType.POCKET_PACKING
        assert result.mechanisms[0].confidence <= 0.95
        assert "V82A" in result.mechanisms[0].title
        assert result.mechanisms[0].provenance  # LLM provenance must be present

    def test_generates_functional_hypotheses(self, forward_request: AnalysisRequest) -> None:
        reasoner = LLMForwardReasoner(_MockProvider())
        result = reasoner.reason(forward_request, ())

        assert len(result.hypotheses) == 1
        assert result.hypotheses[0].function_type == FunctionType.LIGAND_AFFINITY
        assert result.hypotheses[0].direction.value == "decrease"

    def test_generates_missing_evidence(self, forward_request: AnalysisRequest) -> None:
        reasoner = LLMForwardReasoner(_MockProvider())
        result = reasoner.reason(forward_request, ())

        assert len(result.missing_evidence) == 1
        assert result.missing_evidence[0].evidence_type == EvidenceType.ENERGY_COMPONENT

    def test_generates_validation_steps(self, forward_request: AnalysisRequest) -> None:
        reasoner = LLMForwardReasoner(_MockProvider())
        result = reasoner.reason(forward_request, ())

        assert len(result.validation_steps) == 1
        assert result.validation_steps[0].priority == 1

    def test_all_ids_are_stable_and_traceable(self, forward_request: AnalysisRequest) -> None:
        reasoner = LLMForwardReasoner(_MockProvider())
        result = reasoner.reason(forward_request, ())

        mechanism_ids = {m.id for m in result.mechanisms}
        for h in result.hypotheses:
            assert all(mid.startswith("mechanism-") for mid in h.supports)

        claim_ids = mechanism_ids | {h.id for h in result.hypotheses}
        for m in result.missing_evidence:
            assert set(m.related_claims).issubset(claim_ids)

    def test_no_mutation_returns_empty(self) -> None:
        from psf_reasoner.schemas.inputs import LigandSpec, PhenotypeSpec, StructureInput

        request = AnalysisRequest(
            structure=StructureInput(path="/tmp/test.pdb"),
            ligand=LigandSpec(identifier="MK1"),
            phenotype=PhenotypeSpec(name="drug_resistance"),
        )
        reasoner = LLMForwardReasoner(_MockProvider())
        result = reasoner.reason(request, ())

        assert not result.mechanisms
        assert not result.hypotheses


# ---------------------------------------------------------------------------
# Reverse reasoning
# ---------------------------------------------------------------------------


class TestLLMReverseReasoner:
    def test_generates_candidates_from_phenotype(self, reverse_request: AnalysisRequest) -> None:
        reasoner = LLMReverseReasoner(_MockProvider(_default_reverse_output()))
        result = reasoner.reason(reverse_request, ())

        assert len(result.candidates) == 1
        assert result.candidates[0].mechanism_type == MechanismType.POCKET_PACKING
        assert result.candidates[0].rank == 1
        assert result.candidates[0].expected_evidence  # must predict what to look for

    def test_generates_required_evidence(self, reverse_request: AnalysisRequest) -> None:
        reasoner = LLMReverseReasoner(_MockProvider(_default_reverse_output()))
        result = reasoner.reason(reverse_request, ())

        assert len(result.required_evidence) == 3
        assert all(e.status.value == "required" for e in result.required_evidence)

    def test_no_phenotype_returns_empty(self) -> None:
        from psf_reasoner.schemas.inputs import LigandSpec, MutationSpec, StructureInput

        request = AnalysisRequest(
            structure=StructureInput(path="/tmp/test.pdb"),
            ligand=LigandSpec(identifier="MK1"),
            mutation=MutationSpec(notation="V82A", chain="A"),
        )
        reasoner = LLMReverseReasoner(_MockProvider())
        result = reasoner.reason(request, ())

        assert not result.candidates


# ---------------------------------------------------------------------------
# Consistency checking
# ---------------------------------------------------------------------------


class TestLLMConsistencyChecker:
    def test_detects_convergence_of_forward_and_reverse(
        self, forward_request: AnalysisRequest, reverse_request: AnalysisRequest
    ) -> None:
        fwd = LLMForwardReasoner(_MockProvider()).reason(forward_request, ())
        rev = LLMReverseReasoner(_MockProvider(_default_reverse_output())).reason(reverse_request, ())

        canned = {
            "status": "consistent",
            "title": "Forward and reverse converge on pocket packing",
            "description": "Both paths independently nominate pocket packing as the primary mechanism.",
            "confidence": 0.65,
            "shared_mechanism_types": ["pocket_packing"],
        }
        checker = LLMConsistencyChecker(_MockProvider(canned))
        checks = checker.check(fwd, rev, ())

        assert len(checks) >= 1
        assert checks[0].status == ConsistencyStatus.CONSISTENT

    def test_empty_results_return_insufficient(self) -> None:
        from psf_reasoner.reasoning.results import ForwardResult, ReverseResult

        checker = LLMConsistencyChecker(_MockProvider())
        checks = checker.check(ForwardResult(), ReverseResult(), ())

        assert len(checks) == 1
        assert checks[0].status == ConsistencyStatus.INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# Evidence interpreter
# ---------------------------------------------------------------------------


class TestEvidenceInterpreter:
    def test_formats_computed_evidence(self) -> None:
        from psf_reasoner.reasoning.evidence_interpreter import format_evidence_for_llm
        from psf_reasoner.schemas.common import Direction
        from psf_reasoner.schemas.evidence import (
            EvidenceStatus,
            EvidenceType,
            Measurement,
            PhysicalEvidence,
        )
        from psf_reasoner.schemas.inputs import LigandSpec, MutationSpec, StructureInput

        request = AnalysisRequest(
            structure=StructureInput(path="/tmp/test.pdb"),
            ligand=LigandSpec(identifier="MK1"),
            mutation=MutationSpec(notation="V82A", chain="A"),
        )
        evidence = (
            PhysicalEvidence(
                id="evidence-abc123456789",
                title="Nearest heavy-atom distance",
                description="Distance from V82 CG1 to MK1 C1.",
                evidence_type=EvidenceType.ATOMIC_DISTANCE,
                status=EvidenceStatus.COMPUTED,
                measurement=Measurement(
                    name="nearest_heavy_atom_distance",
                    value=3.635,
                    unit="angstrom",
                    direction=Direction.CHANGE,
                ),
                confidence=0.95,
            ),
        )

        text = format_evidence_for_llm(request, evidence)

        assert "MK1" in text
        assert "V82A" in text
        assert "3.635" in text
        assert "angstrom" in text
        assert "COMPUTED" in text.upper() or "computed" in text
