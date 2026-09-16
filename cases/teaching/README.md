# 教学案例库（Teaching Cases）

5 个经过证据审计的教学案例，机制类型互不相同：

| 案例 | 机制类型 | 结构对 | 关键教学点 |
|---|---|---|---|
| `hiv1-v82a-mk1` | 侧链截短 → S1 口袋疏水堆积丢失 | ✅ 1SDT/1SDV（已核实） | 首个完整案例；证据链全程可复现 |
| `hiv1-l90m-mk1` | 二聚体界面突变 → 反直觉的**超敏感**（0.16×） | ✅ 1SDT/1SDU（已核实） | 突变位置决定机制；"耐药相关"≠"结合减弱" |
| `dhfr-l22y-mtx` | 侧链增大+引入芳香/极性 → 蝶啶口袋位阻 | ✅ 1U72/1DLS（结构已核实，数值待复核） | 与 V82A 方向相反的化学变化 |
| `hiv1-g48v-sqv` | flap 区突变，86× Ki（数值已核实） | ❌ 无突变结构 | 证据不足时平台必须诚实说明，不得伪造结构变化 |
| `dhfr-f31r-mtx` | 锚定残基替换，ΔΔG=2.1 kcal/mol（已核实） | ❌ 无突变结构 | ΔΔG 与倍数的换算；能量值≠机制证据 |

## 使用方式

1. 按每个案例 JSON 中 `teaching.run_instructions` 的说明在工作台或 CLI 运行。
2. 教学时先让学生做 `observation_tasks` 与 `thinking_questions`，
   再看 `stepwise_explanation`（分步参考解释）——**顺序不要反**。
3. 每个解释步骤都带 `evidence_status`：
   - `fact`：实验测量或结构直接观测（可追溯 PMID/PDB）
   - `computed`：本平台可复现的计算结果
   - `hypothesis`：文献假说或推理，**未经本平台验证**

## 与科研分析模式的区分（重要）

- 本目录的 `teaching.*` 内容是**已知答案**，只用于教学展示。
- 科研分析模式（工作台上传任意结构）不读取这些答案。
- 严禁把教学案例的已知实验值作为"预测输入"再用来评价预测效果——
  这是标签泄漏。案例 JSON 中 `usage.quantitative_eval_ready` 全部为
  `false`，只有满足 docs/EVIDENCE-REVIEW.md 表 4 人工复核后的案例才
  可能改为 `true`。

## 数据可靠性

- 每个案例的 `provenance`（PMID/DOI/Table 位置）与 `review.status`
  来自 2026-09-10 的独立证据审计（docs/EVIDENCE-REVIEW.md）。
- `review.status = verified` 表示结构与数值均经过核实；
  `pending_verification` 表示结构或方向已核实但精确数值待全文复核。
- 结构文件位于 `examples/data/`，其身份（突变、配体）均已用
  gemmi 本地解析 + RCSB API 双向确认。
