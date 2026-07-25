"""Model evaluation with proper splits (V3 P4).

Implements protein-level and family-level split strategies to prevent
data leakage, plus calibration metrics (AUROC, Brier score, ECE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log


@dataclass
class SplitResult:
    """Evaluation result for one train/test split."""

    split_name: str = ""
    train_samples: int = 0
    test_samples: int = 0
    train_proteins: list[str] = field(default_factory=list)
    test_proteins: list[str] = field(default_factory=list)


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics for a calibrated model."""

    # Classification (for binary labels like resistance_binary)
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    mcc: float = 0.0  # Matthews correlation coefficient

    # Ranking
    auroc: float = 0.0  # Area under ROC curve
    auprc: float = 0.0  # Area under precision-recall curve

    # Regression (for continuous labels like ddG)
    mae: float = 0.0    # Mean absolute error
    rmse: float = 0.0   # Root mean square error
    r2: float = 0.0     # R² score

    # Calibration
    brier_score: float = 0.0
    ece: float = 0.0    # Expected calibration error
    calibration_slope: float = 1.0
    calibration_intercept: float = 0.0

    # Counts
    n_samples: int = 0
    n_positive: int = 0
    n_negative: int = 0

    def summary(self) -> str:
        """Human-readable summary of key metrics."""
        lines = [
            f"  N={self.n_samples} (positive={self.n_positive}, negative={self.n_negative})",
            f"  Accuracy: {self.accuracy:.3f}  MCC: {self.mcc:.3f}",
            f"  AUROC: {self.auroc:.3f}  AUPRC: {self.auprc:.3f}",
            f"  Brier: {self.brier_score:.4f}  ECE: {self.ece:.4f}",
        ]
        if self.mae > 0 or self.rmse > 0:
            lines.append(f"  MAE: {self.mae:.3f}  RMSE: {self.rmse:.3f}  R²: {self.r2:.3f}")
        return "\n".join(lines)


def generate_splits(
    samples: list,
    split_key_attr: str = "split_group",
    n_folds: int = 3,
) -> list[tuple[list, list]]:
    """Generate protein-level train/test splits (leave-one-protein-out).

    Each fold holds out one *split_group* as the test set and uses all
    others for training.  This is the minimum standard for preventing
    protein-level data leakage.

    Returns list of (train_samples, test_samples) pairs.
    """
    # Group samples by split key
    groups: dict[str, list] = {}
    for s in samples:
        key = getattr(s, split_key_attr, "unknown")
        if key not in groups:
            groups[key] = []
        groups[key].append(s)

    group_keys = sorted(groups.keys())

    if len(group_keys) <= 1:
        # Only one group — use random 80/20 split (fallback)
        n = len(samples)
        cutoff = int(n * 0.8)
        return [(samples[:cutoff], samples[cutoff:])]

    # Leave-one-group-out
    splits = []
    for held_out in group_keys:
        train = [s for k in group_keys if k != held_out for s in groups[k]]
        test = groups[held_out]
        if train and test:
            splits.append((train, test))

    return splits[:n_folds]


def compute_binary_metrics(
    y_true: list[float],
    y_pred: list[float],
    threshold: float = 0.5,
) -> EvaluationMetrics:
    """Compute classification + calibration metrics for binary predictions.

    Pure Python — no numpy/scipy dependency required.  Suitable for
    small pilot benchmarks where heavy dependencies are not justified.
    """
    n = len(y_true)
    if n == 0:
        return EvaluationMetrics()

    y_binary = [1.0 if p >= threshold else 0.0 for p in y_pred]

    # Confusion matrix
    tp = sum(1 for t, p in zip(y_true, y_binary) if t >= 0.5 and p >= 0.5)
    tn = sum(1 for t, p in zip(y_true, y_binary) if t < 0.5 and p < 0.5)
    fp = sum(1 for t, p in zip(y_true, y_binary) if t < 0.5 and p >= 0.5)
    fn = sum(1 for t, p in zip(y_true, y_binary) if t >= 0.5 and p < 0.5)

    accuracy = (tp + tn) / n if n > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # MCC
    denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = ((tp * tn) - (fp * fn)) / denom if denom > 0 else 0.0

    # AUROC (simple trapezoidal rule)
    auroc = _compute_auroc(y_true, y_pred)

    # Brier score
    brier = sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / n

    # ECE (expected calibration error, 5 bins)
    ece = _compute_ece(y_true, y_pred, n_bins=5)

    return EvaluationMetrics(
        accuracy=round(accuracy, 3),
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
        mcc=round(mcc, 3),
        auroc=round(auroc, 3),
        brier_score=round(brier, 4),
        ece=round(ece, 4),
        n_samples=n,
        n_positive=sum(1 for t in y_true if t >= 0.5),
        n_negative=sum(1 for t in y_true if t < 0.5),
    )


def _compute_auroc(y_true: list[float], y_pred: list[float]) -> float:
    """Compute AUROC by trapezoidal rule (no scipy dependency)."""
    pairs = sorted(zip(y_pred, y_true), key=lambda x: x[0], reverse=True)
    n_pos = sum(1 for _, t in pairs if t >= 0.5)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5

    tp_rate = 0.0
    fp_rate = 0.0
    prev_fpr = 0.0
    prev_tpr = 0.0
    area = 0.0

    for i, (_, label) in enumerate(pairs):
        if label >= 0.5:
            tp_rate += 1.0 / n_pos
        else:
            fp_rate += 1.0 / n_neg
            area += tp_rate / n_neg

    return area


def _compute_ece(y_true: list[float], y_pred: list[float], n_bins: int = 5) -> float:
    """Compute Expected Calibration Error with equal-width bins."""
    if not y_true:
        return 0.0

    bin_size = 1.0 / n_bins
    ece = 0.0
    n = len(y_true)

    for b in range(n_bins):
        lower = b * bin_size
        upper = (b + 1) * bin_size
        bin_indices = [
            i for i, p in enumerate(y_pred)
            if lower <= p < upper or (b == n_bins - 1 and p == upper)
        ]
        if not bin_indices:
            continue
        bin_avg_pred = sum(y_pred[i] for i in bin_indices) / len(bin_indices)
        bin_avg_true = sum(y_true[i] for i in bin_indices) / len(bin_indices)
        ece += len(bin_indices) / n * abs(bin_avg_pred - bin_avg_true)

    return round(ece, 4)
