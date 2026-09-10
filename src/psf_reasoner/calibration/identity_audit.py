"""Identity baseline and confounding audit.

Answers: does the model learn mechanism, or just memorize protein family?
Adds protein-only, ligand-only, and identity-blinded baselines.
"""

from __future__ import annotations

import json
from pathlib import Path

from psf_reasoner.calibration.build_feature_matrix import build_feature_matrix
from psf_reasoner.calibration.feature_schema import FeatureVector
from psf_reasoner.calibration.train_pilot import (
    evaluate_predictions,
    logistic_regression_predict,
    train_logistic_regression,
)

_AUDIT_DIR = Path(__file__).parent.parent.parent.parent / "pilot_validity_audit"

# Protein family encoding
_FAMILY_MAP = {
    "P03367": 0, "P00374": 1, "P62593": 2, "P00533": 3, "P00519": 4,
}
# Ligand encoding
_LIGAND_MAP = {
    "MK1": 0, "DRV": 1, "APV": 2, "NFV": 3, "SQV": 4, "IDV": 5,
    "MTX": 6, "PEN": 7, "IRE": 8, "ERL": 9, "STI": 10,
}


def run_identity_audit() -> dict:
    """Run identity baselines: protein-only, ligand-only, identity-blinded."""
    matrix = build_feature_matrix()
    all_names = FeatureVector.feature_names()

    results = {}
    for baseline_name, feature_builder in [
        ("protein_family_only", _protein_features),
        ("ligand_only", _ligand_features),
        ("protein_plus_ligand", _protein_ligand_features),
        ("identity_blinded", _identity_blinded),
        ("structure_only", _structure_features),
    ]:
        samples, labels = feature_builder(matrix)
        if len(samples) < 3:
            results[baseline_name] = {"error": "too few samples", "n": len(samples)}
            continue

        coefs, intercept = train_logistic_regression(samples, labels)
        preds = [logistic_regression_predict(s, coefs, intercept) for s in samples]
        r = evaluate_predictions(labels, preds, matrix.sample_ids)
        results[baseline_name] = {
            "accuracy": r.accuracy, "balanced_accuracy": r.balanced_accuracy,
            "mcc": r.mcc, "n": len(samples),
        }

    # Within-family evaluation
    family_results = {}
    for family, family_label in _FAMILY_MAP.items():
        indices = [i for i, s in enumerate(matrix.samples) if s.split_group == family]
        if len(indices) < 3:
            family_results[family] = {"error": "too few samples", "n": len(indices)}
            continue
        subset = [matrix.samples[i] for i in indices]
        sub_labels = [matrix.labels[i] for i in indices]
        sub_ids = [matrix.sample_ids[i] for i in indices]
        coefs, intercept = train_logistic_regression(subset, sub_labels)
        preds = [logistic_regression_predict(s, coefs, intercept) for s in subset]
        r = evaluate_predictions(sub_labels, preds, sub_ids)
        unique_labels = len(set(sub_labels))
        family_results[family] = {
            "n": len(indices),
            "unique_labels": unique_labels,
            "accuracy": r.accuracy,
            "mcc": r.mcc,
            "can_evaluate": unique_labels >= 2,
        }

    # Cross-family: leave one family out entirely
    cross_results = {}
    for held_out in _FAMILY_MAP:
        train_idx = [i for i, s in enumerate(matrix.samples) if s.split_group != held_out]
        test_idx = [i for i, s in enumerate(matrix.samples) if s.split_group == held_out]
        if len(train_idx) < 3 or len(test_idx) < 2:
            continue
        train_samples = [matrix.samples[i] for i in train_idx]
        train_labels = [matrix.labels[i] for i in train_idx]
        test_samples = [matrix.samples[i] for i in test_idx]
        test_labels = [matrix.labels[i] for i in test_idx]
        test_ids = [matrix.sample_ids[i] for i in test_idx]
        coefs, intercept = train_logistic_regression(train_samples, train_labels)
        preds = [logistic_regression_predict(s, coefs, intercept) for s in test_samples]
        r = evaluate_predictions(test_labels, preds, test_ids)
        cross_results[held_out] = {
            "n_train": len(train_idx), "n_test": len(test_idx),
            "accuracy": r.accuracy, "mcc": r.mcc,
        }

    return {
        "identity_baselines": results,
        "within_family": family_results,
        "cross_family": cross_results,
    }


def _protein_features(matrix):
    """One-hot encoded protein family features."""
    samples, labels = [], []
    for s, l in zip(matrix.samples, matrix.labels):
        fid = _FAMILY_MAP.get(s.split_group, -1)
        fv = FeatureVector(sample_id=s.sample_id, split_group=s.split_group)
        # Abuse volume_delta as family encoding
        fv.f_volume_delta = float(fid) if fid >= 0 else -1.0
        for i, fam in enumerate(["P03367", "P00374", "P62593", "P00533", "P00519"]):
            val = 1.0 if s.split_group == fam else 0.0
            if i == 0: fv.f_polarity_added = val
            elif i == 1: fv.f_aromatic_added = val
            elif i == 2: fv.f_hbond_donor_gained = val
            elif i == 3: fv.f_hbond_acceptor_gained = val
            elif i == 4: fv.f_is_catalytic = val
        samples.append(fv)
        labels.append(l)
    return samples, labels


