"""Evidence ranking and grading system (V3 P2).

Grades literature evidence by applicability, experimental method quality,
and measurement precision.  Each piece of evidence receives a composite
grade that determines its weight in the reasoning engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from psf_reasoner.knowledge.entity_normalizer import EvidenceApplicability


class EvidenceGrade(IntEnum):
    """Composite evidence quality grade (1 = highest, 5 = lowest)."""

    GRADE_1_DIRECT = 1    # exact match, quantitative, curated
    GRADE_2_STRONG = 2    # same site, quantitative, reported
    GRADE_3_MODERATE = 3  # same protein, mechanistic, qualitative or inferred
    GRADE_4_WEAK = 4      # family analogy or general principle
    GRADE_5_IRRELEVANT = 5  # too distant to be useful


class MeasurementType(IntEnum):
    """Experimental measurement reliability (lower = more reliable)."""

    CURATED_DDG = 1           # manually curated ΔΔG from dedicated database
    REPORTED_KI_KD = 2        # published Ki/Kd/IC50
    STRUCTURAL_INFERENCE = 3  # structural observation (e.g. "contact lost")
    COMPUTATIONAL_PREDICTION = 4  # MD, docking, or other in silico
    QUALITATIVE_OBSERVATION = 5   # "confers resistance" without quantitative data


@dataclass
class LiteratureEvidence:
    """One piece of structured evidence extracted from the literature."""

    # Identity
    evidence_id: str
    applicability: EvidenceApplicability

    # Source
    pmid: str = ""
    doi: str = ""

    # What was measured
    measurement_type: MeasurementType = MeasurementType.QUALITATIVE_OBSERVATION
    measured_value: float | None = None
    measured_unit: str = ""
    measured_direction: str = ""  # "increased", "decreased", "unchanged"

    # What the evidence says
    original_conclusion: str = ""
    structured_claim: str = ""  # normalized claim, e.g. "V82A reduces MK1 binding affinity"

    # Experimental context
    experimental_system: str = ""  # "in vitro purified enzyme", "cell-based assay", etc.
    ph: float | None = None
    temperature_c: float | None = None

    # Quality flags
    sample_size: int | None = None
    has_control: bool = True
    is_peer_reviewed: bool = True
    notes: str = ""

    def compute_grade(self) -> EvidenceGrade:
        """Compute composite evidence grade from applicability + measurement quality."""
        applicability_score = _applicability_score(self.applicability)
        measurement_score = int(self.measurement_type)

        # Weighted combination: applicability matters more than measurement precision
        composite = applicability_score * 0.6 + measurement_score * 0.4

        if composite <= 1.5:
            return EvidenceGrade.GRADE_1_DIRECT
        if composite <= 2.5:
            return EvidenceGrade.GRADE_2_STRONG
        if composite <= 3.5:
            return EvidenceGrade.GRADE_3_MODERATE
        if composite <= 4.5:
            return EvidenceGrade.GRADE_4_WEAK
        return EvidenceGrade.GRADE_5_IRRELEVANT


def _applicability_score(app: EvidenceApplicability) -> float:
    """Map applicability to numeric score (lower = more applicable)."""
    return {
        EvidenceApplicability.EXACT_MATCH: 1.0,
        EvidenceApplicability.SAME_SITE_SAME_PROTEIN: 2.0,
        EvidenceApplicability.SAME_SITE_HOMOLOG: 2.5,
        EvidenceApplicability.NEARBY_SITE: 3.0,
        EvidenceApplicability.SAME_PROTEIN_MECHANISM: 3.5,
        EvidenceApplicability.FAMILY_ANALOGY: 4.0,
        EvidenceApplicability.GENERAL_BIOCHEMICAL: 5.0,
    }.get(app, 5.0)
