"""Grouped cross-validation with leave-one-protein-out (V3 Pilot Calibrator).

Ensures no data leakage across protein families.  Each fold holds out
one split_group entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psf_reasoner.calibration.build_feature_matrix import FeatureMatrix
from psf_reasoner.calibration.train_pilot import (
    PilotResult,
    evaluate_predictions,
    legacy_heuristic_predict,
    logistic_regression_predict,
    majority_baseline,
    train_logistic_regression,
)


@dataclass
class CVEvaluation:
    """Complete cross-validation evaluation for all models."""

    n_folds: int = 0
    models: dict[str, list[PilotResult]] = field(default_factory=dict)
    aggregated: dict[str, dict] = field(default_factory=dict)


def run_grouped_cv(matrix: FeatureMatrix) -> CVEvaluation:
    """Run leave-one-group-out CV for all pilot models.

    Each fold: hold out one split_group as test, train on the rest.
    """
    groups = sorted(set(matrix.split_groups))
    n_folds = len(groups)

    cv = CVEvaluation(n_folds=n_folds)
    model_results: dict[str, list[PilotResult]] = {
        "majority": [],
        "heuristic": [],
        "logistic_regression": [],
    }

    for held_out_group in groups:
        # Split
        train_idx = [i for i, g in enumerate(matrix.split_groups) if g != held_out_group]
        test_idx = [i for i, g in enumerate(matrix.split_groups) if g == held_out_group]

        train_samples = [matrix.samples[i] for i in train_idx]
        train_labels = [matrix.labels[i] for i in train_idx]
        test_samples = [matrix.samples[i] for i in test_idx]
        test_labels = [matrix.labels[i] for i in test_idx]
        test_ids = [matrix.sample_ids[i] for i in test_idx]

        if not test_samples:
            continue

        # 1. Majority baseline
        maj_pred_val = majority_baseline(train_labels)
        maj_preds = [maj_pred_val] * len(test_labels)
        result_maj = evaluate_predictions(test_labels, maj_preds, test_ids)
        result_maj.model_name = "majority"
        result_maj.n_train = len(train_samples)
        result_maj.n_test = len(test_samples)
        result_maj.test_split_groups = [held_out_group]
        model_results["majority"].append(result_maj)

        # 2. Legacy heuristic
        heur_preds = [legacy_heuristic_predict(s) for s in test_samples]
        result_heur = evaluate_predictions(test_labels, heur_preds, test_ids)
        result_heur.model_name = "heuristic"
        result_heur.n_train = len(train_samples)
        result_heur.n_test = len(test_samples)
        result_heur.test_split_groups = [held_out_group]
        model_results["heuristic"].append(result_heur)

        # 3. Logistic regression
        try:
            coefs, intercept = train_logistic_regression(train_samples, train_labels)
            lr_preds = [logistic_regression_predict(s, coefs, intercept) for s in test_samples]
            result_lr = evaluate_predictions(test_labels, lr_preds, test_ids)
        except Exception:
            result_lr = PilotResult()
        result_lr.model_name = "logistic_regression"
        result_lr.n_train = len(train_samples)
        result_lr.n_test = len(test_samples)
        result_lr.test_split_groups = [held_out_group]
        model_results["logistic_regression"].append(result_lr)

    cv.models = model_results

    # Aggregate metrics
    for model_name, results in model_results.items():
        if not results:
            continue
        accs = [r.accuracy for r in results if r.n_test > 0]
        baccs = [r.balanced_accuracy for r in results if r.n_test > 0]
        mccs = [r.mcc for r in results if r.n_test > 0]
        n_folds_used = len(accs)

        cv.aggregated[model_name] = {
            "mean_accuracy": round(sum(accs) / max(n_folds_used, 1), 3),
            "mean_balanced_accuracy": round(sum(baccs) / max(n_folds_used, 1), 3),
            "mean_mcc": round(sum(mccs) / max(n_folds_used, 1), 3),
            "n_folds_completed": n_folds_used,
            "total_test_samples": sum(r.n_test for r in results),
            "total_errors": sum(len(r.errors) for r in results),
        }

    return cv
