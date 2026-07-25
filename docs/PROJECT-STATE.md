# PSF-Reasoner 项目全景 · 2026-07-21

## V1 — 工程管线（已完成）

蛋白质结构解析 → 物理证据计算 → 基线推理 → FastAPI + CLI + 3Dmol.js 前端。

**核心交付：**
- `physical/` — 12 类物理证据计算器（距离、接触、SASA、氢键、疏水、盐桥、π、水桥、口袋、网络、能量、突变建模）
- `reasoning/baseline.py` — BaselineForwardReasoner、BaselineReverseReasoner、BaselineConsistencyChecker
- `schemas/` — 完整 Pydantic 数据模型（Claim、PhysicalEvidence、StructuralMechanism、PSFReport 等）
- `api/app.py` — FastAPI 应用（`/analyze`、`/forward`、`/reverse` 端点）
- `api/static/` — 3Dmol.js 前端工作台
- 128 个测试

## V2 — 信息组织层（已完成）

将推理结果从"一个百分比"升级为可追溯、可展开的证据网络。

**核心交付：**
- Structure Pair QC（RMSD、chain mapping、背景突变、comparable/partially/poorly 三级评分）
- ScoreBreakdown（supporting/conflicting/missing evidence counts）
- EvidenceGraph（每个机制的 ✅ 支持 / ❌ 冲突 / ⬜ 缺失证据）
- MechanismCategory（Evidence-supported vs Hypothesized）
- SupportCoverage（功能假设的证据覆盖进度条）
- AgreementDetail（physical/functional/phenotype 三维度一致性）
- Validation Roadmap（Priority 1-5）
- SASA 归一化（relative/backbone/sidechain）、Cutoff Sensitivity、Interaction Provenance
- Pocket Volume（grid-based）、Ligand Fragmenter
- 前端：Executive Summary、Evidence Gap Analysis、"Why?" 按钮、定性标签（Strong/Moderate/Weak ⚠ heuristic）
- 生物科技加载动画（DNA 螺旋 + 粒子 + 轨道环）

## V3 — 推理引擎重构（已完成）

从 `+0.06` heuristic 升级为结构语义 + 知识 + 因果图 + 校准管线。

### P0：移除伪精确分数（已完成）
- CalibrationStatus（HEURISTIC/CALIBRATED）
- QualitativeConfidence（Strong/Moderate/Weak/Insufficient）
- 前端所有百分比替换为定性标签
- Baseline 标记为 [LEGACY HEURISTIC]

### P1：Structural Context Builder（已完成）
- `context/structural_context_builder.py` — 6 维化学属性差异 + 4/6/8Å 邻域 + 配体片段化
- `context/ligand_fragmenter.py` — MK1→5 片段、MTX→3 片段
- `context/residue_role_annotator.py` — 9 种功能角色 + 5 家族催化残基库
- **关键验证**：V82A（体积减小、无极性变化）vs L22Y（体积增大+极性+芳香性+HBD+HBA）被正确区分为完全不同的机制

### P2：Knowledge Layer（已完成）
- `knowledge/entity_normalizer.py` — Protein/Mutation/Ligand 实体 + 6 级证据适用性
- `knowledge/evidence_ranker.py` — EvidenceGrade 1-5 + MeasurementType 1-5
- `knowledge/literature_evidence.py` — 9 条 curated evidence（HIV/DHFR/EGFR）

### P3：Causal Reasoning Engine（已完成）
- `reasoning/causal_graph.py` — CausalNode/Edge/Path/Graph 数据结构
- `reasoning/mechanism_generator.py` — V82A: 7节点3路径 vs L22Y: 11节点20路径，完全不同的因果图
- 前端 Causal Mechanism Graph 可视化

### P4：Benchmark & Calibration（已完成）
- `benchmarks/schemas.py` — 6 样本 pilot benchmark
- `calibration/feature_schema.py` — 23 维特征向量
- `calibration/calibrator.py` — Domain-knowledge logistic regression
- `calibration/evaluation.py` — AUROC/Brier/ECE + leave-one-group-out split

### P5a：轻量准备层（已完成）
- `schemas/ensemble.py` — 多构象/ensemble 输入
- `schemas/external_data.py` — ΔΔG/Ki/Kd/IC50 外部数据导入
- `schemas/plugin_interface.py` — 7 个预注册插件接口（FoldX/Rosetta/MMGBSA 等）
- `schemas/inputs.py` — `parse_multi_mutations()` 多点突变解析

