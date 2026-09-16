# PSF-Reasoner 案例库（Case Registry）

本目录存放**经核实、可复现、可展示**的突变机制案例，与
`datasets/golden_cases.py`（校准数据候选集）严格分离：

- `cases/*.json` —— 统一格式的案例记录（见下方 schema）。
- `cases/teaching/*.json` —— 教学案例（含背景、学习目标、任务、分步参考解释）。
- 案例记录中的 `review_status` 是**人工/证据核验后的真实状态**，与
  `datasets/schemas.py` 中 `ReviewStatus.ACCEPTED`（仅代表数据条目曾被打标签）含义不同。

## 案例记录必需字段（每个案例一个 JSON 对象）

```jsonc
{
  "case_id": "hiv1-v82a-mk1",          // 稳定标识
  "title": "HIV-1 蛋白酶 V82A 对 MK1 类抑制剂的结合影响",
  "protein": {
    "name": "HIV-1 protease",
    "species": "Human immunodeficiency virus 1",
    "uniprot_accession": "P03367",
    "pdb_id_wt": "1SDT",
    "pdb_id_mutant": "1SDV"
  },
  "mutation": {
    "notation": "V82A",                 // 野生型一字母 → 突变型
    "wt_residue": "V",
    "mutant_residue": "A",
    "chain": "A",
    "uniprot_position": 82,
    "pdb_position": 82,
    "mapping_note": "UniProt 编号与 PDB 编号一致的依据"
  },
  "structures": {
    "wild_type": {
      "pdb_id": "1SDT", "file": "examples/data/1sdt.cif",
      "method": "X-ray", "resolution_a": 1.3,
      "ligands": [{"id": "MK1", "role": "inhibitor"}],
      "background_mutations": [],        // 相对参考序列的额外突变
      "quality_notes": ""
    },
    "mutant": { /* 同上 */ },
    "pair_comparability": {             // 结构可比性结论
      "grade": "comparable",            // comparable | partially | poorly
      "notes": ""
    }
  },
  "functional_measurement": {
    "assay_type": "Ki",
    "wt_value": 1.0, "mutant_value": 5.0,
    "value_unit": "fold_Ki",            // 记录原始单位，不跨实验混合
    "conditions": "",                   // pH、温度、缓冲液
    "fold_change": 5.0,
    "direction": "affinity_decrease",
    "phenotype": "drug_resistance"
  },
  "provenance": {
    "pmid": "15066177",
    "doi": "",
    "source_location": "Table X / Figure Y",  // 支持该结论的原文位置
    "quote_or_note": "原文数据摘录或转述说明"
  },
  "mechanism": {
    "conclusion": "V82A 缩小 S1 口袋侧链体积，削弱疏水接触……",
    "supporting_evidence": [],           // 结构证据 + 文献证据条目
    "conflicting_evidence": [],
    "missing_evidence": []               // 尚缺的证据（如无氢键缺失的原子级证据）
  },
  "review": {
    "status": "verified",               // verified | pending_verification | excluded
    "reviewed_by": "",
    "review_date": "",
    "notes": ""
  },
  "usage": {
    "demo_ready": true,                 // 可用于完整流程演示
    "teaching_ready": true,             // 可用于教学展示
    "quantitative_eval_ready": false    // 可用于定量评估/校准（默认 false，需独立论证）
  }
}
```

## 写入规则（不可违反）

1. 每项实验数值必须能在所列 PMID/DOI 的表格、图或正文中定位；无法定位的
   数值一律删除或标注 `"status": "pending_verification"`，**禁止编造**。
2. `usage.quantitative_eval_ready` 默认 `false`。只有经过证据核验、结构与
   配体完全匹配、且与校准评估的独立性要求不冲突的案例才能置 `true`。
3. 结构文件中的实际配体必须与 `functional_measurement` 的配体一致；不一致的
   案例要么排除，要么在 `pair_comparability.grade = "poorly"` 中明示并禁止用于
   定量评估。
4. 教学案例的"分步参考解释"必须区分：已知事实（实验/结构直接观测）、计算推断
   （本平台可复现的计算结果）、待验证假设（文献机制假说）。
