# PSF-Reasoner V3：推理引擎重构方案

> 2026-07-16

## 核心判断

- V1 已完成工程管线
- V2 已完成信息组织、证据追溯和前端表达
- 当前瓶颈不是物理指标不足，而是推理引擎依赖未经校准的 heuristic
- V3 应重做引擎，不是继续加页面或堆特征
- V3 不能简单变成"让 LLM 自由读取 PDB 和文献"——科学可验证性仍然不足

**V3 应构建为：结构语义 + 外部知识 + 因果机制图 + 校准模型 + LLM解释 共同驱动的推理系统。**

---

## 一、立即停止未经校准的伪精确分数

当前 `side_chain_smaller -> confidence += 0.06` 等权重没有实验或统计依据。

在模型校准完成前：
- 删除或停用未经校准的百分比
- 不再展示 89%、66%、92% 这类容易被理解为概率的数字
- 临时改为：strong/moderate/weak, direct/indirect/hypothetical, evidence coverage, pathway agreement
- 保留完整 ScoreBreakdown，但明确标记为 heuristic，不用于定量结论

---

## 二、Structural Context Builder（P1）

不要让 LLM 直接阅读几千行 PDB 原子坐标。由确定性程序先把结构转换为结构化、可检查的"结构语义上下文"。

输出统一 JSON，至少包括：

1. 基础身份与映射：protein name, UniProt accession, organism, PDB ID, chain, mutation, residue-number mapping, ligand identity/role, WT/mutant mapping, QC, background mutations
2. 突变位点功能背景：催化位点/配体结合口袋/底物结合位点/二聚化界面/变构位点/疏水核心/表面区域, 位点保守性, UniProt feature, PDB SITE, hotspot 状态
3. 多尺度局部环境：4Å/6Å/8Å 邻域残基列表, 二级结构, 主链/侧链方向, residue-residue/ligand/water contacts, pocket membership, local network role
4. 配体化学语义：环系, 芳香片段, 疏水片段, 带电基团, 氢键供体/受体区域, 可旋转尾部, 药效团（如 MTX → pteridine ring + para-aminobenzoate + glutamate tail）
5. WT/mutant 精确差异：新增/丢失的化学能力, 体积/极性/电荷/芳香性变化, H-bond 供体/受体变化, rotamer change, 原子对变化, 局部几何/相互作用/pocket/network 变化, 不确定性

---

## 三、Knowledge Retrieval and Normalization（P2）

1. 数据源：UniProt, PDB, PubMed, ClinVar, BindingDB, ChEMBL, ProTherm/ThermoMutDB, SKEMPI, MaveDB
2. 实体标准化：每条文献知识映射到 protein accession, isoform, organism, residue numbering, mutation, PDB chain, ligand, experimental system, phenotype, measurement type
3. 文献证据分级：Direct mutation evidence → Same-site substitution → Nearby-site → Same-protein mechanistic → Family-level analogy → General biochemical prior
4. 每条证据保留 PMID/DOI, 原始结论, 实验方法, 测量值, 方向, 样本背景, 适用性, 证据等级, 不确定性

---

## 四、Competing Causal Mechanism Graph（P3）

标准因果层级：Mutation property change → Local geometry change → Interaction change → Pocket/conformational change → Binding or catalytic consequence → Phenotype

系统应生成多条竞争路径（以 DHFR L22Y 为例）：
- 体积增大 → 空间重排/碰撞/配体位移
- 芳香环引入 → 可能的 π 相互作用或疏水堆积
- 羟基引入 → 可能的直接氢键 or 水介导氢键
- Rotamer 和局部构象变化 → 邻近残基重组织

每条路径分别用几何、原子类型、接触变化、文献、动态证据、能量证据、反对证据验证。

---

## 五、Calibrated Prediction Layer（P4）

- V3 第一阶段只做：预测蛋白–小分子结合变化的方向与幅度（ΔΔG_binding, log fold-change Kd/Ki）
- 耐药表型放到后续（依赖催化活性保留、表达、细胞环境等）
- 模型：logistic regression → random forest → gradient boosting → Bayesian model
- 输入：物理证据 + Structural Context + 位点功能 + 配体化学 + 文献证据等级 + QC + missingness indicators
- 输出：effect direction, predicted magnitude, calibrated probability, confidence interval, applicability domain, OOD warning
- 评估：mutation-level split, protein-level split, protein-family split, external test set

