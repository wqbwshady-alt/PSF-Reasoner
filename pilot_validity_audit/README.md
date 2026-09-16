# pilot_validity_audit — 历史快照（已废弃）

> **状态（2026-09-10）：本目录中的全部产物均为历史快照，不再代表当前数据集。**

这些文件是在旧的 30 条（后扩展到 118 条）"金案例"上计算的。2026-09-10 的
独立证据审计（docs/EVIDENCE-REVIEW.md）证明该数据集 103/118 条引用了与
声称无关的 PMID、50 条为配额填充的编造数据。数据集已重建
（`src/psf_reasoner/datasets/golden_cases.py`，当前仅 9 条 ACCEPTED）。

因此：

- 本目录的 `ablation_metrics.json`、`complete_subset_results.json`、
  `fold_metrics.csv`、`leave_one_protein_out.csv`、`missingness_baseline.json`、
  `target_masked_results.json`、`pilot_validity_summary.md` 中的数字
  （包括 "MCC 0.711"、"Identity-blinded MCC = 0.000" 等）**不得再被引用**。
- 在 9 条已核实案例上重新计算这些审计没有统计意义（样本过小）。
- 重新建立有效的校准评估需要：先按 docs/EVIDENCE-REVIEW.md 表 4 完成
  人工复核、扩充已核实案例，再按 V3-ROADMAP 的校准门槛执行。

保留本目录仅为存档，供追溯旧结论的产生过程。