### 数据管线（已完成）
- `datasets/schemas.py` — MutationLigandPair（37 字段、6 验证规则）
- `datasets/unit_normalizer.py` — Ki/Kd→µM、ΔΔG 计算
- `datasets/residue_mapper.py` — UniProt↔PDB 编号映射
- `datasets/pair_builder.py` — 严格 WT-Mutant 配对逻辑
- `datasets/deduplicator.py` — 去重 + 背景突变检查
- `datasets/quality_control.py` — DatasetQCReport
- `datasets/review_export.py` — CSV/JSON 审核导出
- `datasets/golden_cases.py` — **118 个手动整理的金案例**
- `datasets/expansion.py` — 数据集扩张审计
- `calibration/build_feature_matrix.py` — 特征矩阵构建
- `calibration/audit_features.py` — 数据审计（缺失率/分布/相关性）
- `calibration/identity_audit.py` — Identity baseline + within/cross-family 评估
- `calibration/validity_audit.py` — 完整有效性审计

### Identity Audit 核心结论
- Protein-family-only baseline MCC = 0.000（已解除 confounding）
- Identity-blinded MCC = 0.000（跨 8 家族 118 案例）
- Cross-family mean MCC = -0.052
- **科学结论**：通用结构特征无法跨蛋白家族预测突变效应方向。正确方向应是家族内特异性预测。

---

## 文件清单

```
src/psf_reasoner/
├── context/                    # V3 P1
│   ├── structural_context_builder.py
│   ├── ligand_fragmenter.py
│   └── residue_role_annotator.py
├── knowledge/                  # V3 P2
│   ├── entity_normalizer.py
│   ├── evidence_ranker.py
│   └── literature_evidence.py
├── reasoning/
│   ├── causal_graph.py         # V3 P3
│   ├── mechanism_generator.py  # V3 P3
│   ├── baseline.py             # [LEGACY HEURISTIC]
│   └── ...
├── calibration/                # V3 P4 + Pilot
│   ├── feature_schema.py
│   ├── calibrator.py
│   ├── evaluation.py
│   ├── build_feature_matrix.py
│   ├── audit_features.py
│   ├── train_pilot.py
│   ├── grouped_cv.py
│   ├── ablation.py
│   ├── identity_audit.py
│   ├── validity_audit.py
│   └── model_card.py
├── datasets/                   # Data Pipeline
│   ├── schemas.py
│   ├── unit_normalizer.py
│   ├── residue_mapper.py
│   ├── pair_builder.py
│   ├── deduplicator.py
│   ├── quality_control.py
│   ├── review_export.py
│   ├── golden_cases.py         # 118 cases
│   └── expansion.py
├── benchmarks/
│   └── schemas.py
├── schemas/
│   ├── common.py               # CalibrationStatus, QualitativeConfidence, ScoreBreakdown
│   ├── v3_task.py
│   ├── ensemble.py
│   ├── external_data.py
│   ├── plugin_interface.py
│   ├── sensitivity.py
│   └── ...
├── physical/
│   ├── structure_qc.py
│   ├── pocket_volume.py
│   └── advanced_metrics.py
└── api/
    └── static/
        ├── index.html          # v4 UI
        ├── app.js              # V3 rendering + qualitative labels
        └── styles.css          # v4 design system

docs/
├── V2-ROADMAP.md
└── V3-ROADMAP.md
```

---

## 当前数据集状态（2026-07-21）

| Family | Total | Decrease | Neutral | Increase |
|--------|-------|----------|---------|----------|
| HIV-1 Protease | 25 | 10 | 13 | 2 |
| DHFR | 16 | 5 | 9 | 2 |
| TEM-1 β-lactamase | 16 | 3 | 8 | 5 |
| Bovine Trypsin | 16 | 5 | 11 | 0 |
| EGFR Kinase | 6 | 3 | 1 | 2 |
| ABL1 Kinase | 10 | 8 | 2 | 0 |
| SARS-CoV-2 Mpro | 16 | 6 | 10 | 0 |
| Influenza Neuraminidase | 13 | 5 | 8 | 0 |
| **Total** | **118** | **45** | **62** | **11** |

结构覆盖率：89%

---

## 测试状态

116 passed, 0 failed（非 LLM）
