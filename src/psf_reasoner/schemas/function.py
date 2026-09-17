"""Functional hypotheses and reverse candidates."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import Claim, Direction, ScientificModel
from psf_reasoner.schemas.mechanisms import MechanismType


class FunctionType(StrEnum):
    LIGAND_AFFINITY = "ligand_affinity"
    CATALYTIC_ACTIVITY = "catalytic_activity"
    PROTEIN_STABILITY = "protein_stability"
    DRUG_RESISTANCE = "drug_resistance"
    LIGAND_SELECTIVITY = "ligand_selectivity"
    ALLOSTERIC_REGULATION = "allosteric_regulation"


class SupportCoverage(ScientificModel):
    """Structured evidence coverage for functional hypotheses (V2 Phase 4A)."""

    current_evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_labels: tuple[str, ...] = ()  # human-readable names for current
    missing_labels: tuple[str, ...] = ()  # human-readable names for missing


class FunctionalHypothesis(Claim):
    function_type: FunctionType
    direction: Direction
    phenotype: str | None = None
    support_coverage: SupportCoverage | None = None


class ReverseCandidate(Claim):
    mechanism_type: MechanismType
    expected_evidence: tuple[str, ...]
    rank: int
