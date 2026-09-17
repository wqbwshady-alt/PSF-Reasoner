# PSF-Reasoner 平台端到端流程审查报告

- 审查日期：2026-09-10
- 审查范围：`src/psf_reasoner/` 后端全部交付链路 + `api/static/` 前端 + `docs/` 声明
- 审查方法：静态代码追踪（调用链 grep + 逐文件阅读），**未修改任何代码**
- 环境说明：本机 `python3` 无 `gemmi`，无法实跑 API；所有结论均来自代码与调用图，关键推断（如空蛋白名查文献的 fallback）已用纯逻辑复现验证

---

## 总体结论

### 完整链路图

```
┌─ 前端 (api/static/index.html + app.js) ──────────────────────────────────┐
│                                                                          │
│  [开始分析 #submit-analysis]  ──✖ 死按钮（无监听器）                     │
│  [侧栏输入: 文件/配体/突变/链/表型] ──✖ app.js 零引用                     │
│  <form id="analysis-form">  ──✖ index.html 中不存在该元素                │
│      └─ app.js:445 $("...")?.addEventListener 因 ?. 静默失效             │
│         └─ /analyze-upload, /reverse-upload  ──✖ 不可达                  │
│                                                                          │
│  [V82A 示例 #run-example]   ──✔──> POST /analyze      (硬编码 payload)   │
│  [V3 因果推理 #run-v3-example] ──✔──> POST /v3/analyze (硬编码 payload)  │
│  [WT/Mutant 视图 tab]       ──✖ 惰性（只切 CSS class，不换模型）          │
│  [导出 JSON/CSV/PyMOL]      ──✖ 前后端均不存在                          │
│  [点击解释→3D 定位]          ──✖ 不存在                                  │
│  [RCSB ID 获取]             ──✖ 前后端均不存在                          │
└──────────────────────────────────────────────────────────────────────────┘
                    │ 仅两个硬编码示例按钮可达
                    ▼
┌─ 后端 API (api/app.py) ──────────────────────────────────────────────────┐
│                                                                          │
│  【默认链路 — 真实接通】                                                  │
│  /analyze · /forward · /reverse · /analyze-upload · /reverse-upload       │
│      └─> AnalysisRunner.run (application/runner.py:40)                    │
│          └─> AnalysisService.analyze (application/service.py:49)          │
│              ├─ StructurePreparationInspector        ✔ 真实              │
│              ├─ StructureQCProvider                  ✔ 真实(需配对结构)   │
│              ├─ CompositeEvidenceProvider × 7        ✔ 6 个真实几何计算   │
│              │   ├─ MutationProperty / Coordinate / Comparative           │
│              │   ├─ PocketNetwork / LocalEnergy      ✔                  │
│              │   ├─ HIVProteaseCalibrationProvider   ⚠ 硬编码 if 查表     │
│              │   └─ CloudEvidenceProvider            ⚠ 默认 None→返回()   │
│              ├─ BaselineForward/ReverseReasoner       ⚠ 硬编码启发式权重  │
│              └─ PSFReport (calibration_status 恒 = heuristic)             │
│                                                                          │
│  【V3 链路 — 孤立旁路，仅 1 个硬编码按钮触发】                             │
│  /v3/analyze (api/app.py:274-317)                                        │
│      ├─ 先跑一遍 V2 默认链路拿 PSFReport                                  │
│      ├─ StructuralContextBuilder.build(...)   ⚠ 未传 hint → "unknown"     │
│      ├─ MechanismGenerator.generate(ctx)      ⚠ 未传 family → 文献 bug    │
│      └─ get_evidence_summary(按配体简称猜蛋白) ⚠ 猜错→空串→HIV 文献       │
│                                                                          │
│  /v3/status (app.py:121) — 每次请求现场重训，只用于展示 MCC              │
│                                                                          │
│  【完全未接线 — 零调用者】                                                │
│  schemas/v3_task.py · datasets/pair_builder.py · datasets/review_export.py│
│  calibration/calibrator.py (DomainKnowledgeCalibrator)                    │
│  schemas/plugin_interface.py 插件注册表                                   │
│  knowledge/entity_normalizer.py 的 lookup_*/classify_* 函数               │
│  physical/modeling.py 的 FoldXMutationModeler（仅测试用）                 │
│                                                                          │
│  【不存在】                                                              │
│  导出端点 (JSON/CSV/PyMOL) · RCSB 在线获取 · 证据→残基/原子映射端点       │
└──────────────────────────────────────────────────────────────────────────┘
```

### 三句话总结

1. **默认用户流程根本没接上 V3**：`/analyze`、`/analyze-upload` 等默认端点走 `AnalysisService`，而 `StructuralContextBuilder`、`literature_evidence`、`causal_graph`、`mechanism_generator` 在 `application/` 与 `bootstrap.py` 中**完全不出现**。V3 只存在于独立的 `/v3/analyze` 旁路里。
2. **更严重的是前端**：`index.html` 里没有 `<form>` 元素，`#submit-analysis`「开始分析」按钮没有任何监听器，上传链路（`/analyze-upload`）在 UI 上**根本不可达**；侧栏所有参数输入框在 `app.js` 中引用次数为 0，所有分析跑的都是硬编码的 `1sdt.cif/1sdv.cif + MK1 + V82A` 演示数据。
3. **文档声明与实现严重脱节**：`docs/PROJECT-STATE.md` 把 V3 P1–P5a 全部标注为「已完成」，但其中至少 6 个模块零调用者；声称的「118 个金案例」实际为 44 个（且 `TODO.md` 自述「calibration-ready cases currently 2」）。

### 结论分级总览

| 必查项 | 结论 |
|---|---|
| 1. 上传到分析链路 | **部分可用**：默认链路真实但仅覆盖 V2；V3 为孤立旁路；UI 上传入口不可达 |
| 2. 导出功能 | **缺失**（前后端均无） |
| 3. 三维证据定位 | **空壳**：只有突变残基+配体高亮，残基号取自请求并含硬编码 `"82"` 兜底 |
| 4. FoldX / 插件 | **空壳**：FoldX 适配器实现真实但零接线；7 插件为纯元数据；云需外部部署 |
| 5. 校准层 | **空壳**：手工系数、零调用；训练脚本存在但不落盘、不进推理；线上仍是启发式 |
| 6. 蛋白身份识别 | **部分可用（有 bug）**：无结构来源识别，按配体简称猜测，且未知蛋白被污染为 HIV 文献 |
| 7. 结构配对校验 | **空壳**：校验函数零调用，且判据不含结构配体，原理上无法发现该类不匹配 |
| 8. 教学/科研模式 | **完全缺失** |
| 9. 上传类型 | **后端部分可用 / 前端不可达**；RCSB 在线获取前后端均无 |

