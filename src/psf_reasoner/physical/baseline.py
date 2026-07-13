"""Coordinate-free evidence derived from declared mutation properties."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    Measurement,
    PhysicalEvidence,
)
from psf_reasoner.schemas.inputs import AnalysisRequest

# Coarse side-chain size classes are intentionally qualitative at this stage.
SIDE_CHAIN_SIZE = {
    "G": 0,
    "A": 1,
    "S": 1,
    "C": 1,
    "P": 2,
    "T": 2,
    "D": 2,
    "N": 2,
    "V": 3,
    "E": 3,
    "Q": 3,
    "I": 4,
    "L": 4,
    "M": 4,
    "H": 4,
    "K": 4,
    "F": 5,
    "R": 5,
    "Y": 5,
    "W": 6,
}


class MutationPropertyEvidenceProvider:
    """Emit auditable priors without pretending coordinates were analysed."""

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        mutation = request.mutation
        if mutation is None:
            return ()

        old_size = SIDE_CHAIN_SIZE[mutation.wild_type]
        new_size = SIDE_CHAIN_SIZE[mutation.mutant]
        delta = new_size - old_size
        direction = (
            Direction.DECREASE if delta < 0 else Direction.INCREASE if delta > 0 else Direction.UNCHANGED
        )
        evidence_id = make_id(
            "evidence",
            "residue_property_change",
            mutation.notation,
            mutation.chain,
        )
        return (
            PhysicalEvidence(
                id=evidence_id,
                title=f"Side-chain size change for {mutation.notation}",
                description=(
                    f"The declared substitution changes the qualitative side-chain size "
                    f"class from {old_size} to {new_size}."
                ),
                evidence_type=EvidenceType.RESIDUE_PROPERTY_CHANGE,
                status=EvidenceStatus.INFERRED,
                entities=(mutation.notation, request.ligand.identifier),
                measurement=Measurement(
                    name="side_chain_size_class_delta",
                    value=float(delta),
                    unit="ordinal_class",
                    direction=direction,
                    reference_value=float(old_size),
                ),
                confidence=0.85,
                provenance=(
                    Provenance(
                        kind=ProvenanceKind.BUILTIN_PRIOR,
                        source="PSF qualitative amino-acid property table v1",
                        method="ordinal side-chain size comparison",
                    ),
                    Provenance(
                        kind=ProvenanceKind.INPUT,
                        source="analysis request mutation",
                    ),
                ),
                limitations=(
                    "This is a residue-property prior, not a coordinate-derived contact measurement.",
                    "Local conformation can amplify, compensate for, or reverse its structural effect.",
                ),
            ),
        )
