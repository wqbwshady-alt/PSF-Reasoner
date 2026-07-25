# PSF-Reasoner V2 Development Roadmap

> 基于多轮讨论整理，2026-07-14

## 定位升级

PSF-Reasoner 不应定位为**蛋白质结构分析工具**（Protein Structure Analysis Tool），而应定位为**基于多层证据链的蛋白质结构机制推理平台**（Evidence-Driven Protein Structure Mechanism Reasoning Platform）。

## 核心推理链（V2）

```
Mutation
    │
    ▼
Physical Evidence（客观计算）
    │
    ▼
Evidence-supported Mechanisms（证据直接支持）
    │
    ▼
Functional Hypotheses（功能假设）
    │
    ▼
Consistency & Evidence Integration（证据整合与一致性）
    │
    ▼
Evidence Gap Analysis（缺失证据分析）
    │
    ▼
Validation Roadmap（验证路线）
    │
    ▼
Final Executive Summary（最终科研结论）
```

---

## 第一部分：Physical Evidence（物理证据层）

当前覆盖已较完整，不需大量新增指标。重点改进：

### ① Structure Pair QC（最高优先级）
所有 WT/Mutant 比较之前必须增加 Structure Pair Quality Control：
- PDB 信息、Resolution
- Chain mapping、Ligand mapping
- Background mutations、Missing residues、Missing atoms
- Occupancy、Alternate locations
- RMSD、Pocket RMSD、Ligand RMSD

输出分级：**Comparable / Partially Comparable / Poorly Comparable**

### ② Cutoff Sensitivity
对 Contact、Hydrophobic、Network、Salt Bridge 增加 cutoff 敏感性分析（3.5/4.0/4.5/5.0 Å），输出：**Robust / Threshold-sensitive / Unstable**

### ③ SASA Normalization
增加 Relative SASA、Normalized SASA、Backbone SASA、Side-chain SASA、Ligand burial

### ④ Pocket Geometry
实现真正的 Pocket Volume、Shape Complementarity、Cavity/Void Volume、Buried Surface Area

### ⑤ Interaction Provenance
所有 Interaction 可展开显示：原子、距离、Cutoff、计算方式、来源

---

## 第二部分：Mechanism Layer（最大修改）

### ① Mechanism 拆层
- **Evidence-supported Mechanisms**：Pocket Packing、Residue Network、Contact Geometry（直接来自 Physical Evidence）
- **Hypothesized Mechanisms**：Ligand Anchoring、Water Network、Affinity Reduction、Resistance（属于 Hypothesis）

### ② 删除重复机制（如 Pocket Packing / Loss of Pocket Packing）

### ③ 每个 Mechanism 增加 Evidence Graph
展示支持证据 ✅、缺失证据 ⬜、冲突证据，而非单一百分比

### ④ 增加 Contradictory Evidence
不仅展示支持，还要展示反对该机制的证据

---

## 第三部分：Functional Layer

用 **Support Coverage** 替代百分比：
- 当前证据覆盖（进度条）
- 缺失项清单（MMGBSA、Ki、IC50、ΔΔG 等）

---

## 第四部分：Consistency Layer

- 92% → **Pathway Agreement Score**（非 Confidence）
- 增加 Agreement Detail：Physical / Functional / Phenotype 分别展示

---

## 第五部分：Validation Layer

升级为 **Validation Roadmap**：
- Priority 1–5 分层（Contact Occupancy → Pocket Volume → MMGBSA/FoldX → MD → Experiment）

---

## 第六部分：新增页面 — Evidence Gap Analysis

每个机制展示 Current Evidence 覆盖 + Missing 清单，形成闭环

---

## 第七部分：统一评分体系

| 旧 | 新 |
|---|---|
| 89% / 92% / 66% | Mechanism Support Score |
| Confidence | Evidence Coverage |
| | Agreement Score |
| | Validation Priority |

---

## 第八部分：Explainability

增加 "Why?" 按钮，展开证据链推理路径

---

## 第九部分：Executive Summary

综合报告页：Strongly/Moderately/Weakly/Unsupported 分级 + Functional Hypothesis + Next Validation

---

## 第十部分：新增算法层（后期）

- **Dynamic Layer**：Contact Occupancy、Distance Distribution、HBond Lifetime、Water Residence、RMSF
- **Energy Layer**：MMGBSA、FoldX ΔΔG、Rosetta ΔΔG
- **Pocket Layer**：Real Pocket Volume、Shape Complementarity、Void Analysis
- **Experimental Layer**：Ki、IC50、Catalytic Activity

---

## 第十一部分：UI 统一规范

每张卡片标注 Evidence Level：
- 🟢 Direct Computation
- 🟡 Indirect Evidence
- 🟠 Proxy
- 🔴 Hypothesis
- ⚪ Missing Evidence

每张卡片可展开：Evidence、Formula、Parameters、Raw Values、Calculation、Source、Limitation

---

## 核心原则

**不是继续堆更多特征，而是把已有证据组织成一条真正透明、可追溯、可验证的科研推理链。**
