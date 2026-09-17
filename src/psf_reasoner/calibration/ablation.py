"""Feature ablation study (V3 Pilot Calibrator).

Compares model performance with progressively more features to answer:
Does Structural Context actually improve predictions over mutation chemistry alone?
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psf_reasoner.calibration.build_feature_matrix import FeatureMatrix
from psf_reasoner.calibration.feature_schema import FeatureVector
from psf_reasoner.calibration.train_pilot import (
    evaluate_predictions,
    logistic_regression_predict,
    train_logistic_regression,
)


@dataclass
class AblationResult:
    """Result of one ablation experiment."""

    model_label: str = ""  # "Model 0: Chemistry only", etc.
    feature_group: str = ""  # "chemistry", "physical", "structural", "literature"
    n_features: int = 0
    accuracy: float = 0.0
    mcc: float = 0.0
    feature_names: list[str] = field(default_factory=list)


FEATURE_GROUPS = {
    "Model 0: Mutation chemistry": [
        "volume_delta",
        "polarity_added",
        "polarity_removed",
        "charge_delta",
        "aromatic_added",
        "hbond_donor_gained",
        "hbond_acceptor_gained",
    ],
    "Model 1: Chemistry + Physical Evidence": [
        "volume_delta",
        "polarity_added",
        "polarity_removed",
        "charge_delta",
        "aromatic_added",
        "hbond_donor_gained",
        "hbond_acceptor_gained",
        "contact_count_delta",
        "atoms_lost",
        "atoms_gained",
        "nearest_ligand_distance",
    ],
    "Model 2: Chemistry + Physical + Structural Context": [
        "volume_delta",
        "polarity_added",
        "polarity_removed",
        "charge_delta",
        "aromatic_added",
        "hbond_donor_gained",
        "hbond_acceptor_gained",
        "contact_count_delta",
        "atoms_lost",
        "atoms_gained",
        "nearest_ligand_distance",
        "neighborhood_4a_count",
        "is_catalytic",
        "is_ligand_contact",
        "is_pocket_lining",
        "pocket_catalytic_in_4a",
    ],
    "Model 3: All features + Literature": [],  # use all features
}


def run_ablation(matrix: FeatureMatrix) -> list[AblationResult]:
    """Run feature ablation on the full dataset (no CV split — just train/test on all data).

    This is an exploratory analysis, not a rigorous evaluation.
    For rigorous evaluation, use grouped_cv.
    """
    results: list[AblationResult] = []
    all_names = FeatureVector.feature_names()

    for model_label, feature_names in FEATURE_GROUPS.items():
        if not feature_names:
            feature_names = list(all_names)  # Model 3: all features

        # Create feature mask
        feature_indices = [all_names.index(f) for f in feature_names if f in all_names]

        # Filter train/test data to these features
        train_samples = matrix.samples
        train_labels = matrix.labels
        if not train_samples:
            continue

        try:
            coefs, intercept = _train_with_feature_subset(
                train_samples, train_labels, feature_indices, all_names
            )
            preds = [
                _predict_with_feature_subset(s, coefs, intercept, feature_indices, all_names)
                for s in train_samples
            ]
            result = evaluate_predictions(train_labels, preds, matrix.sample_ids)
            results.append(
                AblationResult(
                    model_label=model_label,
                    n_features=len(feature_indices),
                    accuracy=result.accuracy,
                    mcc=result.mcc,
                    feature_names=feature_names,
                )
            )
        except Exception:
            results.append(
                AblationResult(
                    model_label=model_label,
                    n_features=len(feature_indices),
                )
            )

    return results


def _train_with_feature_subset(
    samples: list[FeatureVector],
    labels: list[float],
    feature_indices: list[int],
    all_names: list[str],
) -> tuple[dict[str, float], float]:
    """Train logistic regression using only a subset of features."""
    # Build a new coefficient dict with only the specified features
    full_coefs, intercept = train_logistic_regression(samples, labels)
    filtered_coefs = {}
    for j, name in enumerate(all_names):
        if j in feature_indices:
            filtered_coefs[name] = full_coefs.get(name, 0.0)
        else:
            filtered_coefs[name] = 0.0  # zero out excluded features
    return filtered_coefs, intercept


def _predict_with_feature_subset(
    sample: FeatureVector,
    coefs: dict[str, float],
    intercept: float,
    feature_indices: list[int],
    all_names: list[str],
) -> float:
    """Predict using only a subset of features."""
    return logistic_regression_predict(sample, coefs, intercept)