---

## 1. 上传到分析的完整链路

**结论：部分可用。** 默认链路（V2/legacy）真实接通；V3 四个核心模块只在 `/v3/analyze` 中被调用，与默认服务完全隔离；前端上传入口不可达。

### 1.1 默认链路（真实接通）

调用链：

```
POST /analyze (api/app.py:175) 或 /analyze-upload (api/app.py:184)
  → _resolve_request / _store_upload (app.py:87, 342)
  → _run (app.py:332)
  → AnalysisRunner.run (application/runner.py:40)
  → AnalysisService.analyze (application/service.py:49)
```

`AnalysisService` 的实际组成（`bootstrap.py:40-77`）：

- `CompositeEvidenceProvider`（`bootstrap.py:64-72`）包了 7 个 provider：
  `MutationPropertyEvidenceProvider`、`CoordinateEvidenceProvider`、`ComparativeEvidenceProvider`、`PocketNetworkEvidenceProvider`、`LocalEnergyEvidenceProvider`、`HIVProteaseCalibrationProvider`、`CloudEvidenceProvider`
- 推理器：`BaselineForwardReasoner` / `BaselineReverseReasoner` / `BaselineConsistencyChecker`（`bootstrap.py:59-61`），仅在 `PSF_LLM=1` 时替换为 LLM 版本（`bootstrap.py:54-57, 116-138`）
- `mutation_modeler=LocalSideChainMutationModeler()`（`bootstrap.py:76`）

`AnalysisService.analyze` 的流水线（`service.py:49-145`）：结构准备 → Structure Pair QC → 证据收集 → 前向推理 → 反向推理 → 一致性检查 → 报告组装。**其中没有任何一行涉及结构上下文、知识层、因果图或机制生成器。**

报告级置信度是各 claim 置信度的算术平均（`service.py:113-118`），且 `calibration_status` 被硬编码：

- `service.py:134` `calibration_status=CalibrationStatus.HEURISTIC`

### 1.2 V3 模块未接线（关键发现）

全仓 grep 结果（`src/` + `tests/` + `cloud/`）：

| 模块 | 唯一调用点 | 是否在默认链路 |
|---|---|---|
| `context/structural_context_builder.py` | `api/app.py:287,292`（`/v3/analyze`）；`calibration/build_feature_matrix.py:18,65`（离线） | ✖ |
| `knowledge/literature_evidence.py` | `api/app.py:289`；`reasoning/mechanism_generator.py:15`；`calibration/build_feature_matrix.py:21` | ✖ |
| `reasoning/causal_graph.py` | 仅被 `reasoning/mechanism_generator.py:16` 导入 | ✖ |
| `reasoning/mechanism_generator.py` | 仅 `api/app.py:288,295` | ✖ |

即：**V3 的 P1/P2/P3 三层在默认服务中一行都没执行。** `bootstrap.py` 与 `service.py` 中不含上述任一模块的 import。

`/v3/analyze`（`app.py:274-317`）是一个独立旁路，它先跑一遍完整 V2 默认链路拿 `v2_report`（`app.py:284`），再额外算结构上下文与因果图，返回一个 `dict`（不是 `PSFReport`）。

### 1.3 CLI 同样未接 V3

`cli.py` 只有 `forward` / `reverse` / `analyze` / `batch` 四个命令（`cli.py:37,56,67,106`），全部经 `create_default_runner` 走默认链路，**没有任何 V3 命令或开关**。

### 1.4 `schemas/v3_task.py` 的用途：死代码

该文件定义了 `PredictionTask` / `TargetLabel` / `BenchmarkSystem` / `BenchmarkSampleSpec` 与三个 benchmark 阈值常量（`v3_task.py:12-95`）。

**全仓零 import**——`grep -rn "v3_task\|V3Task"` 只命中 `docs/PROJECT-STATE.md:136` 的文件清单。它既没有被 API 使用，也没有被任何测试、CLI 或校准脚本使用。其定义的 `BENCHMARK_PILOT_MINIMUM = 100`（`v3_task.py:93`）与实际数据集（44 例）也从未被比对过。

### 1.5 测试覆盖

- `grep -rn "v3" tests/` → **零结果**。`/v3/analyze`、`/v3/status` 没有任何测试。
- 触及 V3 相关模块的测试仅 `tests/test_comparison.py`（测 `FoldXMutationModeler` / `LocalSideChainMutationModeler` / `UnconfiguredMutationModeler`，`tests/test_comparison.py:131,115,104`）。
- `StructuralContextBuilder` / `MechanismGenerator` / `literature_evidence` / `causal_graph` **零测试覆盖**。

> 用户怀疑属实：默认上传流程确实没用上结构上下文、因果图和文献证据；这些只在测试/CLI 之外的一个孤立 API 端点里存在，而 CLI 里连这个端点都没有。

---

## 2. 导出功能

**结论：缺失。不是"占位按钮"，是前后端都没有实现。**

### 2.1 后端：无任何导出端点

`api/app.py` 的全部路由（穷举）：

| 行 | 路由 |
|---|---|
| `app.py:117` | `GET /health` |
| `app.py:121` | `GET /v3/status` |
| `app.py:153` | `GET /`（返回 index.html） |
| `app.py:157` | `POST /forward` |
| `app.py:166` | `POST /reverse` |
| `app.py:175` | `POST /analyze` |
| `app.py:184` | `POST /analyze-upload` |
| `app.py:210` | `POST /reverse-upload` |
| `app.py:224` | `GET /reports/{report_id}` |
| `app.py:231` | `GET /structure` |
| `app.py:274` | `POST /v3/analyze` |
| `app.py:319` | `POST /admin/maintain-uploads` |

`grep -rn "export\|csv\|pymol\|download\|StreamingResponse" src/psf_reasoner/api/` 只命中 `app.py:8`（import `FileResponse, PlainTextResponse`）与 `app.py:154-155`（返回 index.html）。**没有 JSON/CSV/PyMOL 导出端点。**

### 2.2 前端：没有导出按钮