---

## 六、Benchmark 设计

Pilot: 100-300 高质量案例，2-3 蛋白体系（HIV protease, DHFR, β-lactamase）
Expanded: EGFR, BCR-ABL, KRAS, SARS-CoV-2 Mpro, influenza neuraminidase, 细菌耐药酶

每条样本：WT structure, mutant structure/modeled, protein, mutation, ligand, assay type, experimental value, experimental condition, literature source, data quality, train/test grouping key

---

## 七、LLM 的正确角色

LLM 适合：根据结构化证据生成竞争机制、比较机制、结合文献解释位点特异性、生成引用完整的科研叙述、提出验证实验

LLM 不应：直接解析原子坐标、计算距离/能量、决定原子类型/质子化状态、发明 confidence、把相似文献当直接证据、独立给出最终定量预测

LLM 输出严格 schema，不是自由散文。

---

## 八、多点突变实施顺序

1. 单点突变机制推理稳定
2. 跨多个蛋白完成外部验证
3. 支持同背景下双突变
4. 计算非加和项
5. 建立 epistasis 模块
6. 推广复杂多突变

Effect(A+B) ≠ Effect(A) + Effect(B)：需考虑 synergistic/antagonistic/compensatory effects, conformational coupling, long-range allostery, background dependence

---

## 九、推荐工程架构

```
context/          structural_context_builder, ligand_fragmenter, residue_role_annotator, numbering_mapper
knowledge/        retriever, entity_normalizer, literature_evidence_extractor, evidence_ranker, citation_store
reasoning/        causal_graph, mechanism_generator, mechanism_ranker, contradiction_checker, llm_reasoner
calibration/      dataset_builder, feature_schema, train_baseline, calibrator, applicability_domain, evaluation
benchmarks/       schemas, loaders, splits, metrics
```

保留 V1/V2 的 parser, physical evidence calculators, reports, API, frontend, EvidenceGraph, Gap Analysis, QC, provenance。把 `reasoning/baseline.py` 降级为 legacy heuristic baseline，仅用于与 V3 做对照实验。

---

## 十、开发优先级

| 优先级 | 内容 |
|--------|------|
| P0 | 停止展示未校准百分比；baseline 标记为 legacy；定义 V3 统一 schema；确定首个预测任务和标签；确定首个 benchmark 蛋白体系 |
| P1 | Structural Context Builder |
| P2 | Knowledge Layer |
| P3 | Causal Reasoning Engine |
| P4 | Benchmark 与校准 |
| P5 | 动态、能量与多点突变 |

---

## 十一、V3 完成标准

1. 推理不再依赖任意 +0.06 权重
2. 每个机制都建立在结构语义而不是单一属性模板上
3. 能区分 L22Y 的体积、芳香性、羟基和新氢键等竞争机制
4. 每条文献知识都有实体映射和引用
5. 能区分直接突变证据、同位点证据和家族类比
6. 机制以因果图表达，包含支持、冲突和缺失证据
7. LLM 不负责生成定量置信度
8. 数值预测来自经过验证和校准的模型
9. 评估使用 protein-level 或 family-level split
10. 系统能报告适用域和 OOD 风险
11. 功能后果与耐药表型严格分开
12. baseline heuristic 只作为比较基线存在
13. 至少在一个外部 benchmark 上证明优于 heuristic
14. 输出结果可复现、可引用、可审计

---

## 最终定位

**V1 搭建了骨架，V2 装好了仪表盘，V3 需要更换发动机：从 pattern matching 升级为可验证、可校准、可追溯的知识与因果推理系统。**

```
Raw structure → Physical evidence → Structural Context Builder
→ Knowledge retrieval & normalization → Competing causal mechanism graph
→ Evidence-based mechanism ranking → Calibrated prediction
→ Citation-grounded explanation → Validation roadmap
```
