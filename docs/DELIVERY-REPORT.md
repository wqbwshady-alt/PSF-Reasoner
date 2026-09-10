# PSF-Reasoner 交付报告（2026-09-10）

> 本轮范围：证据审计 → 平台打通 → 首个可信案例 → 教学案例。科研承诺仅覆盖
> "单蛋白体系内、单点突变对配体结合的结构机制解释"，未新增疾病风险、通用
> 准确率或复杂多点突变预测的承诺。

## 一、实际代码修改与变更说明

### 数据完整性（隔离错误证据）

| 文件 | 修改 |
|---|---|
| `datasets/golden_cases.py` | **整体重建**。原 118 条中 103 条引用无关 PMID、50 条为配额填充编造数据。现仅 9 条 `ACCEPTED`（每条 PMID/方向/数值均经核实），5 条 `PENDING`（来源已更正、数值待全文复核），其余全部 `REJECTED` 并注明理由。新增 `load_verified_cases()`。 |
| `knowledge/literature_evidence.py` | 仅保留已核实条目；**修复空键部分匹配 bug**（此前任何未知蛋白都会错误附加 HIV 文献）；更正/删除错误 PMID 与不存在的 DOI（含 `10.1126/science.2548654`）。 |
| `benchmarks/hiv1_protease/v1.2.0.json`、`pilot.json` | 修正 **1SDU/1SDV 对调**错误（V82A→1SDV，L90M→1SDU）；Mahalingam 1999 来源 3 案例与绝对值未核实项标记 `excluded_from_calibration`。 |
| `benchmarks/schemas.py`（src） | 试点基准改为 5 个已核实样本（log10-fold 标签），移除错误 PMID 样本。 |
| `examples/data/1sdu.cif` | **新增** L90M + MK1 突变结构（RCSB 下载，data_1SDU 验证）。 |
| `calibration/build_feature_matrix.py` | 移除 **ΔΔG→volume_delta 标签泄漏**；配体不匹配改为记录 build error（原为静默使用任意配体）；改用 `load_verified_cases()`。 |
| `calibration/identity_audit.py` | 改用已核实案例。 |
| `datasets/expansion.py` | 删除配额制框架（编造数据的制度根源），改为基于审核状态的盘点。 |
| `pilot_validity_audit/README.md` | 标注全部旧产物为不可再引用的历史快照（样本已重建，数字失效）。 |

### 平台打通（上传→分析→对比→解释→定位→导出）

| 文件 | 修改 |
|---|---|
| `api/app.py` | `/v3/analyze` 整合：蛋白身份取自结构文件头部（非配体猜测）、传入上下文构建器/机制生成器/文献查询；新增 `/v3/analyze-upload`（multipart 主入口）、`/export/{report_id}?format=json|csv|pymol`；`/structure` 可服务内置示例结构（原 403）；`/v3/status` 不再每次请求现场训练。 |
| `physical/identity.py` | **新增**：从 PDB/mmCIF 头部提取蛋白身份与家族提示，无法识别时返回空（绝不猜测）。 |
| `api/exports.py` | **新增**：JSON/CSV/PyMOL 三种真实导出，内容与页面一致。 |
| `bootstrap.py` | FoldX 模型器经 `PSF_FOLDX=1` 接线（未安装时诚实回退截断模型器）。 |
| `api/static/index.html`、`app.js` | **重建**：真实上传表单接入 `/v3/analyze-upload`；WT/Mutant 视图真正切换模型；点击"定位突变位点/配体/4Å邻域"高亮真实残基（数据来自后端 evidence_localization，不再硬编码 82）；导出按钮；校准徽章白名单（只有精确值 `calibrated` 才显示 CALIBRATED）；渲染 Limitations；诚实文案。 |
| `physical/calibration.py` | 文案修正（1SDT/1SDV 为 WT/V82A 对；标注 3.3 倍来源）。 |

### 测试与防回归

