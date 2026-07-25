"""External experimental data import schema (V3 P5a).

Defines the unified schema for importing user-provided experimental
results (ΔΔG, Ki, Kd, IC50, etc.) and external tool outputs (FoldX,
Rosetta, MM/GBSA) into the PSF-Reasoner evidence system.

All imported data is tagged with provenance and normalized to standard
units and directions before integration into the Evidence Graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DataSource(StrEnum):
    """Origin of the imported data."""

    EXPERIMENTAL = "experimental"
    COMPUTATIONAL = "computational"
    LITERATURE = "literature"
    USER_PROVIDED = "user_provided"


class MeasurementKind(StrEnum):
    """Standardised measurement types."""

    DDG_BINDING = "ddG_binding"           # ΔΔG (kcal/mol)
    DDG_STABILITY = "ddG_stability"       # ΔΔG stability (kcal/mol)
    KI = "Ki"                              # inhibition constant
    KD = "Kd"                              # dissociation constant
    IC50 = "IC50"                          # half-maximal inhibitory concentration
    EC50 = "EC50"                          # half-maximal effective concentration
    RESISTANCE_FOLD = "resistance_fold"    # fold change in IC50/MIC
    CATALYTIC_ACTIVITY = "catalytic_activity"  # kcat or kcat/Km
    MMGBSA = "mmgbsa"                      # MM/GBSA binding energy
    FOLDX_DDG = "foldx_ddg"               # FoldX ΔΔG
    ROSETTA_DDG = "rosetta_ddg"           # Rosetta ΔΔG
    FEP_DDG = "fep_ddg"                   # FEP/TI ΔΔG


@dataclass
class ExternalMeasurement:
    """One user-provided or literature-derived experimental measurement."""

    # Identity
    measurement_id: str
    kind: MeasurementKind
    source: DataSource

    # Value
    value: float
    unit: str
    direction: str = ""  # "increased", "decreased", "unchanged"
    uncertainty: float | None = None  # ± standard error
    reference_value: float | None = None  # WT value for fold-change context

    # Experimental context
    experimental_system: str = ""  # "in vitro purified", "cell-based", etc.
    ph: float | None = None
    temperature_c: float | None = None

    # Tool context (for computational results)
    tool_name: str = ""
    tool_version: str = ""
    method: str = ""
    parameters: dict = field(default_factory=dict)
    input_structure: str = ""

    # Provenance
    pmid: str = ""
    doi: str = ""
    provenance_notes: str = ""

    def normalize_direction(self) -> str:
        """Normalize direction to standard PSF terms."""
        if self.direction in ("increased", "decreased", "unchanged"):
            return self.direction
        # Auto-detect from sign
        if self.kind in (MeasurementKind.DDG_BINDING, MeasurementKind.DDG_STABILITY,
                         MeasurementKind.MMGBSA, MeasurementKind.FOLDX_DDG,
                         MeasurementKind.ROSETTA_DDG, MeasurementKind.FEP_DDG):
            return "decreased" if self.value > 0 else "increased"
        if self.kind in (MeasurementKind.KI, MeasurementKind.KD,
                         MeasurementKind.IC50, MeasurementKind.RESISTANCE_FOLD):
            return "increased" if self.value > 1.0 else "decreased"
        return "unchanged"


def compute_evidence_polarity(
    measurement: ExternalMeasurement,
    mechanism_direction: str,
) -> str:
    """Determine if a measurement supports, conflicts with, or is neutral
    to a proposed mechanism direction.

    - mechanism_direction: e.g. "affinity_decrease", "resistance_increase"
    - Returns: "supporting", "conflicting", "neutral"
    """
    m = measurement
    if mechanism_direction == "affinity_decrease":
        if m.kind in (MeasurementKind.DDG_BINDING, MeasurementKind.MMGBSA,
                       MeasurementKind.FOLDX_DDG, MeasurementKind.ROSETTA_DDG):
            return "supporting" if m.value > 0 else "conflicting"
        if m.kind in (MeasurementKind.KI, MeasurementKind.KD):
            return "supporting" if m.value > 1.0 else "conflicting"
    if mechanism_direction == "affinity_increase":
        if m.kind in (MeasurementKind.DDG_BINDING, MeasurementKind.MMGBSA):
            return "supporting" if m.value < 0 else "conflicting"
    if mechanism_direction == "resistance_increase":
        if m.kind == MeasurementKind.RESISTANCE_FOLD:
            return "supporting" if m.value > 1.0 else "conflicting"
        if m.kind in (MeasurementKind.KI, MeasurementKind.IC50):
            return "supporting" if m.value > 1.0 else "conflicting"
    return "neutral"
