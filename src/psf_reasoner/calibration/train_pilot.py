"""Pilot model training (V3 Pilot Calibrator).

Trains the simplest possible models on the golden 30 cases.
Goal: verify the data→features→model→evaluate loop, not achieve high accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, sqrt

from psf_reasoner.calibration.feature_schema import FeatureVector


@dataclass
class PilotResult:
    """Results for one pilot model."""

    model_name: str = ""
    n_train: int = 0
    n_test: int = 0
    test_split_groups: list[str] = field(default_factory=list)

    # Classification
    accuracy: float = 0.0
    balanced_accuracy: float = 0.0
    mcc: float = 0.0

    # Predictions
    y_true: list[float] = field(default_factory=list)
    y_pred: list[float] = field(default_factory=list)
    sample_ids: list[str] = field(default_factory=list)

    # Errors
    errors: list[dict] = field(default_factory=list)


def majority_baseline(labels: list[float]) -> float:
    """Always predict the majority class."""
    if not labels:
        return 0.5
    return 1.0 if sum(labels) / len(labels) >= 0.5 else 0.0


def legacy_heuristic_predict(fv: FeatureVector) -> float:
    """Legacy heuristic: volume decrease + contact loss → affinity decrease."""
    score = 0.5
    if fv.f_volume_delta < -10:
        score += 0.10
    if fv.f_contact_count_delta < 0:
        score += 0.08
    if fv.f_polarity_added:
        score += 0.05
    if fv.f_aromatic_added:
        score += 0.05
    if fv.f_hbond_donor_gained:
        score += 0.05
    if fv.f_is_catalytic:
        score += 0.10
    if fv.f_is_ligand_contact:
        score += 0.08
    return min(0.95, max(0.05, score))


def logistic_regression_predict(fv: FeatureVector, coefficients: dict[str, float], intercept: float) -> float:
    """Simple logistic regression prediction with given coefficients."""
    arr = fv.to_array()
    names = FeatureVector.feature_names()
    logit = intercept
    # names/to_array() are the two parallel definitions of FeatureVector
    # (equal length by construction) — strict guards against drift.
    for name, value in zip(names, arr, strict=True):
        coef = coefficients.get(name, 0.0)
        logit += coef * value
    # Sigmoid
    if logit >= 0:
        return 1.0 / (1.0 + exp(-logit))
    return exp(logit) / (1.0 + exp(logit))


def train_logistic_regression(
    train_samples: list[FeatureVector],
    train_labels: list[float],
    learning_rate: float = 0.01,
    n_iterations: int = 1000,
    l2_penalty: float = 0.1,
) -> tuple[dict[str, float], float]:
    """Train a simple logistic regression with L2 regularization via gradient descent.

    Pure Python — no external ML dependency required for the pilot.
    """
    names = FeatureVector.feature_names()

    # Initialize coefficients
    coefs = {name: 0.0 for name in names}
    intercept = 0.0

    n = len(train_samples)
    if n == 0:
        return coefs, intercept

    for _ in range(n_iterations):
        # Compute gradients
        grad_coefs = {name: 0.0 for name in names}
        grad_intercept = 0.0

        # train_samples/train_labels are independent caller-supplied lists
        # (no length contract): strict=False keeps historical behaviour.
        for sample, label in zip(train_samples, train_labels, strict=False):
            arr = sample.to_array()
            pred = logistic_regression_predict(sample, coefs, intercept)
            error = pred - label

            for j, name in enumerate(names):
                if j < len(arr):
                    grad_coefs[name] += error * arr[j] / n
            grad_intercept += error / n

        # L2 regularization
        for name in names:
            grad_coefs[name] += l2_penalty * coefs[name] / n

        # Update
        for name in names:
            coefs[name] -= learning_rate * grad_coefs[name]
        intercept -= learning_rate * grad_intercept

    return coefs, intercept


def evaluate_predictions(
    y_true: list[float],
    y_pred: list[float],
    sample_ids: list[str],
    threshold: float = 0.5,
) -> PilotResult:
    """Compute classification metrics for binary predictions."""
    n = len(y_true)
    if n == 0:
        return PilotResult()

    y_bin = [1.0 if p >= threshold else 0.0 for p in y_pred]
    y_true_bin = [1.0 if t >= 0.5 else 0.0 for t in y_true]

    # Confusion matrix
    # y_true_bin/y_bin mirror the two independent caller-supplied lists
    # (no length contract): strict=False keeps historical behaviour.
    tp = sum(1 for t, p in zip(y_true_bin, y_bin, strict=False) if t >= 0.5 and p >= 0.5)
    tn = sum(1 for t, p in zip(y_true_bin, y_bin, strict=False) if t < 0.5 and p < 0.5)
    fp = sum(1 for t, p in zip(y_true_bin, y_bin, strict=False) if t < 0.5 and p >= 0.5)
    fn = sum(1 for t, p in zip(y_true_bin, y_bin, strict=False) if t >= 0.5 and p < 0.5)

    accuracy = (tp + tn) / n if n > 0 else 0.0
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # recall/sensitivity
    tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0  # specificity
    balanced_accuracy = (tpr + tnr) / 2.0

    # MCC
    denom = sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn) - (fp * fn)) / denom if denom > 0 else 0.0

    # Error analysis
    errors = []
    for i in range(n):
        if y_bin[i] != y_true_bin[i]:
            errors.append(
                {
                    "sample_id": sample_ids[i] if i < len(sample_ids) else f"sample_{i}",
                    "true": "decrease" if y_true[i] >= 0.5 else "increase",
                    "predicted": y_pred[i],
                    "predicted_label": "decrease" if y_pred[i] >= 0.5 else "increase",
                }
            )

    return PilotResult(
        accuracy=round(accuracy, 3),
        balanced_accuracy=round(balanced_accuracy, 3),
        mcc=round(mcc, 3),
        y_true=y_true,
        y_pred=y_pred,
        sample_ids=sample_ids,
        errors=errors,
    )