| 文件 | 修改 |
|---|---|
| `tests/conftest.py` | autouse fixture 隔离 `PSF_LLM`/云/持久化环境变量——此前同一测试套件在有无环境变量时走完全不同的代码路径（慢 5070 倍，且 LLM 输出不可复现）。 |
| `tests/test_data_integrity.py` | **新增**：错误 PMID 黑名单、已核实 PMID 白名单、拒绝理由必填、bulk 填充不得 ACCEPTED、旗舰案例字段、结构对配体匹配（gemmi 实解）、DRV/MK1 不匹配案例必须 REJECTED、基准 JSON 结构 ID。 |
| `tests/test_literature_integrity.py` | **新增**：空/未知家族返回空、HIV 文献只含已核实 PMID、空家族因果图不含文献证据。 |
| `tests/test_feature_matrix_integrity.py` | **新增**：ΔΔG 不得泄漏进特征、配体不匹配记录 build error、已核实结构对正常构建。 |
| `tests/test_v3_api.py` | **新增**：身份来自结构、定位数据正确、三种导出往返、404/400、multipart 上传、示例结构可服务。 |
| `tests/test_teaching_cases.py` | **新增**：教学案例 JSON 的 schema/审核状态/证据分级/结构文件校验。 |

### 文档修正

`docs/PROJECT-STATE.md`（118 案例声明加审计横幅）、`docs/interaction-validation.md`（PLIP PMID 33950225→33950214；1SDV 是 V82A 不是 L90M）、`progress.md`（"全部核实"声明更正）、`pilot.md`（作者 Sayer→Clemente）。

## 二、案例证据表

详见 `docs/EVIDENCE-REVIEW.md`（逐 PMID/DOI/结构核对，全部附在线链接）与
`src/psf_reasoner/datasets/golden_cases.py`。核心结论：

**已核实（ACCEPTED，9 条）**：HIV V82A/MK1（3.3×）、HIV L90M/MK1（0.16×）、
HIV G48V/SQV（86×）、I50V/DRV（31×）、I54V/SQV（15×）、I54M/SQV（5×）、
D30N/NFV（2–6×）、DHFR L22F/MTX（88×）、DHFR F31R/MTX（ΔΔG 2.1）。

**待人工复核（需全文 PDF，13 项）**：见 EVIDENCE-REVIEW 表 4，主要包括
Mahalingam 2004/1999 的绝对值与 Table II、EGFR T790M/C797S 与 ABL1 倍数
的原始出处、DHFR L22Y/F31S 的归属、TEM-1 与胰蛋白酶/Mpro/神经氨酸酶案例
的从零重建（候选来源已列出）。

## 三、首个完整案例（可运行、可复现）

**HIV-1 protease V82A + MK1（indinavir）**：结构对 1SDT/1SDV（同晶形、同
配体、仅第 82 位 V→A 不同，已逐位比对核实）；Ki 3.3 倍（Mahalingam 2004
摘要）；机制=侧链截短 → S1 口袋疏水堆积丢失 → 配体锚定减弱。

已验证的完整流程（全部实际运行）：
1. 上传/选择 1sdt.cif + 1sdv.cif，配体 MK1，突变 V82A，链 A
2. 结构对比：QC（1.30/1.40 Å）、距离证据（WT 最近 3.782 Å，与独立
   gemmi 复算一致）、接触/SASA/相互作用变化
3. 机制解释：蛋白身份来自结构头部（HIV-1_PROTEASE）→ 3 条已核实文献 →
   7 节点因果图（竞争路径 + 不确定性）
4. 三维证据定位：突变位点 A:VAL82、配体 MK1、4Å 邻域
   PRO81/ASN83/THR80/ILE84（真实数据，反向模式不再捏造 82 号）
5. 导出：JSON（完整报告）、CSV（53 行证据表）、PyMOL 脚本，均验证可打开
6. 确定性：同一输入两次 CLI 运行除 `generated_at` 外逐字节一致

## 四、教学案例（5 个，机制互异）

