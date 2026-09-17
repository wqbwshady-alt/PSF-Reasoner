"""Cutoff thresholds used by the atom-typed interaction classifiers.

The four distance cutoffs are deliberately read *through this module object*
(``constants.HYDROGEN_BOND_CUTOFF_ANGSTROM``) rather than imported by value:
:func:`psf_reasoner.physical.interactions.sensitivity.cutoff_sensitivity_analysis`
rebinds them while it sweeps, which is how the historical single-module
implementation behaved with its module-level globals.
"""

HYDROGEN_BOND_CUTOFF_ANGSTROM = 3.5
HYDROPHOBIC_CUTOFF_ANGSTROM = 4.0
SALT_BRIDGE_CUTOFF_ANGSTROM = 5.5  # aligned with PLIP (was 4.0)
PI_CENTROID_CUTOFF_ANGSTROM = 5.5
HYDROGEN_BOND_MIN_ANGLE_DEGREES = 100.0  # aligned with PLIP (was 110.0)
