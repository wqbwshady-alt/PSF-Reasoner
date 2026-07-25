# PSF-Reasoner Pilot Validity Audit

## 1. Ablation Matrix
| Model | Features | Accuracy | MCC |
|-------|----------|----------|-----|
| M0_chemistry | 7 | 0.767 | 0.000 |
| M1_structure | 9 | 0.600 | 0.154 |
| M2_literature | 3 | 0.767 | 0.000 |
| M3_chem+struct | 16 | 0.600 | 0.154 |
| M4_chem+lit | 10 | 0.767 | 0.000 |
| M5_struct+lit | 12 | 0.867 | 0.599 |
| M6_all | 23 | 0.900 | 0.711 |

## 2. Literature Leakage Audit
- Full model MCC: 0.711
- Literature-masked MCC: 0.441
- Literature-only MCC: 0.000
- MCC drop on masking: 0.270

**Conclusion:** Mixed — investigate per-fold.

## 3. Missingness Baseline
- Accuracy: 0.767, MCC: 0.000
- Decrease rate with structure: 0.750
- Decrease rate without structure: 0.800

**Conclusion:** Missingness NOT independently predictive

## 4. Complete Subset Analysis
| Subset | N | Accuracy | MCC | Label Dist |
|--------|---|----------|-----|------------|
| A_all_30 | 30 | 0.900 | 0.711 | 23decrease/7increase |
| B_struct_20 | 20 | 1.000 | 1.000 | 15decrease/5increase |
| C_contact_8 | 0 | 0.000 | 0.000 | ? |

## 5. Leave-One-Protein-Out CV
- **majority**: balanced_acc=0.400, MCC=0.000, folds=5
- **heuristic**: balanced_acc=0.400, MCC=0.000, folds=5
- **logistic_regression**: balanced_acc=0.110, MCC=0.000, folds=5

**Conclusion:** No cross-protein generalization detected — model likely memorizing protein-specific patterns.

## 6. Error Analysis
Total errors: 3
- **BLAC_E104A_PEN**: true=increase, pred=0.643, likely=No literature evidence — relying on weak structural signal
- **EGFR_L858R_IRE**: true=increase, pred=0.852, likely=No structure features — predicting from protein group prior only
- **EGFR_G719S_IRE**: true=increase, pred=0.852, likely=No structure features — predicting from protein group prior only

## 7. Overall Assessment

### Pipeline Feasibility
✅ Data → Features → Model → Evaluation loop is functional.

### Learnable Signal
✅ Strong signal detected (best MCC=0.711) — but verify source.

### Structure Contribution
✅ Structure features contribute independently (masked MCC=0.441).

### Literature Contribution
Literature and structure contributions are comparable.

### Leakage Risk
✅ LOW — literature features do not dominate.

### Generalization Evidence
❌ No cross-protein generalization detected. Model likely overfitting to protein-specific patterns or data collection biases.

### Current Verdict
**Pilot data-pipeline closed loop is functional. MCC 0.711 on full data represents an existence proof that learnable signal is present, but the source (structure vs literature vs missingness bias vs protein memorization) has not been isolated.**

Next step: restructure literature features to exclude direct target conclusions, expand to 100+ cases, then re-evaluate.