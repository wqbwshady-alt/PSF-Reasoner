"""Small curated HIV-1 protease calibration evidence."""

from __future__ import annotations

from psf_reasoner.identifiers import make_id
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType, Measurement, PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest


class HIVProteaseCalibrationProvider:
    """Emit curated benchmark labels for supported HIV-1 protease cases."""

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if request.mutation is None:
            return ()
        if request.mutation.notation != "V82A" or request.ligand.identifier.upper() != "MK1":
            return ()
        return (
            PhysicalEvidence(
                id=make_id("evidence", "calibration", "hiv1_protease", "v82a", "mk1"),
                title="HIV-1 protease V82A indinavir-site calibration label",
                description=(
                    "Curated benchmark label: the V82A HIV-1 protease mutant is treated as an "
                    "inhibitor-binding-site resistance case for MK1/indinavir-like pocket analysis. "
                    "Literature: 3.3-fold Ki increase (Mahalingam et al. 2004, abstract)."
                ),
                evidence_type=EvidenceType.EXPERIMENTAL_CALIBRATION,
                status=EvidenceStatus.OBSERVED,
                entities=("HIV-1 protease", "V82A", "MK1"),
                measurement=Measurement(
                    name="qualitative_resistance_affinity_label",
                    value=1.0,
                    unit="directional_label",
                    direction=Direction.INCREASE,
                ),
                confidence=0.70,
                provenance=(
                    Provenance(
                        kind=ProvenanceKind.LITERATURE,
                        source="Mahalingam et al. Eur J Biochem 271:1516-1524 (2004)",
                        method="curated qualitative label from primary structure paper",
                        parameters={"doi": "10.1111/j.1432-1033.2004.04060.x", "pubmed": 15066177},
                    ),
                    Provenance(
                        kind=ProvenanceKind.STRUCTURE,
                        source="RCSB PDB 1SDT and 1SDV",
                        method="paired MK1-bound HIV protease WT/V82A crystallographic benchmark",
                        parameters={"1SDT_resolution_angstrom": 1.3, "1SDV_resolution_angstrom": 1.4},
                    ),
                ),
                limitations=(
                    "This calibration label is qualitative; it is not a numeric Ki, Kd, or IC50 value.",
                    "The structural pair can include crystallographic and background-mutation effects.",
                ),
            ),
        )
