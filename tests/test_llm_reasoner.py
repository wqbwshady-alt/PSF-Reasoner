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
                "title": "Pocket packing loss at V82A",
                "description": (
                    "V82A truncation reduces side-chain volume, weakening hydrophobic contacts with MK1."
                ),
                "mechanism_type": "pocket_packing",
                "direction": "decrease",
                "affected_region": "V82-MK1 contact shell",
                "confidence": 0.72,
                "evidence_ids": ["evidence-dummy-001"],
                "limitations": ["Ensemble effects not sampled."],
            },
            {
                "title": "Ligand anchoring maintained",
                "description": ("Key H-bonds between MK1 and catalytic aspartates are unaffected by V82A."),
                "mechanism_type": "ligand_anchoring",
                "direction": "unchanged",
                "affected_region": "catalytic site",
                "confidence": 0.68,
                "evidence_ids": ["evidence-dummy-002"],
                "limitations": ["Hydrogen positions are inferred."],
            },
        ],
        "hypotheses": [
            {
                "title": "Moderate MK1 affinity decrease",
                "description": (
                    "Loss of hydrophobic packing without compensatory polar contacts suggests weaker binding."
                ),
                "function_type": "ligand_affinity",
                "direction": "decrease",
                "confidence": 0.58,
                "mechanism_ids": ["mechanism-placeholder-001"],
                "limitations": ["Entropic compensation unknown."],
            },
        ],
        "missing_evidence": [
            {
                "evidence_type": "energy_component",
                "reason": "No binding free energy calculation available.",
                "impact": "Cannot quantify affinity change.",
            },
        ],
        "validation_steps": [
            {
                "priority": 1,
                "kind": "binding_assay",
                "objective": "Measure WT vs V82A MK1 binding affinity.",
                "method": "ITC or SPR under matched conditions.",
                "expected_result": (
                    "V82A should show moderately reduced affinity if packing hypothesis is correct."
                ),
            },
        ],
    }


def _default_reverse_output() -> dict:
    return {
        "candidates": [
            {
                "title": "Pocket packing disruption",
                "description": "V82A in the binding pocket could weaken inhibitor contacts.",
                "mechanism_type": "pocket_packing",
                "expected_evidence_types": ["residue_contact", "pocket_geometry", "energy_component"],
                "rank": 1,
                "confidence": 0.65,
                "limitations": ["Other resistance mechanisms not ruled out."],
            },
        ],
        "required_evidence_types": ["residue_contact", "pocket_geometry", "energy_component"],
        "missing_evidence": [
            {
                "evidence_type": "energy_component",
                "reason": "Binding energetics not computed.",
                "impact": "Cannot confirm resistance mechanism.",
            },
        ],
        "validation_steps": [
            {
                "priority": 1,
                "kind": "mutant_modelling",
                "objective": "Compare WT and mutant contact maps.",
                "method": "MD relaxation + contact analysis.",
                "expected_result": "Altered contacts would support packing mechanism.",
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
        assert result.mechanisms[0].title == "Pocket packing loss at V82A"
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