`grep -rniE "export|csv|pymol|download|blob|createObjectURL"` 覆盖整个 `api/static/`（app.js 462 行 + index.html 150 行 + styles.css）→ **零匹配**。

index.html 的全部按钮：`index.html:31,32,33`（模式 tab）、`74`（开始分析）、`75`（V82A 示例）、`76`（V3 因果推理）、`141,142`（WT/Mutant）、`143`（关闭视图）。**没有导出按钮，也没有客户端 Blob 导出。**

### 2.3 顺带发现：`datasets/review_export.py` 是孤儿模块

该文件实现了 `export_review_csv`（`review_export.py:16`）与 `export_review_json`（`review_export.py:40`），但**零调用者**。且它导出的是数据集人工审核用的 CSV，与"分析报告导出"是两回事。

> 用户怀疑属实且更严重：导出功能完全不存在，前后端都没有。

---

## 3. 三维证据定位

**结论：空壳。** 只有"高亮突变残基 + 配体"，而且残基号取自请求参数而非证据，还带硬编码兜底，反向模式下会高亮一个捏造的位点。

### 3.1 前端唯一的三维路径

`app.js:51-63` `showStructure()`，三处 `setStyle`：

- `app.js:58` — 整条链 cartoon 谱色
- `app.js:59` — `viewer.setStyle({chain, resi: resNum}, {cartoon:{color:"#ff6b6b"}, stick:{...}})` 高亮**单个残基**
- `app.js:60` — `viewer.setStyle({resn: ligandId.toUpperCase()}, {stick:{...}})` 高亮配体

调用者是报告里生成的两个按钮（`app.js:356` 输出 `data-resnum` 等属性，`app.js:395-401` 绑定）。

### 3.2 残基号来源是伪造的

`app.js:318`：

```js
const mResNum = r.request?.mutation?.residue_number || "82";
```

残基号来自**请求**，不是任何证据；`|| "82"` 是硬编码兜底。

后果：反向模式（`/reverse`、`/reverse-upload`）下 `request.mutation` 为 `null`（`app.py:168-172` 强制要求 mutation 为 None），因此视图会**恒定高亮 82 号残基 + A 链** —— 一个与实际分析无关的捏造位点。

### 3.3 没有 evidence → 残基/原子 的映射

- **前端**：`addEventListener` 全仓仅 8 处（`app.js:64,65,396,425,426,427,431,445`），**没有任何一处绑定在证据卡片 / 因果图节点 / 因果路径 / 证据缺口行上**（这些元素在 `app.js:168,226,225,272` 生成）。不存在 `highlight` / `select` / `zoomTo` / `focus` 等交互。
- 报告里的接触残基列表从未喂给 viewer；`app.js:17,56` 的 `referenceData` / `mutantData` 写了但**从未被读取**。
- **后端**：没有"evidence_id → 残基位置/原子"的结构化端点。证据的 `entities` 是自由文本（如 `physical/coordinates.py:70,115`、`physical/comparison.py:366`），`physical/modeling.py:146` 是 `f"{chain}:{residue_number}"` 字符串拼接，没有 schema 化。

### 3.4 后端有可用数据但前端未读

| 数据 | 位置 | 前端引用 |
|---|---|---|
| `InteractionDetail.protein_atom` / `ligand_atom` / `distance_angstrom` | `schemas/evidence.py:42-55,63`；真实填充于 `physical/comparison.py:205,225,245,265,285` | 0 次 |
| `StructuralMechanism.affected_region` | `schemas/mechanisms.py:65` | 0 次 |
| `ctx.neighborhood_4a` | 仅作文本渲染 `app.js:212` | 未连 viewer |

### 3.5 WT/Mutant 视图切换是惰性的

`index.html:141-142` 两个 tab，处理函数 `app.js:65-68` 只做 `viewerMode = t.dataset.mode` 与 `classList` 切换，**从不重新加载或替换模型**。点击 tab 不会改变三维视图。

> 用户怀疑属实：三维定位只到"高亮口袋/突变残基"这一层，而且比怀疑的还要弱——连口袋接触残基都没有，只有单个突变残基 + 配体，残基号还可能凭空生成。

---

## 4. FoldX / 插件

**结论：空壳。** FoldX 适配器代码实现是真实的，但**零生产接线**（只在测试里被实例化）；7 个"插件"是纯字符串元数据，没有任何执行能力。

### 4.1 FoldX 适配器：实现真实，但从未被使用

`FoldXMutationModeler`（`physical/modeling.py:32-176`）实现是真实的：

- `physical/modeling.py:54` `shutil.which(foldx_binary)` 检测是否安装
- `physical/modeling.py:100-106` `subprocess.run([foldx, "-f", "config.cfg"], timeout=300)` 真实调用 BuildModel
- `physical/modeling.py:65-72` 未安装或失败时**回退**到 `LocalSideChainMutationModeler`

**但是它从未被生产代码实例化。** grep 全仓 `FoldXMutationModeler`：

- `physical/modeling.py:32`（定义）
- `tests/test_comparison.py:9,131,149`（测试）
- `bootstrap.py:76` 默认接的是 `LocalSideChainMutationModeler()`，**不是** `FoldXMutationModeler()`

即：**用户即使装了 FoldX 也不会被调用**，因为组合根从未创建该适配器。没有环境变量开关能让它上线。

### 4.2 默认突变建模是"截断"，不是建模

`LocalSideChainMutationModeler`（`physical/modeling.py:208-292`）做的是确定性侧链截断（`_mutate_residue_by_truncation`，`modeling.py:303-343`）：删掉目标残基不需要的原子、保留共享原子。它自带的 limitations 已明说（`modeling.py:285-290`）：

> "This local model is suitable for evidence plumbing and side-chain truncation cases only."
> "It is not a rotamer search, molecular-dynamics relaxation, or crystallographic mutant structure."

这与 README 的描述一致（`README.md:61-65`），属于诚实声明。问题在于：**唯一可能做真实建模的 FoldX 路径没接线**，所以平台实际只有截断。

### 4.3 插件接口：纯元数据占位

`schemas/plugin_interface.py:96-127`：

- `register_plugin(name, tool_type, description)`（`plugin_interface.py:99-105`）只往 `_PLUGIN_REGISTRY` dict 里写三个字符串
- 预注册的 7 个：`foldx` / `rosetta` / `mmgbsa` / `fpocket` / `gromacs` / `amber` / `user_experiment`（`plugin_interface.py:114-127`）
- `list_registered_plugins()`（`plugin_interface.py:108`）**零调用者**

