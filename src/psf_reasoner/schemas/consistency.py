"""Forward/reverse consistency contracts."""

from enum import StrEnum

from psf_reasoner.schemas.common import Claim


class ConsistencyStatus(StrEnum):
    CONSISTENT = "consistent"
    CONFLICT = "conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ConsistencyCheck(Claim):
    status: ConsistencyStatus
    compared_claims: tuple[str, ...] = ()
