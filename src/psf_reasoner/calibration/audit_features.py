"""Data audit for feature matrix (V3 Pilot Calibrator).

Before training, run comprehensive audit: missingness, distributions,
correlations, label imbalance, protein/label splits, and leakage checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

from psf_reasoner.calibration.feature_schema import FeatureVector


@dataclass
class FeatureAudit:
    """Complete feature audit report."""

    n_samples: int = 0
    n_features: int = 0

    # Labels
    label_distribution: dict[str, int] = field(default_factory=dict)
    label_imbalance_ratio: float = 0.0

    # Missingness
    feature_missingness: dict[str, float] = field(default_factory=dict)
    samples_with_missing: int = 0
    complete_samples: int = 0

    # Feature distributions
    feature_means: dict[str, float] = field(default_factory=dict)
    feature_stdevs: dict[str, float] = field(default_factory=dict)
    feature_mins: dict[str, float] = field(default_factory=dict)
    feature_maxs: dict[str, float] = field(default_factory=dict)
    constant_features: list[str] = field(default_factory=list)
    near_constant_features: list[str] = field(default_factory=list)

    # Correlations (with label)
    feature_label_correlations: dict[str, float] = field(default_factory=dict)
    top_correlated: list[tuple[str, float]] = field(default_factory=list)

    # Protein/label splits
    protein_counts: dict[str, int] = field(default_factory=dict)
    protein_label_distribution: dict[str, dict[str, int]] = field(default_factory=dict)

    # Warnings
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Feature Audit Report",
            f"====================",
            f"Samples: {self.n_samples}  Features: {self.n_features}",
            f"Complete samples: {self.complete_samples}/{self.n_samples}",
            f"",
            f"Label distribution: {self.label_distribution}",
            f"Imbalance ratio: {self.label_imbalance_ratio:.2f}",
            f"",
            f"Constant features: {self.constant_features or 'none'}",
            f"Near-constant: {self.near_constant_features or 'none'}",
            f"",
            f"Top feature-label correlations:",
        ]
        for name, corr in self.top_correlated[:8]:
            lines.append(f"  {name}: {corr:+.3f}")
        lines.append(f"")
        lines.append(f"Protein counts: {self.protein_counts}")
        if self.warnings:
            lines.append(f"")
            lines.append(f"Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        return "\n".join(lines)


def audit_features(matrix) -> FeatureAudit:
    """Run comprehensive audit on a feature matrix."""
    audit = FeatureAudit(
        n_samples=matrix.n_samples,
        n_features=matrix.n_features,
    )

    names = FeatureVector.feature_names()
    samples = matrix.samples
    labels = matrix.labels
    split_groups = matrix.split_groups
    if not samples:
        return audit

    # Label distribution
    for label, group in zip(labels, split_groups):
        direction = "decrease" if label >= 0.9 else ("increase" if label <= 0.1 else "neutral")
        audit.label_distribution[direction] = audit.label_distribution.get(direction, 0) + 1
        if group not in audit.protein_label_distribution:
            audit.protein_label_distribution[group] = {}
        audit.protein_label_distribution[group][direction] = (
            audit.protein_label_distribution[group].get(direction, 0) + 1
        )

    n_pos = audit.label_distribution.get("decrease", 0)
    n_neg = audit.label_distribution.get("increase", 0)
    audit.label_imbalance_ratio = n_pos / max(n_neg, 1)

    # Feature statistics
    for j, name in enumerate(names):
        values = []
        missing = 0
        for s in samples:
            arr = s.to_array()
            if j < len(arr):
                v = arr[j]
                if v == 0.0 and _is_missing_contextually(name, s):
                    missing += 1
                values.append(v)
            else:
                missing += 1

        audit.feature_missingness[name] = missing / len(samples) if samples else 0.0
        if values:
            audit.feature_means[name] = round(sum(values) / len(values), 3)
            variance = sum((v - audit.feature_means[name]) ** 2 for v in values) / len(values)
            audit.feature_stdevs[name] = round(sqrt(variance), 3)
            audit.feature_mins[name] = round(min(values), 3)
            audit.feature_maxs[name] = round(max(values), 3)

            # Constant check
            if audit.feature_stdevs[name] < 0.001:
                audit.constant_features.append(name)
            elif audit.feature_stdevs[name] < 0.01 * max(abs(audit.feature_means[name]), 0.001):
                audit.near_constant_features.append(name)

            # Label correlation (Pearson)
            if len(values) == len(labels) and audit.feature_stdevs[name] > 0.001:
                corr = _pearson_correlation(values, labels)
                audit.feature_label_correlations[name] = round(corr, 3)

    # Top correlated
    audit.top_correlated = sorted(
        audit.feature_label_correlations.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )

    # Protein counts
    for g in split_groups:
        audit.protein_counts[g] = audit.protein_counts.get(g, 0) + 1

    # Warnings
    if audit.label_imbalance_ratio > 5:
        audit.warnings.append(f"Severe label imbalance: {audit.label_imbalance_ratio:.1f}:1")
    missing_frac = 1.0 - audit.complete_samples / max(audit.n_samples, 1)
    if missing_frac > 0.5:
        audit.warnings.append(f"{missing_frac:.0%} samples have missing features")
    if audit.constant_features:
        audit.warnings.append(f"{len(audit.constant_features)} constant features — drop before training")
    if len(audit.protein_counts) < 3:
        audit.warnings.append(f"Only {len(audit.protein_counts)} split groups — CV unreliable")

    return audit


def _is_missing_contextually(name: str, sample: FeatureVector) -> bool:
    """Check if a zero value is genuinely missing (not just zero)."""
    # Structural features that should be non-zero for a real mutation
    structural_indicators = {
        "contact_count_delta", "atoms_lost", "atoms_gained",
        "nearest_ligand_distance", "neighborhood_4a_count",
    }
    if name in structural_indicators and sample.f_nearest_ligand_distance == 0.0:
        return True  # no structure data available
    if name == "nearest_ligand_distance" and sample.f_nearest_ligand_distance == 0.0:
        return True
    return False


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = len(x)
    if n < 3:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    sx = sqrt(sum((v - mx) ** 2 for v in x) / n)
    sy = sqrt(sum((v - my) ** 2 for v in y) / n)
    if sx < 1e-10 or sy < 1e-10:
        return 0.0
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / n
    return cov / (sx * sy)