**没有任何插件有可执行实现、adapter 类、subprocess 调用或结果归一化落地。** `PluginResult`（`plugin_interface.py:44-89`）定义了一个标准化输出契约与 `to_evidence_dict()`，但从未有代码产出过 `PluginResult` 实例。

> 用户怀疑属实：的确"只是注册了插件接口而没有真实计算"。

### 4.4 云计算的真实状态

- **默认关闭**：`CloudEvidenceProvider.collect`（`physical/cloud_provider.py:30-32`）在 `adapter is None` 时直接 `return ()`；`bootstrap.py:108-113` `_cloud_adapter()` 仅在环境变量 `PSF_CLOUD_URL` 存在时创建 `HttpCloudAdapter`，否则返回 `None`。
- **需要外部部署**：`infrastructure/cloud_compute.py:58-66` 通过 `httpx.post(f"{base_url}/compute/{tool}")` 调用远端；`cloud/server.py` 是那个远端服务，`/compute/fpocket`（`cloud/server.py:67`）与 `/compute/coulomb`（`cloud/server.py:189`）**有真实实现**（含 API Key 校验 `cloud/server.py:47`）。
- 因此云路径是"真实但默认离线、需外部 Cloud Run 部署 + 设 `PSF_CLOUD_URL`/`PSF_CLOUD_SECRET`"。

---

## 5. 校准层

**结论：空壳。** 不存在"训练出来的模型"。线上的 `calibration_status` 恒为 HEURISTIC；`DomainKnowledgeCalibrator` 是手工系数且零调用；训练脚本存在，但只在离线审计中被调用，结果不落盘、不进任何推理链路。

### 5.1 "Domain-knowledge logistic regression" 就是手工系数

`calibration/calibrator.py` 的自述（`calibrator.py:38-45`）：

> "This is **NOT a trained model** — coefficients are set manually based on known structure-activity relationships."

- `COEFFICIENTS` 是 23 个手写浮点数（`calibrator.py:49-73`，如 `"charge_delta": 0.15`、`"is_catalytic": 0.20`）
- `INTERCEPT = -1.0`（`calibrator.py:75`）
- `predict()`（`calibrator.py:77-109`）就是 `sigmoid(intercept + Σ w_i·x_i)`

**并且它零调用者**：grep 全仓 `DomainKnowledgeCalibrator` 只在本文件内命中（`calibrator.py:34`）。它既没进 `bootstrap.py`，也没进 `service.py`，也没被任何测试或脚本使用。

### 5.2 训练代码是真的，但只在离线审计里跑

`train_pilot.py:80-126` `train_logistic_regression` 是真实的手写梯度下降 + L2（纯 Python，无 sklearn）。但它的调用者全部是离线审计脚本：

- `calibration/identity_audit.py:51,69,93`
- `calibration/ablation.py:115`
- `calibration/grouped_cv.py:82`
- `calibration/validity_audit.py:91,106,201,257,305`

**训练产物没有任何持久化**：全仓没有 `.pkl` / `.joblib` / `model.json` 之类的模型文件，没有 save/load 逻辑。`/v3/status`（`app.py:121-151`）会在**每次 HTTP 请求时现场重训** `identity_audit`（`app.py:125-128`），只为返回 MCC 数字展示，不产出可复用模型。

### 5.3 推理链路没有校准模型

`AnalysisService`（`service.py:30-47`）的构造参数里**没有 calibrator 位置**，`reasoning/baseline.py` 全程使用硬编码常数：

- 置信度基数：`0.63 / 0.47`（`baseline.py:90,112`）、`0.48`（`baseline.py:128`）、`0.42`（`baseline.py:172,207`）、`0.36`（`baseline.py:208`）
- 每条证据加分：`0.06` / `0.01`（`baseline.py:864`）、`0.07` / `-0.03`（`baseline.py:870`）、`0.12` / `-0.04`（`baseline.py:875`）、`0.12` / `-0.05` / `0.04`（`baseline.py:885-887`）、`0.08` / `-0.03` / `-0.06`（`baseline.py:935-939`）、`0.03`（`baseline.py:971`）
- 每个 claim 都带 `calibration_status=CalibrationStatus.HEURISTIC`（`baseline.py:119,154,201,242,279,603`）

这正是 `service.py:136-140` 那条 limitations 警告所描述的 "+0.06 per evidence match"。

### 5.4 老校准 provider 仍在用，但它是硬编码查表

`physical/calibration.py` 的 `HIVProteaseCalibrationProvider` **仍在默认链路中**（`bootstrap.py:20,70`），但实现是一个 `if`（`calibration.py:15-18`）：

```python
if request.mutation.notation != "V82A" or request.ligand.identifier.upper() != "MK1":
    return ()
```

只有输入恰好是 `V82A` + `MK1` 时才返回一条固定的定性标签（`calibration.py:19-56`，`value=1.0, unit="directional_label"`）。这是针对单个演示案例的硬编码分支，不是校准层。它自带的 limitations 也承认"is not a numeric Ki, Kd, or IC50 value"（`calibration.py:52`）。README 对此的描述（`README.md:67-70`）是诚实的。

### 5.5 前端 confidence 的来源

| 展示项 | 来源 | 位置 |
|---|---|---|
| 报告标题徽章 | `calibration_status === "heuristic" ? "⚠ HEURISTIC" : "CALIBRATED"` | `app.js:325,334` |
| 报告级 confidence | 各 claim 置信度算术平均 | `service.py:113-118` |
| 单条证据卡片 | `qualitative_confidence`，否则数字分桶（≥0.70 strong / ≥0.45 moderate / ≥0.25 weak） | `app.js:135-146,169` |
| 汇总面板 Strong/Moderate/Weak | `m.confidence >= 0.7 / >= 0.45` | `app.js:285-287` |
| 全局警告 | 硬编码文本，不读 `calibration_status` | `app.js:389` |

**两个前端缺陷**：

1. `app.js:325` 只对字符串 `"heuristic"` 特判，**其余一切（含 `null`/缺失）都渲染为 "CALIBRATED"**。当前后端恒返回 `heuristic`（`service.py:134`）所以没暴露，但这是一个会在字段缺失时输出正向错误声明的逻辑。
2. `index.html:125` 宣传「因果推理 · 文献证据 · **校准预测**」，与实际的启发式引擎不符。