见 `cases/teaching/README.md` 与 5 个案例 JSON。每个案例含背景、学习目标、
观察任务、思考题、分步参考解释（每步标注 fact/computed/hypothesis）、
已知事实/计算推断/待验证假设三分。全部 `quantitative_eval_ready=false`，
教学答案与科研分析模式严格分离。

## 五、测试与复现记录

- **156 个测试：155 通过 / 1 跳过**（Python 3.14.7，全新 venv 安装）。
- 完整记录：`docs/VERIFICATION-RECORD.md`（含修订指纹、测试质量分级）。
- 复现命令（干净环境）：
  ```
  python -m venv .venv && pip install -e '.[dev]'
  pytest                    # 155 passed, 1 skipped
  psf analyze --structure examples/data/1sdt.cif \
      --mutant-structure examples/data/1sdv.cif \
      --ligand MK1 --mutation V82A --chain A --phenotype drug_resistance
  uvicorn psf_reasoner.api.app:app  # 工作台 http://127.0.0.1:8000
  ```
- 已知限制：`PSF_LLM=1` 时 LLM 推理不具确定性（两次运行 235 处字段差异，
  已记录）；测试环境已隔离该变量，默认基线完全确定。

## 六、面向学生的简明操作说明

1. 启动：`uvicorn psf_reasoner.api.app:app --reload`，浏览器打开
   http://127.0.0.1:8000。
2. 首次体验：直接点「V82A 示例（配对结构）」，阅读报告各分区，再点
   「定位突变位点/配体/4Å邻域」看 3D 高亮，最后试三种导出。
3. 自己的案例：左侧选择 WT 文件（必填）、突变体文件（可选）、填配体
   ID（PDB 三字母代码，如 MK1/MTX）、突变（如 V82A）、链；选模式后点
   「开始分析」。
4. 没有突变体结构时：平台只给 WT 结构证据并明确说明"未计算结构变化"，
   不会编造——这正是 G48V 教学案例要演示的行为。
5. 教学案例：`cases/teaching/` 下 5 个 JSON，先做观察任务与思考题，再看
   分步参考解释。

## 七、已完成 / 未完成 / 受阻事项

**已完成**：证据审计与错误证据隔离；上传→分析→对比→解释→3D 定位→导出
全链路；首个可信案例端到端验证；5 个教学案例；回归测试；文档修正。

**未完成（明确声明，未伪装为完成）**：
- 交互引擎仍未通过 PLIP/Arpeggio 等外部工具的系统验证（已有单向对比，
  H-bond 系统性低估、疏水接触高估）；
- 校准层仍是启发式：线上 `calibration_status` 恒为 HEURISTIC，报告明确
  标注"未校准"，不展示百分比概率；
- FoldX 仅按需接线（PSF_FOLDX=1 且本机安装），默认仍是截断式局部建模；
- 局部相互作用评分不是 ΔΔG，前端已加说明；
- 反向模式（无突变）的 3D 定位只高亮配体与口袋，不做机制级高亮；
- B-factor、保守性、RCSB 在线获取未实现（按优先级延后）。

**受阻事项**：Mahalingam 2004/1999 全文付费墙（13 项待人工复核清单）；
EGFR/ABL1 等家族的可靠倍数来源需要全文检索——已给出候选 PMID，需要
人工获取 PDF。

## 八、下一阶段科研验证计划（建议顺序）

1. 人工复核 EVIDENCE-REVIEW 表 4 的 13 项（取全文 PDF），把 PENDING
   案例转为 ACCEPTED。
2. 交互引擎外部验证：在已核实结构对上跑 PLIP/Arpeggio，按
   `docs/interaction-validation.md` 的参数修正流程收敛 H-bond/疏水判据。
3. 扩充已核实案例（优先 Liu 2008 体系内已核实文献），**不设配额**，
   每条数值必须落到 Table/Figure。
4. 达到 ≥30 条已核实案例、≥2 蛋白家族后再评估校准门槛
   （V3-ROADMAP 六条 gate），此前所有置信度保持"未校准"。
5. 教学案例的网页端教学模式页面（分步揭示、任务清单），与科研模式
   入口分离。
