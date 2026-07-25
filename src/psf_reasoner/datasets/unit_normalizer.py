"""Unit normalization and ΔΔG calculation (V3 data pipeline).

All imported experimental values pass through this module to ensure
consistent units and directions before entering any training set.
"""

from __future__ import annotations

import math

# Gas constant in kcal/(mol·K)
R_KCAL = 0.001987


def normalize_ki_kd_units(value: float, unit: str) -> tuple[float, str]:
    """Convert Ki/Kd values to µM with standardized units.

    Returns (value_in_uM, "uM").
    """
    unit_lower = unit.lower().strip()
    conversions = {
        "mm": 1000.0, "millimolar": 1000.0,
        "µm": 1.0, "um": 1.0, "micromolar": 1.0,
        "nm": 0.001, "nanomolar": 0.001,
        "pm": 1e-6, "picomolar": 1e-6,
        "m": 1_000_000.0, "molar": 1_000_000.0,
    }
    factor = conversions.get(unit_lower, 1.0)
    return round(value * factor, 4), "uM"


def compute_ddg_from_ki_kd(
    wt_value: float,
    mutant_value: float,
    temperature_kelvin: float = 298.15,
) -> float:
    """Compute ΔΔG_binding = RT × ln(K_mutant / K_WT).

    Positive ΔΔG → mutant binds weaker (less favorable).
    Negative ΔΔG → mutant binds stronger (more favorable).

    Values should already be in the same unit before calling.
    """
    if wt_value <= 0 or mutant_value <= 0:
        raise ValueError("Ki/Kd values must be positive")
    rt = R_KCAL * temperature_kelvin
    ratio = mutant_value / wt_value
    return round(rt * math.log(ratio), 3)


def classify_effect_direction(
    ddg: float | None = None,
    ki_ratio: float | None = None,
    threshold_kcal: float = 0.5,
    threshold_ratio: float = 2.0,
) -> str:
    """Classify binding effect direction from ΔΔG or Ki ratio.

    Returns one of: "affinity_decrease", "approximately_neutral", "affinity_increase".
    """
    if ddg is not None:
        if ddg > threshold_kcal:
            return "affinity_decrease"
        if ddg < -threshold_kcal:
            return "affinity_increase"
        return "approximately_neutral"

    if ki_ratio is not None:
        if ki_ratio > threshold_ratio:
            return "affinity_decrease"  # higher Ki = weaker binding
        if ki_ratio < 1.0 / threshold_ratio:
            return "affinity_increase"
        return "approximately_neutral"

    return "unknown"