**未渲染但后端已提供**：`report.limitations`（`schemas/report.py:38`）在 `app.js` 中零引用；`report.overall_agreement_score`（`report.py:34-37`，注释明确写"replaces confidence for report-level summary"）零引用——前端仍在展示已被取代的 `confidence`。

> 用户怀疑属实：校准模型仍是人工系数，且连这个人工系数模型都没接进推理链路。

---

## 6. 蛋白身份识别

**结论：部分可用（含严重 bug）。** 平台**从不**从 PDB 头解析蛋白身份；唯一自动识别逻辑是"按配体简称猜"，且猜不出来时会把 HIV-1 蛋白酶文献错误地附加到任意蛋白上。

### 6.1 结构文件从不提供蛋白身份

`grep -rni "COMPND\|HEADER\|entity_name\|organism" src/psf_reasoner/physical/structure.py` → **零匹配**。结构解析器不读 `COMPND`/`HEADER`，因此蛋白身份不可能来自结构本体。

### 6.2 唯一的"猜测"逻辑（确切位置）

`api/app.py:298-303`：

```python
lit_summary = get_evidence_summary(
    "HIV-1_PROTEASE"
    if "MK1" in resolved.ligand.identifier.upper()
    else "DHFR"
    if "MTX" in resolved.ligand.identifier.upper()
    else "",
    resolved.mutation.notation,
)
```

即：**看到配体是 MK1 就猜 HIV-1 蛋白酶，看到 MTX 就猜 DHFR，其余一律空串。** 这是用户怀疑的那段逻辑，确切位置为 `app.py:298-303`。

其他身份来源（均为硬编码表，非计算）：

- `datasets/golden_cases.py` — 每个案例手写 `protein_accession` / `protein_name` / `organism`（如 `golden_cases.py:39`）
- `calibration/build_feature_matrix.py:210-218` — accession → family hint 的 5 项硬编码映射
- `knowledge/entity_normalizer.py:72-113` — 5 项硬编码蛋白库

### 6.3 空串触发文献污染 bug（已复现验证）

`knowledge/literature_evidence.py:163-170` 的部分匹配兜底：

```python
key = protein_family.upper().strip()
entries = _CURATED_EVIDENCE.get(key, [])
if not entries:
    for k in _CURATED_EVIDENCE:
        if key in k or k in key:  # ← 空串时 "".__contains__ 恒真
            entries = _CURATED_EVIDENCE[k]
            break
```

当 `key == ""` 时 `"" in "HIV-1_PROTEASE"` 为 `True`，而 dict 的插入顺序中 `HIV-1_PROTEASE` 是第一个被注册的（`literature_evidence.py:31`），因此：

```
query_evidence("")            -> ['HIV_V82A_MK1_001']   ← HIV 文献
query_evidence("UNKNOWN")     -> []
query_evidence("TEM1_BLAC")   -> []
```

（用纯逻辑复现该函数验证，排除 import 依赖）

### 6.4 更严重：因果图的文献**永远**是 HIV

`app.py:296` 调用 `gen.generate(ctx)` **没有传 `protein_family`**；而 `MechanismGenerator.generate`（`mechanism_generator.py:37-41`）默认 `protein_family=""`，并在 `mechanism_generator.py:55` 调用 `query_evidence(protein_family, mutation, ligand)`。

结合 6.3 的 bug：**任何经 `/v3/analyze` 的分析，其因果图边上的"文献证据"都是 HIV-1 蛋白酶文献**（`mechanism_generator.py:100-111` 把 `lit_evidence` 挂到 binding→consequence 边上，`mechanism_generator.py:109` 过滤 grade ≤ 3）。输入 DHFR 或 EGFR 结构也一样。

### 6.5 蛋白名与催化残基注释同时失效

- `app.py:293` `ctx_builder.build(resolved, qc_report=...)` 未传 `protein_family_hint` → `StructuralContextBuilder` 的 `protein_name=protein_family_hint or "unknown"`（`structural_context_builder.py:135`）→ 恒为 `"unknown"`
- `mechanism_generator.py:50` `protein=protein_family or ctx.protein_name` → 因果图的 `protein` 字段也是 `"unknown"`
- 催化残基注释依赖 hint：`residue_role_annotator.py:66-67` 用 `protein_family_hint.upper() == family` 匹配 `_CATALYTIC_MOTIFS`，而兜底的 `_matches_family` **恒返回 False**（`residue_role_annotator.py:158-161` 注释明写 "relies on explicit protein_family_hint"）→ 不传 hint 时**完全没有催化残基注释**，`is_catalytic` 恒为 False

### 6.6 实体归一化层整体零调用

`knowledge/entity_normalizer.py` 中：

- `lookup_protein`（`entity_normalizer.py:144`）— 零调用者
- `lookup_ligand`（`entity_normalizer.py:152`）— 零调用者
- `classify_evidence_applicability`（`entity_normalizer.py:157`）— 零调用者

即：文件中宣传的「6 级证据适用性」**从未被真正计算过**。`literature_evidence.py:33,45,55,75,87,98,116,126,136` 里 9 条证据的 `applicability` 全部是**手写常量**，不是由查询与证据实体比对得出的。

> 用户怀疑属实且更糟：不仅"根据配体简称猜测"，猜不出来时还会错误地套用 HIV 文献。

---

## 7. 结构配对校验

**结论：空壳。** 严格配对函数零调用；更根本的是，其判据**不包含"结构中实际包含的配体"**，因此原理上无法发现 DRV 案例用 MK1 结构作 WT 这类不匹配。

### 7.1 `pair_builder.py` 零调用者

`build_pairs`（`datasets/pair_builder.py:45-125`）在全仓（`src/` + `tests/` + `cloud/`）**只有定义处命中，没有任何调用者**。PROJECT-STATE.md:74 称其为「严格 WT-Mutant 配对逻辑」，但它从未运行过。

### 7.2 判据不含结构配体

其宣称的 7 条判据（`pair_builder.py:49-59`）与实现（`pair_builder.py:63-114`）全部基于 `CandidateRecord` 的元数据：`protein_accession` / `ligand_id` / `assay_type` / `residue_position` / `is_wt` / `organism` / `temperature_kelvin` / `unit`。

`CandidateRecord`（`pair_builder.py:15-33`）的字段里**没有"结构中实际存在的配体"**，只有 `pdb_id: str`（`pair_builder.py:32`）和 `ligand_id`（`pair_builder.py:24`，语义是"实验配体"）。没有任何代码去解析 `pdb_id` 对应的结构文件、提取其 HETATM 配体、再与 `ligand_id` 比对。

