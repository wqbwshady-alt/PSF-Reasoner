"""Cutoff Sensitivity Analysis (V2 Phase 2A).

The sweep rebinds the cutoffs on :mod:`.constants` (restoring them in a
``finally`` block) instead of on module-level globals, because that is where
:mod:`.analysis` and :mod:`.contacts` read them from.  Values and behaviour
are unchanged.
"""

from __future__ import annotations

from psf_reasoner.physical.interactions import constants
from psf_reasoner.physical.interactions.analysis import analyze_typed_interactions
from psf_reasoner.physical.structure import ResidueRecord


def _classify_stability(counts: tuple[int, ...]) -> str:
    """Classify a cutoff-count series as robust / threshold-sensitive / unstable."""
    if len(counts) < 2:
        return "robust"
    max_val = max(counts)
    min_val = min(counts)
    if max_val == 0 and min_val == 0:
        return "robust"
    spread = (max_val - min_val) / max(1, max_val)
    # Count how many transitions (sign changes) there are
    transitions = sum(1 for i in range(len(counts) - 1) if counts[i] != counts[i + 1])
    if transitions == 0:
        return "robust"
    if spread < 0.25:
        return "robust"
    if transitions <= 2 and spread < 0.5:
        return "threshold_sensitive"
    return "unstable"


def cutoff_sensitivity_analysis(
    residue: ResidueRecord,
    ligand: ResidueRecord,
    waters: tuple[ResidueRecord, ...],
    *,
    hbond_cutoffs: tuple[float, ...] = (3.0, 3.5, 4.0, 4.5, 5.0),
    hydrophobic_cutoffs: tuple[float, ...] = (3.5, 4.0, 4.5, 5.0),
    salt_bridge_cutoffs: tuple[float, ...] = (4.0, 4.5, 5.0, 5.5, 6.0),
    pi_cutoffs: tuple[float, ...] = (4.5, 5.0, 5.5, 6.0),
) -> dict[str, tuple[tuple[float, ...], tuple[int, ...]]]:
    """Sweep cutoff parameters and return per-class (cutoff_values, counts) pairs.

    Returns a dict keyed by interaction class name, each value a pair of
    ``(cutoff_values, count_per_cutoff)`` suitable for constructing
    ``CutoffSensitivityReport``.
    """
    original_hbond = constants.HYDROGEN_BOND_CUTOFF_ANGSTROM
    original_hydrophobic = constants.HYDROPHOBIC_CUTOFF_ANGSTROM
    original_salt = constants.SALT_BRIDGE_CUTOFF_ANGSTROM
    original_pi = constants.PI_CENTROID_CUTOFF_ANGSTROM

    hbond_counts: list[int] = []
    hydrophobic_counts: list[int] = []
    salt_counts: list[int] = []
    pi_counts: list[int] = []

    try:
        for cutoff in hbond_cutoffs:
            constants.HYDROGEN_BOND_CUTOFF_ANGSTROM = cutoff
            # Re-run analysis for this residue-ligand pair
            result = analyze_typed_interactions(residue, ligand, waters)
            hbond_counts.append(sum(item.interaction_type == "hydrogen_bond" for item in result.interactions))

        for cutoff in hydrophobic_cutoffs:
            constants.HYDROPHOBIC_CUTOFF_ANGSTROM = cutoff
            result = analyze_typed_interactions(residue, ligand, waters)
            hydrophobic_counts.append(
                sum(item.interaction_type == "hydrophobic_contact" for item in result.interactions)
            )

        for cutoff in salt_bridge_cutoffs:
            constants.SALT_BRIDGE_CUTOFF_ANGSTROM = cutoff
            result = analyze_typed_interactions(residue, ligand, waters)
            salt_counts.append(sum(item.interaction_type == "salt_bridge" for item in result.interactions))

        for cutoff in pi_cutoffs:
            constants.PI_CENTROID_CUTOFF_ANGSTROM = cutoff
            result = analyze_typed_interactions(residue, ligand, waters)
            pi_counts.append(sum(item.interaction_type == "pi_interaction" for item in result.interactions))
    finally:
        constants.HYDROGEN_BOND_CUTOFF_ANGSTROM = original_hbond
        constants.HYDROPHOBIC_CUTOFF_ANGSTROM = original_hydrophobic
        constants.SALT_BRIDGE_CUTOFF_ANGSTROM = original_salt
        constants.PI_CENTROID_CUTOFF_ANGSTROM = original_pi

    return {
        "hydrogen_bond": (hbond_cutoffs, tuple(hbond_counts)),
        "hydrophobic_contact": (hydrophobic_cutoffs, tuple(hydrophobic_counts)),
        "salt_bridge": (salt_bridge_cutoffs, tuple(salt_counts)),
        "pi_interaction": (pi_cutoffs, tuple(pi_counts)),
    }
