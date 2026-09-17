"""Model card generation (V3 Pilot Calibrator).

Produces a standardized model card documenting the pilot model's
limitations, training data, evaluation, and intended use.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# PSF-Reasoner Pilot Calibrator — Model Card",
        "",
        "**Version:** pilot_v1",
        f"**Generated:** {now}",
        "**Status:** EXPERIMENTAL — NOT FOR PRODUCTION USE",
        "",
        "## Intended Use",
        "",
        "This is a PILOT model trained on 30 manually curated mutation–ligand",
        "pairs.  It is intended ONLY for internal validation of the PSF data",
        "pipeline (schema → features → model → evaluation).",
        "",
        "**This model MUST NOT be used to:**",
        "- Make predictions about untested mutations",
        "- Guide experimental decisions",
        "- Replace literature review or expert judgment",
        "- Predict clinical drug resistance",
        "",
        "## Training Data",
        "",
        f"- **Samples:** {audit.n_samples}",
        "- **Source:** Manually curated from peer-reviewed literature",
        "- **Label:** Binary — affinity_decrease vs affinity_increase",
        f"- **Label distribution:** {audit.label_distribution}",
        f"- **Proteins:** {audit.protein_counts}",
        f"- **Features:** {audit.n_features} (mutation chemistry + physical evidence + structural context)",
        "",
        "## Data Limitations",
        "",
        "- Only 2/30 samples have complete structure pairs (PDB files)",
        "- 28/30 samples lack structural context features (imputed as zeros)",
        f"- Label imbalance: {audit.label_imbalance_ratio:.1f}:1 (decrease:increase)",
        "- EGFR and ABL1 values are fold-changes from literature, not ΔΔG",
        "- β-lactamase labels are catalytic mutants (affinity_increase), not resistance",
        "",
        "## Evaluation",
        "",
        f"**Method:** Leave-one-protein-out cross-validation ({cv.n_folds} folds)",
        "",
    ]

    for model_name, agg in cv.aggregated.items():
        lines.append(f"### {model_name}")
        lines.append(f"- Balanced accuracy: {agg['mean_balanced_accuracy']:.3f}")
        lines.append(f"- MCC: {agg['mean_mcc']:.3f}")
        lines.append(f"- Folds completed: {agg['n_folds_completed']}/{cv.n_folds}")
        lines.append(f"- Total test samples: {agg['total_test_samples']}")
        lines.append(f"- Total errors: {agg['total_errors']}")
        lines.append("")

    lines.extend(
        [
            "## Feature Ablation",
            "",
            "| Model | Features | Accuracy | MCC |",
            "|-------|----------|----------|-----|",
        ]
    )
    for r in ablation_results:
        lines.append(f"| {r.model_label} | {r.n_features} | {r.accuracy:.3f} | {r.mcc:.3f} |")

    lines.extend(
        [
            "",
            "## Caveats",
            "",
            "1. **Sample size:** 30 cases is insufficient for generalization",
            "2. **Feature coverage:** Most structural features are zero for cases without PDB files",
            "3. **Label definition:** Binary classification masks quantitative ΔΔG values",
            "4. **Protein diversity:** 5 proteins, but only HIV-1 protease has 10 cases",
            "5. **No external test set:** All evaluation is cross-validation on the same 30 cases",
            "6. **Heuristic baseline is weak:** The legacy heuristic is a strawman, "
            "not a competitive baseline",
            "",
            "## Next Steps",
            "",
            "1. Add PDB structure files for remaining 28 cases",
            "2. Expand to 100-300 cases with quantitative ΔΔG labels",
            "3. Add external test set (hold out 1-2 proteins entirely)",
            "4. Calibrate probabilities with Platt scaling or isotonic regression",
            "5. Compare with FoldX/Rosetta/MM-GBSA as external baselines",
            "",
            "## Responsible Use",
            "",
            "This model card must accompany any use of the pilot calibrator.",
            "The calibrator is a research prototype, not a validated scientific instrument.",
        ]
    )

    card = "\n".join(lines)
    if output_path:
        with open(output_path, "w") as f:
            f.write(card)
    return card