`MutationLigandPair`（`datasets/schemas.py:54-99`）同样只有 `ligand_id`（`schemas.py:74`）与 `wt_pdb`/`mutant_pdb`（`schemas.py:88-89`），**没有结构配体字段**。

**结论：即使把 `build_pairs` 接上线，它也无法发现结构配体与实验配体不一致——该不匹配在数据模型层面不可表达。**

### 7.3 `HIV_V82A_DRV` 案例：系统知道不匹配，但只写在备注里

`datasets/golden_cases.py:58-72`：

- `golden_cases.py:63` `ligand_id="DRV", ligand_name="Darunavir"`
- `golden_cases.py:66` `wt_pdb="1sdt.cif", mutant_pdb=_hiv_wt[1]`（即 `1sdv.cif`），`has_structure_pair=True`
- `golden_cases.py:67` `review_notes="WT structure: 1sdt (MK1, not DRV). Mutant: 1sdv (V82A/MK1). Ligand differs from assay ligand."`

即：**系统自己明确知道配体不一致**，但该信息只存在于自由文本 `review_notes` 中。没有任何代码读取 `review_notes` 做校验，`has_structure_pair=True` 照常置位，`review_status=ReviewStatus.ACCEPTED`（`golden_cases.py:70`）照常接受。

同类问题在 HIV 组是系统性的：`golden_cases.py:53-56` 的注释写明"all share WT reference 1sdt (MK1)…we use 1sdt as the common WT anchor"，随后 15 个 HIV 案例（APV/NFV/SQV/IDV 等不同抑制剂）全部用 `wt_pdb="1sdt.cif"`（`golden_cases.py:82,97,112,127,142,157,172,187`）。

### 7.4 静默回退把 MK1 当成 DRV 用

`calibration/build_feature_matrix.py:127-139`：

```python
try:
    wt_ligand = wt_struct.locate_ligand_by_identifier(case.ligand_id)  # 找 DRV
except ValueError:
    # 找不到就"回退到结构中任意非标准残基"
    for r in wt_struct.residues:
        if r.is_hetero and rname not in std_aa and len(rname) <= 3:
            wt_ligand = r  # ← 拿到 MK1，但后续当作 DRV 使用
            break
```

`build_feature_matrix.py:177` 随后 `decompose_ligand(wt_ligand, case.ligand_id)` —— 用的是 MK1 的坐标，配的却是 `"DRV"` 的标识。整个 `except` 块（`build_feature_matrix.py:185-186`）还是 `except Exception: pass`，**静默吞掉所有错误**。

### 7.5 数据集规模与文档不符

| 来源 | 声称 | 实际 |
|---|---|---|
| `docs/PROJECT-STATE.md:78,130,171` | 118 个金案例 | `grep -c "cases.append(MutationLigandPair("` = **44** |
| `docs/PROJECT-STATE.md:87` | "跨 8 家族 118 案例" | 8 个 split_group 属实，案例数 44 |
| `build_feature_matrix.py:3` docstring | "golden 30 cases" | 44 |
| `docs/TODO.md`（Data Curation） | "target ≥30 calibration-ready cases (**currently 2**)" | 与 TODO 自述一致：`has_structure_pair=True` 仅 **3** 处 |

真实可配对结构只有 3 个案例（`grep -c "has_structure_pair=True"` = 3），其余全是"仅 WT 参考结构"。

> 用户怀疑属实：`pair_builder` 不会拒绝或标记 `HIV_V82A_DRV` 的不匹配——它连被调用都没有，而且它的判据里根本没有结构配体这一项。

---

## 8. 教学/科研模式

**结论：完全缺失。**

`grep -rniE "teaching|tutorial|学习目标|思考题|quiz|lesson|education|教学模式|step_by_step|stepwise"` 覆盖 `src/`、`docs/`、`README.md` → **零匹配**。

- 前端 `index.html` / `app.js` 中没有任何分步骤解释、学习目标、思考题、教学模式开关
- 后端没有任何教学相关的 schema、端点或字段
- 文档中也没有教学模式的规划条目

> 用户怀疑属实：完全没有实现，连规划都没有。

---

## 9. 上传类型

**结论：后端支持三种输入方式（其中 RCSB 在线获取不存在）；前端上传入口不可达。**

### 9.1 multipart 上传 — 后端可用，前端不可达

- `POST /analyze-upload`（`app.py:184-208`）：接受 `reference_file`、`mutant_file`、`ligand`、`mutation`、`chain`、`phenotype`
- `POST /reverse-upload`（`app.py:210-222`）：接受 `reference_file`、`ligand`、`phenotype`
- 存储：`_store_upload`（`app.py:342-367`），文件名 `uuid4().hex + 后缀`（`app.py:350`）
- 校验：仅允许 `.pdb` / `.cif` / `.mmcif`（`app.py:27,344-348`），上限 25 MB（`app.py:26,356-360`）

**但前端不可达**（详见 §10.1）。

### 9.2 `upload_id` 引用 — 后端可用

- `_resolve_structure_input`（`app.py:30-84`）：优先用 `upload_id` 经 `resolve_upload` 解析；无 `upload_id` 时要求 `path` 存在
- `GET /structure?upload_id=`（`app.py:231-272`）：用 `gemmi.read_structure` 读回并转成 minimal PDB 文本供 3Dmol.js 使用（`app.py:263-269`），并剔除 ANISOU 行（`app.py:266`）
- 前端实际用的是这个：`app.js:47` `fetch('/structure?...')`（唯一被调用的读取端点）

### 9.3 RCSB 在线获取 — 前后端均不存在

- **后端**：`api/app.py` 的 12 个路由中没有任何 RCSB 获取端点。全仓 `grep -rni "rcsb"` 只命中一处 provenance 字符串：`physical/calibration.py:46` `source="RCSB PDB 1SDT and 1SDV"`。
- **前端**：`grep -rniE "rcsb|files\.rcsb|pdb_id|fetch_pdb"` 覆盖 `api/static/` → **零匹配**。`index.html` 中没有 PDB ID 输入框（全部输入框为 `index.html:41,45,53,57,61,65`：两个文件选择器 + 配体 + 突变 + 链 + 表型），也没有构造 `files.rcsb.org` 的客户端 URL。

