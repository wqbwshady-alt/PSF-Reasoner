"""Internal outputs exchanged by reasoning services."""

from dataclasses import dataclass

from psf_reasoner.schemas.evidence import PhysicalEvidence
from psf_reasoner.schemas.function import FunctionalHypothesis, ReverseCandidate
from psf_reasoner.schemas.mechanisms import StructuralMechanism
from psf_reasoner.schemas.validation import MissingEvidence, ValidationStep


@dataclass(frozen=True, slots=True)
class ForwardResult:
    mechanisms: tuple[StructuralMechanism, ...] = ()
    hypotheses: tuple[FunctionalHypothesis, ...] = ()
    missing_evidence: tuple[MissingEvidence, ...] = ()
    validation_steps: tuple[ValidationStep, ...] = ()


@dataclass(frozen=True, slots=True)
class ReverseResult:
    mechanisms: tuple[StructuralMechanism, ...] = ()
    candidates: tuple[ReverseCandidate, ...] = ()
    required_evidence: tuple[PhysicalEvidence, ...] = ()
    missing_evidence: tuple[MissingEvidence, ...] = ()
    validation_steps: tuple[ValidationStep, ...] = ()