def _ligand_features(matrix):
    """Ligand-only features."""
    samples, labels = [], []
    from psf_reasoner.datasets.golden_cases import load_verified_cases
    cases = {c.sample_id: c for c in load_verified_cases()}
    for s, l in zip(matrix.samples, matrix.labels):
        case = cases.get(s.sample_id)
        lid = case.ligand_id if case else "?"
        fid = _LIGAND_MAP.get(lid, -1)
        fv = FeatureVector(sample_id=s.sample_id, split_group=s.split_group)
        fv.f_volume_delta = float(fid)
        fv.f_ligand_heavy_atoms = 1 if lid in ("MK1", "DRV", "APV", "NFV", "SQV", "IDV") else 0  # HIV inhibitors
        samples.append(fv)
        labels.append(l)
    return samples, labels


def _protein_ligand_features(matrix):
    """Protein + ligand combined."""
    from psf_reasoner.datasets.golden_cases import load_verified_cases
    cases = {c.sample_id: c for c in load_verified_cases()}
    samples, labels = [], []
    for s, l in zip(matrix.samples, matrix.labels):
        case = cases.get(s.sample_id)
        fid = _FAMILY_MAP.get(s.split_group, -1)
        lid = _LIGAND_MAP.get(case.ligand_id if case else "?", -1)
        fv = FeatureVector(sample_id=s.sample_id, split_group=s.split_group)
        fv.f_volume_delta = float(fid)
        fv.f_ligand_heavy_atoms = float(lid)
        fv.f_is_ligand_contact = 1.0 if fid == 0 else 0.0  # HIV
        fv.f_is_pocket_lining = 1.0 if fid == 1 else 0.0  # DHFR
        samples.append(fv)
        labels.append(l)
    return samples, labels


def _identity_blinded(matrix):
    """All features EXCEPT protein family and ligand identity."""
    all_names = FeatureVector.feature_names()
    # Identity-related features to exclude
    exclude = {
        "ligand_heavy_atoms", "ligand_hbond_donors", "ligand_hbond_acceptors",
        "ligand_charge",
        "direct_evidence_count", "strong_evidence_count", "any_literature",
    }
    keep_indices = [i for i, n in enumerate(all_names) if n not in exclude]
    # Zero out identity features, keep structure
    samples, labels = [], []
    for s, l in zip(matrix.samples, matrix.labels):
        arr = s.to_array()
        fv = FeatureVector(sample_id=s.sample_id, split_group=s.split_group)
        for i, name in enumerate(all_names):
            if i in keep_indices and i < len(arr):
                # Directly set structure features
                if name == "volume_delta": fv.f_volume_delta = arr[i]
                elif name == "contact_count_delta": fv.f_contact_count_delta = int(arr[i])
                elif name == "atoms_lost": fv.f_atoms_lost = int(arr[i])
                elif name == "atoms_gained": fv.f_atoms_gained = int(arr[i])
                elif name == "nearest_ligand_distance": fv.f_nearest_ligand_distance = arr[i]
                elif name == "neighborhood_4a_count": fv.f_neighborhood_4a_count = int(arr[i])
                elif name == "is_catalytic": fv.f_is_catalytic = int(arr[i])
                elif name == "is_ligand_contact": fv.f_is_ligand_contact = int(arr[i])
                elif name == "is_pocket_lining": fv.f_is_pocket_lining = int(arr[i])
                elif name == "pocket_catalytic_in_4a": fv.f_pocket_catalytic_in_4a = int(arr[i])
        samples.append(fv)
        labels.append(l)
    return samples, labels


def _structure_features(matrix):
    """Only structural/physical features, no identity, no literature."""
    all_names = FeatureVector.feature_names()
    struct_names = {
        "volume_delta", "polarity_added", "polarity_removed", "charge_delta",
        "aromatic_added", "hbond_donor_gained", "hbond_acceptor_gained",
        "contact_count_delta", "atoms_lost", "atoms_gained",
        "nearest_ligand_distance", "neighborhood_4a_count",
        "is_catalytic", "is_ligand_contact", "is_pocket_lining",
        "pocket_catalytic_in_4a",
    }
    samples, labels = [], []
    for s, l in zip(matrix.samples, matrix.labels):
        arr = s.to_array()
        fv = FeatureVector(sample_id=s.sample_id, split_group=s.split_group)
        for i, name in enumerate(all_names):
            if name in struct_names and i < len(arr):
                if name == "volume_delta": fv.f_volume_delta = arr[i]
                elif name == "polarity_added": fv.f_polarity_added = int(arr[i])
                elif name == "polarity_removed": fv.f_polarity_removed = int(arr[i])
                elif name == "charge_delta": fv.f_charge_delta = int(arr[i])
                elif name == "aromatic_added": fv.f_aromatic_added = int(arr[i])
                elif name == "hbond_donor_gained": fv.f_hbond_donor_gained = int(arr[i])
                elif name == "hbond_acceptor_gained": fv.f_hbond_acceptor_gained = int(arr[i])
                elif name == "contact_count_delta": fv.f_contact_count_delta = int(arr[i])
                elif name == "atoms_lost": fv.f_atoms_lost = int(arr[i])
                elif name == "atoms_gained": fv.f_atoms_gained = int(arr[i])
                elif name == "nearest_ligand_distance": fv.f_nearest_ligand_distance = arr[i]
                elif name == "neighborhood_4a_count": fv.f_neighborhood_4a_count = int(arr[i])
                elif name == "is_catalytic": fv.f_is_catalytic = int(arr[i])
                elif name == "is_ligand_contact": fv.f_is_ligand_contact = int(arr[i])
                elif name == "is_pocket_lining": fv.f_is_pocket_lining = int(arr[i])
        samples.append(fv)
        labels.append(l)
    return samples, labels


if __name__ == "__main__":
    result = run_identity_audit()
    print(json.dumps(result, indent=2, default=str))