**结论：不是"只有 UI 没有后端"，而是 UI 和后端都没有。** 结构来源只能是本地文件（前端硬编码 `examples/data/*.cif`，`app.js:4-5,11`）。

---

## 10. 额外发现（未在必查清单内，但影响严重）

### 10.1 `index.html` 中不存在 `<form>`，上传路径整体不可达（最高优先级）

- `index.html:74` 有按钮 `<button id="submit-analysis">开始分析</button>`
- `app.js:30` 捕获了它：`submit: $("#submit-analysis")`，但 **`els.submit` 全文件引用次数为 0，没有任何监听器被绑定**
- `app.js:24` `form: $("#analysis-form")` → `null`（**`index.html` 中不存在 `<form>` 元素**）
- `app.js:445` `$("#analysis-form")?.addEventListener("submit", ...)` 因可选链 `?.` 而**静默失效**
- 因此 `app.js:445-453` 整段（含 `app.js:450` 的 `/analyze-upload` 与 `/reverse-upload` 调用）是**死代码**
- `app.js:449` `new FormData($("#analysis-form"))` 若真被执行会直接抛异常

**后果：普通用户通过 UI 无法上传 PDB 文件。** 唯一可用的分析入口是两个硬编码示例按钮。

### 10.2 侧栏所有输入框从未被读取

`#reference-file`(`index.html:41`)、`#mutant-file`(`45`)、`#ligand`(`53`)、`#mutation`(`57`)、`#chain`(`61`)、`#phenotype`(`65`) 在 `app.js` 中**引用次数均为 0**（`#mutation` 只在 `app.js:440` 被写 `required` 属性，但因为没有 form 也无意义）。

所有分析使用硬编码的 `examplePayload`（`app.js:3-9`）：

- `#run-example`（`index.html:75`）→ `POST /analyze`（`app.js:409`）
- `#run-v3-example`（`index.html:76`，标签「V3 因果推理」）→ `POST /v3/analyze`（`app.js:422`），且 `delete payload.phenotype`（`app.js:420-421`）

**即：无论用户在界面上填什么，跑的都是 `1sdt.cif` / `1sdv.cif` + MK1 + V82A。**

### 10.3 其他死元素

- `#run-reverse-example`（`app.js:426` 绑定）在 `index.html` 中**不存在** → `/reverse` 从 UI 不可达
- 模式 tab「正向 P→F」与「双向 P⇄F」在 `app.js:450` 映射到同一端点，且都不影响示例按钮
- `app.js:17` 的 `referenceData` / `mutantData` 写了从未读
- 未被使用的捕获元素：`els.form`(`app.js:24`)、`els.status`(`25`)、`els.submit`(`30`)、`els.viewer3d`(`32`)
- `index.html:78` 文案「文件仅在本地处理」与实际上传后端存储（`app.py:342-367`）不符

### 10.4 特征矩阵存在目标泄漏（科学有效性问题）

`calibration/build_feature_matrix.py:200-201`：

```python
if case.delta_delta_g is not None:
    fv.f_volume_delta = float(case.delta_delta_g)  # use ΔΔG as strong signal
```

把**实验测得的 ΔΔG** 写入 23 维特征的**第 1 维**（`feature_schema.py:25,63`）。而标签由同一实验的方向导出（`build_feature_matrix.py:73-81`，`AFFINITY_DECREASE → 1.0`）。ΔΔG 非零 ⟺ 方向为 decrease，因此对这些样本构成**完美的标签泄漏**。`golden_cases.py:211,227,243,258` 有 4 处设置了 `delta_delta_g`。

### 10.5 特征矩阵约 10/23 维恒为零

`build_feature_matrix.py:105` `ctx_diff = {}` 初始化后**从未被赋值**（该函数只解析 `wt_pdb`，从不读 `mutant_pdb`）。因此 `extract_features`（`feature_schema.py:122-133`）中所有取自 `diffs` 的特征恒为默认值：

`volume_delta`（除上述泄漏样本外）、`polarity_added`、`polarity_removed`、`charge_delta`、`aromatic_added`、`hbond_donor_gained`、`hbond_acceptor_gained`、`contact_count_delta`、`atoms_lost`、`atoms_gained` —— **即全部"结构差异"类特征恒为 0**。

另：`catalytic_4a = 0` 硬编码（`build_feature_matrix.py:173`，附注释 "can't easily determine from single structure"）。

### 10.6 审计报告本身已给出否定结论

`pilot_validity_audit/pilot_validity_summary.md`：

- 第 5 节 Leave-One-Protein-Out CV：`majority` / `heuristic` / `logistic_regression` 三种模型 **MCC 全为 0.000**（balanced_acc 分别 0.400 / 0.400 / 0.110）
- 第 2 节 文献掩蔽：Full model MCC 0.711 → masked 0.441，MCC drop 0.270，结论 "Mixed — investigate per-fold"
- 第 4 节 子集 B（struct_20）accuracy 1.000 / MCC 1.000 —— 结合 §10.4 的泄漏，该完美分数高度可疑

即：**离线审计已经表明该特征集不具备跨蛋白预测能力**，而线上推理链路连这个模型都没接。

---

## 修复优先级建议清单

> **说明：以下清单仅供统筹参考，本次审查不修改任何代码。** 优先级依据「是否阻断普通用户完成一次基本分析」与「是否会导致错误的科学结论」两个维度排序。

### P0 — 阻断性问题（用户无法完成基本操作 / 输出错误结论）

| # | 问题 | 位置 | 建议方向 |
|---|---|---|---|
| 1 | 「开始分析」按钮无监听器；`index.html` 无 `<form>`；上传链路整段死代码 | `index.html:74`；`app.js:24,30,445-453` | 补 `<form id="analysis-form">` 或改为直接读各输入框 id；为 `#submit-analysis` 绑定 submit 处理 |
| 2 | 侧栏全部输入框零引用，所有分析跑硬编码演示数据 | `app.js:3-9,409,422`；`index.html:41,45,53,57,61,65` | 从 DOM 读取真实输入构造 payload |
| 3 | `/v3/analyze` 的文献恒为 HIV-1：空串触发部分匹配兜底 | `literature_evidence.py:163-170`；`app.py:296,298-303`；`mechanism_generator.py:55` | 修 `query_evidence` 的空串判空；`app.py:296` 传真实 `protein_family` |
| 4 | 特征矩阵目标泄漏：实验 ΔΔG 被当作输入特征 | `build_feature_matrix.py:200-201` | 移除该赋值，或将其明确降级为 label 而非 feature |
| 5 | 前端对 `calibration_status` 缺失渲染为 "CALIBRATED" | `app.js:325,334` | 改为白名单判断，未知状态显示 UNKNOWN |

