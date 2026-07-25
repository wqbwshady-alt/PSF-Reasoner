"""Simple calibrated baseline model (V3 P4).

A minimal logistic-regression-style model that maps structural features
to a calibrated prediction.  This is the first step away from uncalibrated
heuristics — even a simple model with known coefficients is more
scientifically defensible than +0.06 per evidence match.

For the pilot benchmark, we use predefined coefficients based on
domain knowledge.  These will be replaced by trained coefficients
once sufficient labeled data exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

from psf_reasoner.calibration.feature_schema import FeatureVector


@dataclass
class CalibratedPrediction:
    """Output of the calibrated model for one mutation."""

    sample_id: str
    predicted_probability: float  # calibrated P(resistance) or P(affinity_decrease)
    predicted_direction: str      # "increase", "decrease", "unchanged"
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    is_out_of_distribution: bool = False
    ood_reason: str = ""


class DomainKnowledgeCalibrator:
    """A calibrated model using domain-knowledge coefficients.

    This is NOT a trained model — coefficients are set manually based
    on known structure-activity relationships.  It serves as:
    1. A baseline for comparison with the legacy heuristic
    2. A scaffold that will be replaced by trained coefficients
    3. A demonstration of the calibration pipeline

    The key advantage over the legacy heuristic: coefficients are
    explicit, auditable, and ready to be replaced by trained values.
    """

    # Domain-knowledge coefficients (will be replaced by training)
    # Positive coefficient → increases P(resistance)
    COEFFICIENTS: dict[str, float] = {
        "volume_delta": -0.003,          # volume decrease → slight risk increase
        "polarity_added": 0.10,          # new polarity → more interactions possible
        "polarity_removed": 0.05,
        "charge_delta": 0.15,            # charge change → significant effect
        "aromatic_added": 0.10,
        "hbond_donor_gained": 0.12,      # new H-bond capability
        "hbond_acceptor_gained": 0.08,
        "contact_count_delta": -0.05,     # contact loss → risk
        "atoms_lost": 0.03,
        "atoms_gained": 0.02,
        "nearest_ligand_distance": -0.02, # closer = more impact
        "neighborhood_4a_count": 0.01,
        "is_catalytic": 0.20,            # catalytic site → high impact
        "is_ligand_contact": 0.15,       # direct contact → high impact
        "is_pocket_lining": 0.08,
        "pocket_catalytic_in_4a": 0.10,
        "ligand_heavy_atoms": 0.001,
        "ligand_hbond_donors": 0.01,
        "ligand_hbond_acceptors": 0.01,
        "ligand_charge": 0.02,
        "direct_evidence_count": 0.10,    # literature support → higher confidence
        "strong_evidence_count": 0.05,
        "any_literature": 0.10,
    }

    INTERCEPT: float = -1.0  # baseline log-odds (low resistance probability)

    def predict(self, features: FeatureVector) -> CalibratedPrediction:
        """Compute calibrated prediction from feature vector.

        Uses a logistic regression model: P = sigmoid(bias + Σ w_i * x_i).
        """
        arr = features.to_array()
        names = FeatureVector.feature_names()

        logit = self.INTERCEPT
        for name, value in zip(names, arr):
            coef = self.COEFFICIENTS.get(name, 0.0)
            logit += coef * value

        probability = _sigmoid(logit)
        probability = round(max(0.01, min(0.99, probability)), 3)

        direction = "increased" if probability >= 0.55 else (
            "decreased" if probability <= 0.45 else "unchanged"
        )

        # OOD check: if no features are non-zero, we can't predict
        all_zero = all(v == 0.0 for v in arr)
        ood = all_zero

        return CalibratedPrediction(
            sample_id=features.sample_id,
            predicted_probability=probability,
            predicted_direction=direction,
            confidence_interval_low=None,   # requires bootstrap for CI
            confidence_interval_high=None,
            is_out_of_distribution=ood,
            ood_reason="No structural features available — all feature values are zero" if ood else "",
        )

    def predict_batch(
        self, features_list: list[FeatureVector]
    ) -> list[CalibratedPrediction]:
        """Batch prediction."""
        return [self.predict(f) for f in features_list]

    def get_coefficients(self) -> dict[str, float]:
        """Return model coefficients for auditability."""
        return {
            "intercept": self.INTERCEPT,
            **self.COEFFICIENTS,
        }


def _sigmoid(x: float) -> float:
    """Logistic sigmoid function."""
    if x >= 0:
        return 1.0 / (1.0 + exp(-x))
    return exp(x) / (1.0 + exp(x))
