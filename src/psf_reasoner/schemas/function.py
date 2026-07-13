"""Functional hypotheses and reverse candidates."""

from enum import StrEnum

from psf_reasoner.schemas.common import Claim, Direction
from psf_reasoner.schemas.mechanisms import MechanismType


class FunctionType(StrEnum):
    LIGAND_AFFINITY = "ligand_affinity"
    CATALYTIC_ACTIVITY = "catalytic_activity"
    PROTEIN_STABILITY = "protein_stability"
    DRUG_RESISTANCE = "drug_resistance"
    LIGAND_SELECTIVITY = "ligand_selectivity"
    ALLOSTERIC_REGULATION = "allosteric_regulation"


class FunctionalHypothesis(Claim):
    function_type: FunctionType
    direction: Direction
    phenotype: str | None = None


class ReverseCandidate(Claim):
    mechanism_type: MechanismType
    expected_evidence: tuple[str, ...]
    rank: int