### P1 — 严重（功能存在但不可用 / 声明与实现不符）

| # | 问题 | 位置 | 建议方向 |
|---|---|---|---|
| 6 | V3 四模块未接入默认服务，用户常规流程无 V3 | `bootstrap.py:40-77`；`service.py:30-47` | 将 StructuralContextBuilder 等纳入 `AnalysisService` 或合并 `/v3/analyze` 进 `/analyze` |
| 7 | 蛋白身份按配体简称猜测；无结构来源；催化残基注释失效 | `app.py:298-303`；`structural_context_builder.py:135`；`residue_role_annotator.py:158-161` | 解析 PDB/mmCIF 的 `COMPND`/entity 信息；或要求用户显式指定 |
| 8 | 三维证据定位不存在；反向模式高亮捏造的 82 号残基 | `app.js:51-63,318`；`schemas/evidence.py:42-55` | 后端输出 evidence→residue/atom 结构化映射；前端绑定点击事件；去掉 `\|\| "82"` |
| 9 | 反向示例按钮指向不存在的 DOM 元素 | `app.js:426` | 补元素或删绑定 |
| 10 | WT/Mutant 视图 tab 惰性，不切换模型 | `app.js:65-68`；`index.html:141-142` | 用已缓存的 `referenceData`/`mutantData` 实现模型切换 |
| 11 | `pair_builder` 零调用且判据无结构配体，无法发现 1sdt/DRV 类不匹配 | `pair_builder.py:45-125`；`datasets/schemas.py:74,88-89` | 给数据模型加"结构配体"字段；在 `build_feature_matrix` 中校验并在不匹配时拒绝或标记 |
| 12 | 特征矩阵约 10/23 维恒为 0（`ctx_diff` 从未赋值） | `build_feature_matrix.py:105,173` | 真正读入 `mutant_pdb` 并填充结构差异特征 |
| 13 | `build_feature_matrix` 静默把 MK1 当 DRV 用；`except: pass` 吞错 | `build_feature_matrix.py:127-139,185-186` | 回退时记录 warning 并标记该样本的配体不匹配 |

### P2 — 中等（缺失功能 / 无效代码）

| # | 问题 | 位置 | 建议方向 |
|---|---|---|---|
| 14 | 导出功能（JSON/CSV/PyMOL）前后端均缺失 | 全仓 | 新增导出端点 + 前端按钮；或复用 `datasets/review_export.py` 的模式 |
| 15 | FoldX 适配器零生产接线，装了也不会用 | `physical/modeling.py:32-176`；`bootstrap.py:76` | 在 `bootstrap.py` 中按环境变量选择 FoldX/本地 modeler |
| 16 | `DomainKnowledgeCalibrator` 零调用；`calibration_status` 恒为 HEURISTIC | `calibrator.py:34-123`；`service.py:134` | 决定是否接入；若接入须先解决 P0#4 |
| 17 | 训练产物不落盘，每次 `/v3/status` 现场重训 | `app.py:121-151`；`train_pilot.py:80-126` | 增加模型序列化与加载 |
| 18 | 7 个预注册插件纯元数据，无实现 | `plugin_interface.py:96-127` | 落地或明确标注为占位 |
| 19 | 实体归一化层三个查询函数零调用；9 条文献的 applicability 全手写 | `entity_normalizer.py:144,152,157`；`literature_evidence.py:33-136` | 接线或在文档中降级描述 |
| 20 | `schemas/v3_task.py` 死代码；`review_export.py` 孤儿模块 | `v3_task.py:1-96`；`review_export.py:16,40` | 接入或删除 |

### P3 — 文档与一致性

| # | 问题 | 位置 | 建议方向 |
|---|---|---|---|
| 21 | 文档声称 118 金案例，实际 44（可配对仅 3）；TODO 自述 "currently 2" | `PROJECT-STATE.md:78,87,130,171`；`TODO.md` | 同步真实数字 |
| 22 | `PROJECT-STATE.md` 把零调用模块标注为「已完成」 | `PROJECT-STATE.md:42,48,53,58,64,70` | 区分「代码完成」与「已接线」 |
| 23 | 前端宣传「校准预测」，实际为启发式 | `index.html:125` | 改为「启发式评分」 |
| 24 | 前端未渲染 `report.limitations` 与 `overall_agreement_score`（后者注释明确说取代 confidence） | `schemas/report.py:34-38`；`app.js` 零引用 | 渲染这两个字段 |
| 25 | `/v3/analyze` 无任何测试；V3 模块零测试覆盖 | `tests/` | 补端点级与模块级测试 |
| 26 | 「文件仅在本地处理」文案与后端存储不符 | `index.html:78` | 修正文案 |

---

## 附：本次审查中确认「零调用者」的模块清单

以下模块在 `src/` + `tests/` + `cloud/` 全范围内**无任何调用点**（仅定义处命中）：

| 模块 / 符号 | 位置 |
|---|---|
| `schemas/v3_task.py`（全部符号） | `v3_task.py:12-96` |
| `datasets/pair_builder.py::build_pairs` | `pair_builder.py:45` |
| `datasets/review_export.py::export_review_csv` / `export_review_json` | `review_export.py:16,40` |
| `calibration/calibrator.py::DomainKnowledgeCalibrator` | `calibrator.py:34` |
| `schemas/plugin_interface.py::list_registered_plugins` | `plugin_interface.py:108` |
| `knowledge/entity_normalizer.py::lookup_protein` / `lookup_ligand` / `classify_evidence_applicability` | `entity_normalizer.py:144,152,157` |
| `physical/modeling.py::FoldXMutationModeler`（生产代码中） | `modeling.py:32`（仅 `tests/test_comparison.py` 使用） |
| `physical/modeling.py::UnconfiguredMutationModeler`（生产代码中） | `modeling.py:194`（仅测试使用） |

**仅在离线脚本中调用、未进入任何 HTTP/CLI 请求链路**的模块：

`calibration/train_pilot.py`、`calibration/build_feature_matrix.py`、`calibration/grouped_cv.py`、`calibration/ablation.py`、`calibration/validity_audit.py`、`calibration/identity_audit.py`（后者例外：被 `/v3/status` 调用，但仅用于展示 MCC）。
