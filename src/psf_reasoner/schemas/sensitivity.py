"""Cutoff sensitivity analysis contracts (V2 Phase 2A)."""

from enum import StrEnum

from pydantic import Field

from psf_reasoner.schemas.common import ScientificModel


class SensitivityStability(StrEnum):
    ROBUST = "robust"
    THRESHOLD_SENSITIVE = "threshold_sensitive"
    UNSTABLE = "unstable"


class CutoffSensitivityReport(ScientificModel):
    """Per-interaction-class sensitivity across a sweep of distance cutoffs."""

    interaction_class: str = Field(min_length=1, description="e.g. hydrogen_bond, hydrophobic_contact")
    cutoff_values: tuple[float, ...] = ()
    count_per_cutoff: tuple[int, ...] = ()
    stability: SensitivityStability = SensitivityStability.ROBUST
    reference_cutoff: float = Field(ge=0.0, description="Canonical cutoff used in main analysis")


class GlobalSensitivityReport(ScientificModel):
    """Aggregate cutoff sensitivity across all interaction classes."""

    reports: tuple[CutoffSensitivityReport, ...] = ()
    overall_stability: SensitivityStability = SensitivityStability.ROBUST
