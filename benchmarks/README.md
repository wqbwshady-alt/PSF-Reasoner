# PSF-Reasoner Benchmarks

## Directory Structure

```
benchmarks/
    README.md                    ← this file
    hiv1_protease/
        pilot.json               ← N1B: pilot dataset (≥10 cases)
        pilot.md                 ← search strategy, inclusion/exclusion criteria
        README.md                ← family context, known biases
```

## Curation Standards

Every case in a benchmark dataset must record:

1. **Literature provenance**: PMID/DOI + source table or figure number.
2. **Assay conditions**: pH, temperature, buffer composition — these affect
   affinity measurements and limit cross-case comparability.
3. **Background mutations**: secondary mutations present in the structure
   beyond the primary one under study.
4. **Exclusion flags**: cases with data quality issues or confounding factors
   stay in the dataset but are excluded from quantitative evaluation.

## Functional Outcome vs Mechanism Label

**Functional outcome** (Ki, Kd, IC50, fold-change) measures what happened to
binding affinity. **Mechanism label** describes why — the structural mechanism
responsible for the change. These are recorded in separate fields:

- `assay_type`, `wt_value`, `mutant_value`, `wt_unit`, `mutant_unit`,
  `fold_change`, `direction` — functional outcome
- `mechanism_label`, `mechanism_evidence`, `mechanism_source`,
  `mechanism_review_status`, `mechanism_confidence` — mechanism label

A mutation can change binding affinity through multiple distinct structural
mechanisms. The correct mechanism is NOT automatically identified by the
functional measurement.

## Assay Type Handling

Ki, Kd, and IC50 measure different things and **must not be pooled as a single
absolute numeric scale**. Each case records its original units and assay type.
Cross-case comparison uses normalized direction (increase/decrease/unchanged)
and fold-change when available and comparable.

## Mechanism Label Evidence Tiers

| Tier | `mechanism_evidence` | Description |
|------|---------------------|-------------|
| 1 | `literature` | Mechanism explicitly proposed and supported by experimental evidence in a peer-reviewed publication |
| 2 | `structural_analysis` | Mechanism inferred from direct structural inspection (e.g., contact analysis of the PDB structure) |
| 3 | `expert_review` | Mechanism assessed by a domain expert based on available evidence |
| 4 | `none` | No mechanism label available — case usable for functional outcome metrics only |

## Review Status

| Status | Meaning |
|--------|---------|
| `unreviewed` | Initial curation, not independently verified |
| `single_reviewer` | Reviewed by one person (author or colleague) |
| `consensus` | Agreement across ≥2 independent reviewers |

## Exclusion Criteria for Calibration

A case should be `excluded_from_calibration=True` when:

- Background mutations confound the interpretation of the primary mutation
- The structure is low-resolution or has significant missing density at the
  binding site
- The assay conditions differ substantially from physiological conditions
  without a clear justification
- The mechanism label is `none` AND the case is being used for mechanism-level
  evaluation (cases without mechanism labels are still valid for
  functional-outcome-level metrics)
- Data was extracted from a review article rather than the primary
  experimental publication

## Versioning

Benchmark datasets are versioned. A frozen benchmark has a version tag
(e.g., `v1.0.0`), a frozen hash, and a changelog. No changes to cases,
labels, or train/test splits without a version bump.
