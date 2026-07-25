"""Model card generation (V3 Pilot Calibrator).

Produces a standardized model card documenting the pilot model's
limitations, training data, evaluation, and intended use.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from psf_reasoner.calibration.audit_features import FeatureAudit
from psf_reasoner.calibration.grouped_cv import CVEvaluation


def generate_model_card(
    audit: FeatureAudit,
    cv: CVEvaluation,
    ablation_results: list,
    output_path: str = "",
) -> str:
    """Generate a standardized model card for the pilot calibrator.

    Returns the card as a markdown string.  If *output_path* is provided,
    also writes it to disk.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# PSF-Reasoner Pilot Calibrator — Model Card",
        f"",
        f"**Version:** pilot_v1",
        f"**Generated:** {now}",
        f"**Status:** EXPERIMENTAL — NOT FOR PRODUCTION USE",
        f"",
        f"## Intended Use",
        f"",
        f"This is a PILOT model trained on 30 manually curated mutation–ligand",
        f"pairs.  It is intended ONLY for internal validation of the PSF data",
        f"pipeline (schema → features → model → evaluation).",
        f"",
        f"**This model MUST NOT be used to:**",
        f"- Make predictions about untested mutations",
        f"- Guide experimental decisions",
        f"- Replace literature review or expert judgment",
        f"- Predict clinical drug resistance",
        f"",
        f"## Training Data",
        f"",
        f"- **Samples:** {audit.n_samples}",
        f"- **Source:** Manually curated from peer-reviewed literature",
        f"- **Label:** Binary — affinity_decrease vs affinity_increase",
        f"- **Label distribution:** {audit.label_distribution}",
        f"- **Proteins:** {audit.protein_counts}",
        f"- **Features:** {audit.n_features} (mutation chemistry + physical evidence + structural context)",
        f"",
        f"## Data Limitations",
        f"",
        f"- Only 2/30 samples have complete structure pairs (PDB files)",
        f"- 28/30 samples lack structural context features (imputed as zeros)",
        f"- Label imbalance: {audit.label_imbalance_ratio:.1f}:1 (decrease:increase)",
        f"- EGFR and ABL1 values are fold-changes from literature, not ΔΔG",
        f"- β-lactamase labels are catalytic mutants (affinity_increase), not resistance",
        f"",
        f"## Evaluation",
        f"",
        f"**Method:** Leave-one-protein-out cross-validation ({cv.n_folds} folds)",
        f"",
    ]

    for model_name, agg in cv.aggregated.items():
        lines.append(f"### {model_name}")
        lines.append(f"- Balanced accuracy: {agg['mean_balanced_accuracy']:.3f}")
        lines.append(f"- MCC: {agg['mean_mcc']:.3f}")
        lines.append(f"- Folds completed: {agg['n_folds_completed']}/{cv.n_folds}")
        lines.append(f"- Total test samples: {agg['total_test_samples']}")
        lines.append(f"- Total errors: {agg['total_errors']}")
        lines.append(f"")

    lines.extend([
        f"## Feature Ablation",
        f"",
        f"| Model | Features | Accuracy | MCC |",
        f"|-------|----------|----------|-----|",
    ])
    for r in ablation_results:
        lines.append(f"| {r.model_label} | {r.n_features} | {r.accuracy:.3f} | {r.mcc:.3f} |")

    lines.extend([
        f"",
        f"## Caveats",
        f"",
        f"1. **Sample size:** 30 cases is insufficient for generalization",
        f"2. **Feature coverage:** Most structural features are zero for cases without PDB files",
        f"3. **Label definition:** Binary classification masks quantitative ΔΔG values",
        f"4. **Protein diversity:** 5 proteins, but only HIV-1 protease has 10 cases",
        f"5. **No external test set:** All evaluation is cross-validation on the same 30 cases",
        f"6. **Heuristic baseline is weak:** The legacy heuristic is a strawman, not a competitive baseline",
        f"",
        f"## Next Steps",
        f"",
        f"1. Add PDB structure files for remaining 28 cases",
        f"2. Expand to 100-300 cases with quantitative ΔΔG labels",
        f"3. Add external test set (hold out 1-2 proteins entirely)",
        f"4. Calibrate probabilities with Platt scaling or isotonic regression",
        f"5. Compare with FoldX/Rosetta/MM-GBSA as external baselines",
        f"",
        f"## Responsible Use",
        f"",
        f"This model card must accompany any use of the pilot calibrator.",
        f"The calibrator is a research prototype, not a validated scientific instrument.",
    ])

    card = "\n".join(lines)
    if output_path:
        with open(output_path, "w") as f:
            f.write(card)
    return card
