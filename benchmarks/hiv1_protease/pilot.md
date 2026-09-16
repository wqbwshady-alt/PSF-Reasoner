# HIV-1 Protease Pilot Benchmark

> **Status**: PILOT — not a formal benchmark. Data quality varies across cases.

## Search Strategy

Literature search focused on:
1. Peer-reviewed publications with experimentally measured Ki/Kd/IC50 values
   for HIV-1 protease mutants vs inhibitors
2. Cases with available PDB structures (WT or mutant)
3. Preference for high-resolution crystal structures with clear mechanism labels

Sources used:
- Mahalingam et al. 2004, PMID 15066177 — V82A + L90M vs indinavir (MK1)
- Clemente et al. 2003, PMID 14690411 — D30N ± M36I/A71V vs nelfinavir
- Klabe et al. 1998, PMID 9628735 — cross-resistance survey (V82A/F, I84V)
- Liu et al. 2008, PMID 18597780 — flap mutations G48V, I50V, I54V
- Mahalingam et al. 1999, PMID 10429209 — L90M + G48V kinetics

## Case Summary

| # | case_id | Mutation | Inhibitor | Fold-change | Exact Ki? | Mechanism Label? |
|---|---------|----------|-----------|-------------|-----------|-----------------|
| 1 | hiv1-v82a-mk1 | V82A | Indinavir (MK1) | 3.35× | Yes (540→1810 pM) | Yes |
| 2 | hiv1-l90m-mk1 | L90M | Indinavir (MK1) | 0.16× | Yes (540→86 pM) | Yes |
| 3 | hiv1-d30n-nfv | D30N | Nelfinavir (NFV) | ~6× | No (estimated) | Yes |
| 4 | hiv1-d30n_m36i_a71v-nfv | D30N+M36I+A71V | Nelfinavir (NFV) | ~22× | No (estimated) | Yes |
| 5 | hiv1-v82a-sqv | V82A | Saquinavir (ROC) | ~20× | No | Partial |
| 6 | hiv1-i84v-idv | I84V | Indinavir (MK1) | ~10× | No | Partial |
| 7 | hiv1-v82f_idv | V82F | Indinavir (MK1) | ~30× | No | Partial |
| 8 | hiv1-v82f_i84v_idv | V82F+I84V | Indinavir (MK1) | ~200× | No | Partial |
| 9 | hiv1-g48v-sqv | G48V | Saquinavir (ROC) | ~13.5× | No | Partial |
| 10 | hiv1-i50v-apv | I50V | Amprenavir (APV) | ~25× | No | Partial |
| 11 | hiv1-l90m-sqv | L90M | Saquinavir (ROC) | ~5× | No | Partial |

## Data Quality

- **Cases 1-2**: High confidence. Exact Ki values from PMID 15066177. Both have matching WT and mutant PDB structures at ≤1.40 Å resolution.
- **Cases 3-4**: Medium confidence. Fold-change from PMID 14690411. Absolute Ki values estimated from typical WT NFV Ki. No confirmed mutant PDB structures.
- **Cases 5-11**: Low confidence (pilot). Fold-change values are approximate, extracted from literature abstracts and secondary sources. Absolute Ki values not verified against full text. Most excluded from calibration.

## Limitations

1. **Absolute Ki verification**: Cases 3-11 need full-text verification of exact Ki values.
2. **Assay condition matching**: Different papers used slightly different buffer conditions, pH, and temperature — cross-case comparison of absolute Ki values is not valid.
3. **Background mutations**: WT constructs often contain stabilizing mutations (Q7K, L33I, L63I, C67A, C95A) that differ between studies.
4. **Mechanism labels**: Cases 5-11 have mechanism labels inferred from general structural knowledge rather than specific experimental evidence in the cited paper.
5. **Single protein family**: All cases are HIV-1 protease. Generalization to other families is not yet assessed.
6. **Single reviewer**: All mechanism labels have been curated by one person. Multi-reviewer consensus is needed before formal benchmark freeze.


> **AUDIT 2026-09-10**: 本文件为 pilot 快照。已修正：V82A/L90M 的 mutant_pdb_id 1SDU/1SDV 对调错误；作者署名 Sayer→Clemente。仍待人工复核：Mahalingam 1999 (PMID 10429209) 三个 SQV 案例的 Table II 数值。详见 docs/EVIDENCE-REVIEW.md。
