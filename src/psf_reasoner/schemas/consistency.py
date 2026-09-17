"""Forward/reverse consistency contracts (V2 Phase 4B)."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import Claim, ScientificModel


class ConsistencyStatus(StrEnum):
    CONSISTENT = "consistent"
    CONFLICT = "conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class AgreementDetail(ScientificModel):
    """Breakdown of pathway agreement into physical, functional, phenotype dimensions."""

    physical_agreement: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Evidence-level agreement between forward and reverse"
    )
    functional_agreement: float = Field(default=0.0, ge=0.0, le=1.0, description="Hypothesis-level agreement")
    phenotype_agreement: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Phenotype-to-mechanism alignment"
    )


class ConsistencyCheck(Claim):
    status: ConsistencyStatus
    compared_claims: tuple[str, ...] = ()
    agreement_detail: AgreementDetail | None = None
