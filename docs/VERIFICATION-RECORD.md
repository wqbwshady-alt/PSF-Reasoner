# PSF-Reasoner 独立验证记录

> 验证执行者：独立验证 Agent（不修改任何项目代码，只运行与审查）
> 验证日期：2026-09-10 19:1x – 19:4x（CST）
> 工作目录：`/Users/zengbowen/psf-reasoner`
> 验证方式：新建独立 venv 实测，所有结论均来自实际命令输出，未运行核实的项目一律标注为「未核实」。

---

## 0. 首要说明：验证期间代码库被并发修改（影响所有结论）

本次验证过程中，**另一个进程在持续修改本仓库**。这不是推测，是文件系统时间戳与 git 状态直接证据：

- 验证开始时 `tests/` 有 **17 个测试文件**（`ls -la tests/` 实测）；
- 19:32 期间凭空出现 **4 个新测试文件**：`test_data_integrity.py`、`test_feature_matrix_integrity.py`、`test_literature_integrity.py`、`test_v3_api.py`；
- 测试总数从 **128 → 156**；
- `src/psf_reasoner/api/app.py` 于 19:25:38 被修改，`physical/identity.py` 于 19:34:07 被修改，`api/app.py` 于 19:35:53 再次被修改；
- `git status` 显示 17 个已修改文件 + 未跟踪的 `docs/EVIDENCE-REVIEW.md`、`docs/PLATFORM-REVIEW.md`、`cases/`。

**直接后果：同一个命令在不同时刻得到不同结果。** 例如 `tests/test_api.py::test_structure_endpoint_rejects_path_traversal`：

| 时刻 | 结果 | 原因 |
|---|---|---|
| R1（19:19–19:24） | 通过 | 当时的 `app.py` 版本无此问题 |
| R1b（~19:31） | **失败** `NameError: EXAMPLES_DIR` | 19:25:38 的改动引入了未定义名 |
| R3（19:38，当前） | 通过 | 并发进程于 19:35:53 补上了 `EXAMPLES_DIR` 定义 |

因此下文所有测试结果都标注**修订版本指纹**（`src` + `tests` 全部 `.py` 文件的 md5 汇总）：

- **修订 R1**：17 个测试文件、128 用例（指纹未记录，早于指纹机制引入）
- **修订 R2/R3**：156 用例，指纹 `132a336847aa9aa144615175a0aac9c3`

> 结论：**「128 个测试全部通过」「V3 已完成」这类表述在本仓库中不具备稳定的可核实性**，因为代码库在被验证的同时被改写。下文的 R3 结果仅对指纹 `132a3368…` 负责。

---

## 1. 环境信息

### 1.1 Python 版本选择

```
$ command -v python3.12 python3.13 python3.11 python3
（3.12 / 3.13 / 3.11 均不存在）
/opt/homebrew/bin/python3
Python 3.14.7
```

系统中可用解释器：`python3.14`（3.14.7）、`python3.9`（过旧）。项目 `pyproject.toml` 要求 `>=3.12,<3.15`，故选用 **Python 3.14.7**（在允许范围内）。注意：**未能按要求使用 3.12 或 3.13，因为本机没有安装**。

### 1.2 虚拟环境与安装

```
$ /opt/homebrew/bin/python3.14 -m venv .venv-verify
$ .venv-verify/bin/python -m pip install -e '.[dev]'
...
Successfully installed ... psf-reasoner-0.1.0
```

**安装成功，无报错。** 关键依赖版本（`pip list` 实测）：

| 包 | 版本 | 包 | 版本 |
|---|---|---|---|
| gemmi | 0.7.5 | pytest | 8.4.2 |
| fastapi | 0.141.1 | pytest-cov | 6.3.0 |
| pydantic | 2.13.5 | starlette | 1.6.0 |
| typer | 0.27.2 | httpx | 0.28.1 |
| uvicorn | 0.52.4 | ruff | 0.16.6 |
| click | 8.5.0 | **anthropic** | **未安装** |

`anthropic` 未安装（`llm` extra 未安装）。**重要**：这不影响 LLM 路径被激活——实际使用的是 `DeepSeekProvider`（见 §3）。

---

## 2. 测试运行记录

### 2.1 R1（128 用例，环境含 `PSF_LLM=1`）

```
$ .venv-verify/bin/python -m pytest -p no:cacheprovider --durations=10 -v
...
============ 127 passed, 1 skipped, 2 warnings in 274.60s (0:04:34) ============
```

- **127 通过 / 1 跳过 / 0 失败**，耗时 **274.60 秒**。
- 跳过项：`tests/test_external_validation.py:87: PLIP not installed (requires Python ≤3.12, OpenBabel)`。
- 警告 2 条，均来自第三方（starlette/anyio 弃用告警），与项目代码无关。
- 最慢 10 项耗时 13–54 秒，全部是调用 `create_default_runner()` 的测试。

> 「128 个测试」= 128 个用例被收集，其中 **1 个被跳过**，因此「128 个测试全部通过」在字面上不成立；实际是「127 通过 + 1 跳过」。

### 2.2 R1b（同 128 用例，去掉 `PSF_LLM`/`PSF_CLOUD_URL`/`DEEPSEEK_API_KEY`）

```
$ env -u PSF_LLM -u PSF_CLOUD_URL -u DEEPSEEK_API_KEY .venv-verify/bin/python -m pytest -q -rs
...F..................................................................s. [ 56%]
SKIPPED [1] tests/test_external_validation.py:87: PLIP not installed
EXIT=1
```

- **1 失败 / 126 通过 / 1 跳过**。
- 失败：`tests/test_api.py::test_structure_endpoint_rejects_path_traversal`
  `E  NameError: name 'EXAMPLES_DIR' is not defined` — `src/psf_reasoner/api/app.py:256`
  （`EXAMPLES_DIR` 全仓库仅此一处出现，从未被定义；HEAD 版本无此引用，属工作区回归。该缺陷已于 19:35:53 被并发进程修复。）

### 2.3 R2（156 用例，环境含 `PSF_LLM=1`）

```
$ .venv-verify/bin/python -m pytest -p no:cacheprovider -q -rs
...F.................................................................... [ 46%]
........s............................................................... [ 92%]
....F.F.FF.F                                                             [100%]
```

**6 失败 / 149 通过 / 1 跳过**。失败全部集中在并发新增的测试文件：

| 测试 | 错误 |
|---|---|
| `test_api.py::test_structure_endpoint_rejects_path_traversal` | `NameError: EXAMPLES_DIR`（app.py:130） |
| `test_v3_api.py::test_v3_analyze_includes_identity_from_structure` | `AttributeError: 'gemmi.InfoMap' object has no attribute 'get'` |
| `test_v3_api.py::test_v3_export_json_csv_pymol_roundtrip` | 同上 |
| `test_v3_api.py::test_export_rejects_unknown_format` | 同上 |
| `test_v3_api.py::test_v3_upload_endpoint_multipart` | 同上 |
| `test_v3_api.py::test_example_structure_serving` | `NameError: EXAMPLES_DIR` |

> 该轮运行期间代码库**再次被修改**（指纹 `2b698ad2…` → `132a3368…`），故这 6 个失败反映的是一个瞬时状态，**不应视为对当前代码的最终评价**。

### 2.4 R3（156 用例，指纹 `132a3368…`，确定性环境）— 本次验证的权威结果

```
tree BEFORE: 132a336847aa9aa144615175a0aac9c3
$ env -u PSF_LLM -u PSF_CLOUD_URL -u DEEPSEEK_API_KEY .venv-verify/bin/python -m pytest -p no:cacheprovider -rs
155 passed, 1 skipped, 2 warnings in 1.45s
tree AFTER : 132a336847aa9aa144615175a0aac9c3
```

- **155 通过 / 1 跳过 / 0 失败**，耗时 **1.45 秒**，运行前后指纹一致（无并发改动）。
- 2.3 中失败的 6 项已由并发进程修复，实测 `tests/test_api.py::test_structure_endpoint_rejects_path_traversal tests/test_v3_api.py` → `9 passed in 1.16s`。

### 2.5 一个附带发现：`pytest -q` 会隐藏统计行

`pyproject.toml` 设了 `addopts = "-q"`。再手工加 `-q` 会变成 `-qq`，pytest 会**吞掉最后的 `N passed` 统计行**（实测：只有进度点，exit=0 但无汇总）。本记录中所有精确计数均以 `-o addopts=""` 或直接 `python -m pytest` 获得。

### 2.6 耗时异常：测试是否真的在跑网络？

同一测试、同一修订，仅环境变量不同：

```
$ env PSF_LLM=1  ... pytest -q -o addopts="" tests/test_reasoning.py::test_report_id_is_stable_for_same_request
1 passed in 50.70s

$ env -u PSF_LLM -u PSF_CLOUD_URL -u DEEPSEEK_API_KEY ... （同一测试）
1 passed in 0.01s
```

**5070 倍差距。** 全套件同理：`274.60s`（R1，含 `PSF_LLM=1`）vs `1.45s`（R3，无 LLM）。

**这证明测试确实在发真实网络请求**，而非使用 mock。见 §3。

---

## 3. 关键机制发现：测试默认会打真实 LLM API

`src/psf_reasoner/bootstrap.py` 的工厂函数在未显式传入 provider 时会读环境变量：

```python
def _auto_llm_provider() -> LLMProvider | None:
    if os.environ.get("PSF_LLM") != "1":
        return None
    provider_name = os.environ.get("PSF_LLM_PROVIDER", "deepseek")
    ...
    return DeepSeekProvider()          # -> httpx.post("https://api.deepseek.com/...")
```

本机环境**恰好**设置了：

```
PSF_LLM=1
DEEPSEEK_API_KEY=<已设置>
PSF_CLOUD_URL=https://psf-cloud-compute-800903726899.us-central1.run.app
```

实测确认（未发请求，仅检查对象类型）：

| 环境 | `_forward_reasoner` | `_reverse_reasoner` | `_consistency_checker` |
|---|---|---|---|
| 当前环境 | `LLMForwardReasoner` | `LLMReverseReasoner` | `LLMConsistencyChecker` |
| 去掉 `PSF_LLM` | `BaselineForwardReasoner` | `BaselineReverseReasoner` | `BaselineConsistencyChecker` |

而测试中有约 20 处直接调用 `create_default_runner()` / `create_default_service()` 且**不注入 provider**（`test_api.py` 8 处、`test_batch.py` 4 处、`test_reasoning.py` 3 处、`test_comparison.py` 1 处、`test_infrastructure.py` 2 处、`test_cli.py` 的 CLI 路径），`tests/conftest.py` 中**没有** `autouse` fixture 清理这些环境变量。

**推论：**
1. 同一份测试代码，在本机是「调用线上 DeepSeek + Cloud Run 的集成测试」，在干净 CI 中是「纯本地确定性单元测试」——**两者覆盖的是完全不同的代码路径**。
2. 由此产生的通过/失败依赖第三方服务的可用性、配额与采样随机性，不具备可复现性。
3. `PSF_CLOUD_URL` 指向的 Cloud Run 服务实测**在线**（`GET /health` → HTTP 200），所以云路径同样会被真实调用。

---

## 4. 复现性验证（V82A 配对分析）

CLI 实际用法（`psf analyze --help` 实测，**必须提供 `--phenotype`**，且**没有 `--output` 参数**，报告直接打印到 stdout）：

```
psf analyze --structure examples/data/1sdt.cif --mutant-structure examples/data/1sdv.cif \
            --ligand MK1 --mutation V82A --chain A --phenotype drug_resistance
```

### 4.1 按当前默认配置（`PSF_LLM=1`）运行两次 → **不一致**

两次运行结果深度对比（自写脚本逐字段递归比较）：

```
TOTAL DIFFERING PATHS: 235
  .confidence: '0.7' vs '0.664'
  .consistency_checks[]: LEN 3 vs 4
  .consistency_checks[0].title: 'Forward and reverse paths converge on pocket_packing'
                             vs 'Forward and reverse paths converge on ligand_anchoring'
  .functional_hypotheses[1].function_type: 'ligand_affinity' vs 'ligand_selectivity'
  .missing_evidence[]: LEN 9 vs 8
  .generated_at: ...
```

**两份报告在科学内容层面实质不同**：机制数量、一致性检查数量与标题、功能假设的类型与方向、缺失证据条目数、整体 confidence（0.7 vs 0.664）全部不同。LLM 的 token 计数（`prompt_tokens` 852 vs 1129）也证明这是两次真实的模型调用。

### 4.2 去掉 LLM / 云依赖后运行两次 → **一致（仅时间戳不同）**

```
$ for i in 1 2; do env -u PSF_LLM -u PSF_CLOUD_URL .venv-verify/bin/psf analyze ... > /tmp/psf_base$i.json; done
$ diff /tmp/psf_base1.json /tmp/psf_base2.json
206c206
<   "generated_at": "2026-09-10T11:31:03.933514Z",
---
>   "generated_at": "2026-09-10T11:31:04.249003Z",
```

**除 `generated_at` 时间戳外逐字节一致**（74447 字节，md5 不同仅因时间戳）。

> **结论：** 项目的确定性基线路径复现性良好。但**默认配置（`PSF_LLM=1`）下的分析不可复现**——同一命令、同一输入、同一台机器，两次得到实质不同的科学结论。这对「科研有效性」是硬伤：报告不可复现即不可审计。

---

## 5. 导出验证

导出入口：`GET /export/{report_id}?format=json|csv|pymol`（`src/psf_reasoner/api/exports.py`）。导出内容存放在进程内 `_V3_RESULTS`，须先调用 `POST /v3/analyze`。

**实测（uvicorn 127.0.0.1:8101）：**

```
POST /v3/analyze → HTTP 200, 80357 bytes, report_id=report-bc364fd422dc
GET  /export/report-bc364fd422dc?format=json  → HTTP 200, 110477 bytes, application/json
GET  /export/report-bc364fd422dc?format=csv   → HTTP 200,  11981 bytes, text/csv
GET  /export/report-bc364fd422dc?format=pymol → HTTP 200,   1391 bytes, text/plain
```

三个文件均成功生成、可被标准工具解析（`file` 识别为 JSON data / CSV text / ASCII text）。

### 5.1 CSV 与页面数据一致性 — **通过**

| 检查项 | 结果 |
|---|---|
| 可解析行数 | 53 行（+表头） |
| 行类别直方图 | physical_evidence 26 / structural_mechanism 4 / functional_hypothesis 2 / missing_evidence 11 / validation_step 10 |
| 与报告内各类计数是否一致 | **完全一致** |
| CSV 中是否存在报告中不存在的 id | **无** |

### 5.2 JSON 与页面数据一致性 — **通过（仅时间格式差异）**

逐字段递归比较导出 JSON 与 `/v3/analyze` 返回载荷，**差异路径数 = 1**：

```
.v2_report.generated_at : '2026-09-10T11:35:57.799805Z' vs '2026-09-10 11:35:57.799805+00:00'
```

同一时刻的两种序列化格式（`default=str` 造成），非数据不一致。

### 5.3 PyMOL 脚本一致性 — **通过**

脚本引用的残基号 `resi 80,81,82,83,84`，其中 82 为突变位点；`resi 81/83/80/84` 来自载荷 `v3_context.neighborhood_4a`，实测：

```
载荷 neighborhood_4a labels : ['A:PRO81', 'A:ASN83', 'A:THR80', 'A:ILE84']
脚本 resi 提取              : [80, 81, 82, 83, 84]   ✅ 一致
```

脚本正确 load 两个结构（`1sdt.cif` / `1sdv.cif`），配体 `MK1` 正确。

> 注：脚本仅通过文本审查（本机无 PyMOL，**未实际执行脚本**）。脚本是纯文本生成，未见语法问题。

---

## 6. 数据匹配抽查（金案例）

### 6.1 案例总数 vs PROJECT-STATE.md 的「118」

```
$ python -c "from psf_reasoner.datasets.golden_cases import load_golden_cases; ..."
load_golden_cases() total: 127
QC: {"total_samples": 127, "accepted": 9, "pending": 5, "rejected": 113, ...,
     "has_structure_pair": 3, "has_ddg": 1, "unverified": 118, "missing_pmid": 113}
load_verified_cases(): 9
```

**「118 个金案例」的说法不成立**：

- 实际加载 **127** 条（不是 118）；
- 其中 **rejected 113 条、pending 5 条、accepted 仅 9 条**；
- **有 WT+突变体结构对的只有 3 条**；
- **有 ΔΔG 的只有 1 条**；
- 113 条根本没有 PMID。

`docs/PROJECT-STATE.md` 现已在开头加入审计横幅，承认「118」被独立文献核验推翻（103 条引用无关 PMID、50 条为配额填充编造），并说明全文其余内容按 2026-07-21 快照保留。**该文件第 136 行仍写着 `golden_cases.py # 118 cases`，与实测不符（文档自身未清理干净）。**

### 6.2 `HIV_V82A_DRV` 案例

```
sample_id      = HIV_V82A_DRV
ligand_id      = DRV (Darunavir)      wt_pdb = 1sdt.cif      mutant_pdb = (空)
pmid = ''      doi = ''
review_status  = rejected
rejection_reason = 'PMID 12730686 is cyclophilin A; structure ligand (MK1) != assay ligand'
has_structure_pair = False
```

独立核验（用 gemmi 直接读结构，不经过项目代码）：

```
HET residues in 1sdt.cif: ['CL', 'MK1']
记录声称的配体:            DRV (Darunavir)
→ 配体不匹配：True
```

**独立确认该案例的配体确实不匹配。** 该记录现已被正确标为 `rejected` 并写明理由。`pair_builder.build_pairs` 在全仓库中**从未被任何生产代码或测试调用**（`grep` 除自身模块外零命中），属死代码。

---

## 7. 校准层运行

### 7.1 是否有真实训练 / 模型序列化？

- `calibration/train_pilot.py` 含真实的纯 Python 逻辑回归梯度下降实现（`train_logistic_regression`，1000 次迭代 + L2），**是真实训练代码**；
- 但**全仓库不存在任何序列化模型文件**（`find` 搜 `*.joblib *.pkl *.onnx *.pt *.h5` → 零结果），也没有任何 `joblib.dump` / `pickle` / `save(` 调用；
- 运行时路径**不加载任何校准模型**。`src/psf_reasoner/physical/calibration.py` 的 `HIVProteaseCalibrationProvider` 是一张**硬编码查表**，只匹配一个案例（`V82A` + `MK1`），返回写死的 `value=1.0, confidence=0.70` 定性标签。

报告自身也如实标注：`"calibration_status": "heuristic"`，并在 limitations 中写明「This calibration label is qualitative; it is not a numeric Ki, Kd, or IC50 value.」

### 7.2 重跑 validity_audit 与既有结果比对 → **不一致**

```
$ python -c "from psf_reasoner.calibration.validity_audit import run_full_validity_audit; run_full_validity_audit('/tmp/audit_rerun')"
耗时 0.57 秒
```

与 `pilot_validity_audit/` 已提交快照逐文件 diff，**6 个文件全部不同**：

| 文件 | 快照 | 重跑 |
|---|---|---|
| `ablation_metrics.json` | M0 accuracy 0.767 / n_errors 7 | 0.889 / n_errors 1 |
| `target_masked_results.json` | 全模型 accuracy 0.9, MCC **0.711**；掩蔽 MCC 0.441 | accuracy 1.0, MCC **1.0**；掩蔽 MCC 1.0 |
| `missingness_baseline.json` | accuracy 0.767 | 0.889 |
| `complete_subset_results.json` | **n=30**, label_dist 23decrease/7increase | **n=9**, 8decrease/1increase |
| `leave_one_protein_out.csv` | **5 个蛋白折**（P00374/P00519/P00533/P03367/P62593） | **2 个蛋白折**（P00374/P03367） |
| `case_error_analysis.json` | 2408 字节，3 条错误 | **2 字节（`[]`，空）** |

**根因**：`build_feature_matrix()` 现在只产出 **9 个样本**（`n_samples: 9`），因为数据集重建后只剩 9 条 accepted 案例，而快照是在旧的 30 案例数据集上算出来的。

> **结论：`pilot_validity_audit/` 下的全部发布数字都是陈旧快照，对应的数据集已被项目自己推翻。** 其中被反复引用的「MCC 0.711」「结构特征独立贡献（掩蔽 MCC 0.441）」「LoPo 无跨蛋白泛化」等结论，**当前代码无法复现**，不应再作为科研结论引用。（`_lopo_to_csv` 写 `leave_one_protein_out.csv` 后立刻用同样内容覆盖 `fold_metrics.csv`，两个文件本就同名同源。）

### 7.3 唯一被运行时引用的文献断言 — **独立核实为真**

`physical/calibration.py` 引用的 `PubMed 15066177` / DOI `10.1111/j.1432-1033.2004.04060.x`，经独立网络检索核实：

- **PMID 15066177** = Mahalingam B, Wang Y-F, Boross PI, Tozser J, Louis JM, Harrison RW, Weber IT. *"Crystal structures of HIV protease V82A and L90M mutants reveal changes in the indinavir-binding site."* Eur J Biochem **271**(8):1516–1524, 2004.
- 该文确实报道 V82A 对 indinavir 的 **Ki 升高 3.3 倍**（与代码中 3.3-fold 的说法一致）。
- 该文的 PDB 条目 **1SDT = 野生型 PR、1SDU = L90M、1SDV = V82A**，与 `examples/data/` 中的文件完全对应。

**这是本次验证中少见的、经得起外部核对的科学断言，且引用完全正确。**

---

## 8. API 冒烟测试

```
$ nohup .venv-verify/bin/python -m uvicorn psf_reasoner.api.app:app --host 127.0.0.1 --port 8101 &
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8101

GET  /health  → HTTP 200  {"status":"ok"}
GET  /docs    → HTTP 200
```

### 8.1 V3 端点：曾 500，被并发修复

首次 `POST /v3/analyze` **返回 500**：

```
File "src/psf_reasoner/physical/identity.py", line 77, in extract_protein_identity
    if any(keyword in text for keyword in keywords):
AttributeError: 'gemmi.ResidueSpan' object has no attribute 'entity_type'
```

（`identity.py` 于 19:34:07 被并发修改后，重启服务再测）

```
POST /v3/analyze → HTTP 200, 80357 bytes, report_id=report-bc364fd422dc
```

V2 端点 `POST /analyze` 在同一时间窗内**始终正常**：`HTTP 200, 71600 bytes`，`confidence 0.656`，4 个机制。

### 8.2 服务已停止

验证结束后 `pkill -f "uvicorn psf_reasoner.api.app:app"`，确认进程已退出。

---

## 9. 独立科学正确性核验（不经过项目代码）

用 `gemmi` 直接读 `examples/data/1sdt.cif` / `1sdv.cif` 自行计算，与项目输出比对：

| 检查项 | 项目声称 | 我的独立计算 | 结论 |
|---|---|---|---|
| WT 突变位点残基 | `A:VAL82` | `1sdt` chain A resi 82 = **VAL** | ✅ |
| 突变体残基 | `mutant_residue_name = ALA` | `1sdv` chain A resi 82 = **ALA** | ✅ |
| 最近重原子距离 | `3.782 Å`（`A:VAL82:CG2 → B:MK1902:C16`） | **3.782 Å**（CG2 → C16），去 altloc/氢后 | ✅ 精确一致 |
| 4 Å 邻域 | `['A:PRO81','A:ASN83','A:THR80','A:ILE84']` | 以 A:VAL82 为圆心 4.0 Å 内的残基 = 同样 4 个（ASN83 1.319 / PRO81 1.318 / THR80 2.705 / ILE84 3.526 Å） | ✅ 完全一致 |
| 配体 | `MK1` 存在于两个结构中 | `1sdt`/`1sdv` 均含 `B:902 MK1` | ✅ |

**这些是真实的、可独立复算的结构事实，不是形式化断言。** 项目的结构解析与几何计算层（`physical/coordinates.py` 等）在本例中给出了正确结果。

---

## 10. 测试质量评估

方法：通读 R1 的 17 个测试文件（128 用例）逐文件判定；`test_api.py` / `test_llm_reasoner.py` / `test_evaluation_metrics.py` / `test_external_validation.py` 逐用例核对。

### 10.1 分文件评级表

| 测试文件 | 用例数 | 测了什么 | 实质意义评级 |
|---|---|---|---|
| `test_interactions.py` | 9 | 相互作用分类/计数的真实计算 | **科学有效** |
| `test_coordinates.py` | 5 | 真实 `1hsg.cif` 的距离计算（3.635 Å 等） | **科学有效**（4/5） |
| `test_comparison.py` | 8 | 真实 `1sdt`+`1sdv` 配对比较（Δ0.315 Å 复算一致） | **部分科学有效**（2/8），5 形式、1 永真 |
| `test_reasoning.py` | 3 | 双向链条一致性（依赖 LLM 输出） | 1 有效 / 2 形式 |
| `test_preparation.py` | 4 | 结构准备 | 1 有效、1 形式、**2 不可证伪** |
| `test_evaluation.py` | 23 | 基准加载与指标 | **全形式**（仅断言 version/计数） |
| `test_evaluation_metrics.py` | 9 | 见 §10.2 | **全形式，0 科学有效** |
| `test_external_validation.py` | 8 | 见 §10.2 | **全形式，0 科学有效**（1 跳过） |
| `test_llm_reasoner.py` | 12 | 见 §10.2 | **全部 mock** |
| `test_api.py` | 8 | HTTP 状态/字段 | 7 形式、1 永真 |
| `test_batch.py` | 8 | 批处理状态 | 7 形式、1 永真 |
| `test_cli.py` | 2 | CLI 退出码 | 形式 |
| `test_ports.py` | 13 | 异常继承、Protocol 形状 | 10 形式、3 永真 |
| `test_schemas.py` | 3 | Pydantic 校验 | 形式 |
| `test_uploads.py` | 11 | 上传/路径处理 | 形式 |
| `test_infrastructure.py` | 2 | 报告持久化 | 形式 |

**汇总（R1 的 128 用例）：科学有效 ≈ 17（13%）、纯形式 ≈ 82（64%）、mock 12（9%）、不可证伪 ≈ 16（13%）、跳过 1。**

### 10.2 三个被点名文件的具体内容

**`tests/test_evaluation_metrics.py`（9 用例，0 科学有效）**
- `test_empty_mechanisms` / `test_empty_results` / `test_empty_results_note` / `test_summary_empty_results`：只调用真实函数的**空输入分支**，断言 `n_cases == 0`、`brier_score is None`、`mrr == 0.0`。
- `test_bin_centers_cover_0_to_1`：**手工构造** 5 个 `CalibrationBin` 字面量，再断言 `len(bins) == 5`——断言的是测试自己刚塞进去的数据，`compute_calibration_analysis` 的真实分箱逻辑从未被数据驱动过。
- `test_summary_with_matching_types`：把 `mechanism_types_match=True` 硬编码进输入，再断言 rate 是 `1.0`、`mean_jaccard==0.5`。
- `test_comparison_without_llm` / `test_reasoner_output_fields`：断言 Pydantic 默认值回显。
- **核心匹配逻辑 `_match_by_interaction_changes` 全无覆盖**；它依赖的 `expected_interaction_changes` 在所有 benchmark 文件中都是空数组（`docs/TODO.md` 自述「currently empty」），即**核心排序指标在真实数据上零覆盖**。

**`tests/test_external_validation.py`（8 用例，0 科学有效，1 跳过）**
- 该模块的**存在意义**是把 PSF 的相互作用引擎与外部金标准 PLIP 对比。但：
  - `TestPerTypeAgreement::test_match_when_counts_equal` / `test_mismatch_when_counts_differ`：构造 `PerTypeAgreement(match=True/False)` 然后断言 `.match is True/False`——**读回自己刚构造的数据类字段，不可能失败**。
  - `test_total_agreement_rate`：在 `by_type` 里硬编码 `match=True/False`，断言 `1/2 == 0.5`。`compare_interactions` 的真实匹配逻辑从未运行。
  - 两个 `test_graceful_*` 走异常吞没路径，**即使整个引擎坏掉也会通过**。
  - `test_runs_with_plip_when_available`：**被跳过**（PLIP 未安装，且 PLIP 需 Python ≤3.12，本环境 3.14 永远装不上）；即便运行也只断言 `isinstance(result.total_agreement_rate, float)`。
- **结论：对外部金标准的真实一致率，在整个测试套件中从未被计算过一次。**
- 附带潜在缺陷：PLIP 缺失时 `plip_counts = {}`，代码与默认值 `-1` 比较，会把每种相互作用都记为 mismatch，产生一个看起来像科研结果、实为人为产物的「0% 一致率」。无测试覆盖此路径。

**`tests/test_llm_reasoner.py`（12 用例，全部 mock）**
- **LLM 如何被伪造**：测试文件内手写 `_MockProvider` 类（24–42 行），通过**构造函数注入**传给 `LLMForwardReasoner(_MockProvider())`。**不是** `monkeypatch`、**不是** `unittest.mock`、**不是**环境变量。
- `_MockProvider.complete()` **忽略全部入参**，直接返回写死的 `LLMCompletion(content=self._canned, model="mock-model")`，`_canned` 是测试文件里硬编码的中文 HIV-1 蛋白酶文本。
- **该文件不可能发生真实网络调用**（不构造任何触碰 httpx/anthropic 的 provider）。但 `_MockProvider.calls` 记录了 prompt 却**没有任何一个测试断言 prompt 内容**（system prompt、证据序列化、传给模型的 schema 均未被检查）。
- 12 个用例做的事：把写死的 dict 喂进去，再断言拿回来的 `len()==2`、类型是 `POCKET_PACKING`、`direction=='decrease'`——**断言的是测试自己的 fixture**。
- 典型问题用例 `test_all_ids_are_stable_and_traceable`（名为「可追溯性」测试）：它断言 hypothesis 的 `supports` 以 `"mechanism-"` 开头、`related_claims ⊆ claim_ids`。但 fixture 里的 `mechanism_ids: ["mechanism-placeholder-001"]` 是一个**悬空引用**（真实生成的 id 是 `mechanism-85de00d36080` 等），测试却从不校验 `supports` 是否真的落在 `mechanism_ids` 内——**一个编造出来的引用可以顺利通过「可追溯性」测试**。
- 真正有意义的只有 3 个：两个早退分支（无 mutation / 无 phenotype 返回空）和 `TestEvidenceInterpreter::test_formats_computed_evidence`（断言 prompt 格式化字符串含 `"3.635"` 和 `"angstrom"`）——而后者测的是字符串格式化，不是推理。

### 10.3 不可证伪 / 明显有问题的断言

| 位置 | 断言 | 问题 |
|---|---|---|
| `test_preparation.py` | `assert len(preparation[0].issues) >= 0` | 恒真（注释自认「may or may not have issues」） |
| `test_preparation.py` | `pytest.raises(Exception)` | 任何异常都过 |
| `test_batch.py::test_successful_batch` | `assert result.jobs[0].status in ("success","error")` | 注释自认存在「pre-existing molecular_dynamics bug」；管线全挂也能过 |
| `test_api.py::test_forward_endpoint_rejects_bidirectional_request` | `assert response.status_code in (400, 422)` | 测试内注释承认实际是因缺少 upload 返回 400，**不是**因为双向请求被拒——名不副实 |
| `test_ports.py::TestApplicationExceptions`（3 个） | 在 `pytest.raises` 里手动 raise | 测的是 Python 异常继承，不是产品 |
| `test_ports.py`（多个） | `hasattr(Protocol, "method")` | 形状检查 |
| `test_evaluation_metrics.py::test_empty_results` vs `test_empty_results_note` | 同一次调用的重复断言 | 冗余 |

### 10.4 硬编码标识符与「错误 PMID 能否通过」的正面回答

测试中出现的硬编码 PMID：`test_evaluation.py:34,38` 的 `"12345678"`（明显的假占位符，**从未被断言**）、`test_evaluation_metrics.py:38` 的 `"12345678"`（同样未被断言）。

新增的 4 个测试文件提高了标准，出现了真实的 allowlist/denylist：

```
tests/test_literature_integrity.py:41  assert entry.pmid in {"15066177", "18597780"}
tests/test_literature_integrity.py:63  assert entry.pmid == "15066177"
tests/test_data_integrity.py:68        assert case.pmid in VERIFIED_PMIDS   # 7 个字面量
tests/test_data_integrity.py:68        KNOWN_BAD_PMIDS  # 18 个字面量，附人工注释
```

**对「引用了错误 PMID 的案例能否照样通过测试」的正面回答：能。** 这些是**对一份人工审计过的数据集的锁定（allowlist/denylist）**，不是对引用内容的验证。没有任何测试会去解析 PMID、DOI 或 UniProt 记录以确认论文内容与所支撑的断言相符。如果 PMID 15066177 实际上是环孢素 A 的论文，**全部 156 个测试仍会通过**，除非有人手动把它加进 denylist。DOI 字段在任何断言中**从未出现**。任何测试断言中都不含 UniProt accession、EC 号或药物名；`"MK1"` 始终只作为一个不透明字符串使用。

真正做了「内容 vs 声称」核验的只有少数几个（属于 R2 新增）：
- `test_data_integrity.py::test_verified_structure_pairs_have_matching_ligand`：用 gemmi 解析真实 mmCIF，断言声称的配体（`MK1`）确实以 HET 残基存在——**这是真实的证据核对**（我在 §6.2 用同样思路独立复现了它的价值）。
- `test_v3_api.py::test_v3_analyze_includes_identity_from_structure`：从真实结构推导 protein identity 并断言 `family_hint == "HIV-1_PROTEASE"`。

### 10.5 覆盖率缺口

49 / 90 个源码模块从未被任何测试引用，包括 `calibration/calibrator.py`、`calibration/train_pilot.py`、`calibration/grouped_cv.py`、`knowledge/entity_normalizer.py`、`knowledge/evidence_ranker.py`、`datasets/deduplicator.py`、`datasets/unit_normalizer.py`、两个 LLM provider 适配器。**最需要被验证的校准/统计层，覆盖率是零。**

---

## 11. 总结

### 11.1 可以标为「已运行核实」的内容

| 项目 | 核实结论 |
|---|---|
| 干净 venv 安装 | ✅ 成功（Python 3.14.7 + `pip install -e '.[dev]'`，无报错） |
| 测试套件在确定性环境下通过 | ✅ 指纹 `132a3368…`，**155 passed / 1 skipped / 0 failed，1.45s** |
| 真实测试数量 | ⚠️ 当前 156 个用例；R1 时 128 个（127 通过 + 1 跳过）。**「128 个测试全部通过」字面不成立**（有 1 个跳过） |
| 确定性基线分析可复现 | ✅ 两次运行除 `generated_at` 外逐字节一致 |
| 结构解析与几何计算 | ✅ **独立复算一致**：3.782 Å、4 Å 邻域 4 残基、WT=VAL/MUT=ALA 全部精确吻合 |
| JSON / CSV / PyMOL 导出 | ✅ 三者均生成成功、可解析，内容与页面数据一致（CSV 53 行与报告计数完全对应） |
| API 冒烟 | ✅ `/health` `/docs` `/analyze` `/v3/analyze` 均 200 |
| 唯一运行时文献断言 | ✅ PMID 15066177 = Mahalingam 2004，内容与引用相符，且正确对应 1SDT/1SDU/1SDV |
| 数据集诚实性 | ✅ 项目已自行把 113 条问题案例降级 rejected，并在 `PROJECT-STATE.md` 加审计横幅；`HIV_V82A_DRV` 的配体不匹配经我独立确认并已被正确拒绝 |

### 11.2 存疑 / 不可作为科研有效性证明的内容

| 项目 | 问题 |
|---|---|
| **「128 个测试全部通过」** | 实际 127 通过 + 1 跳过；且验证期间测试数变为 156、出现 6 个失败又被修复。**仓库在被验证的同时被改写，任何静态数字都会过期** |
| **默认配置下分析不可复现** | `PSF_LLM=1` 时同一命令两次运行有 **235 处字段差异**，机制数量、假设类型、confidence 全不同。不可复现的报告不可审计 |
| **测试默认打真实网络** | 环境含 `PSF_LLM=1`/`DEEPSEEK_API_KEY`/`PSF_CLOUD_URL`，约 20 处测试用默认工厂 → 实测同一测试 50.70s vs 0.01s（5070×）。**同一套测试在不同环境下测的是完全不同的代码路径**，CI 通过不代表本地行为 |
| **`pilot_validity_audit/` 全部数字** | 6/6 文件无法复现；样本量 30→9、MCC 0.711→1.0、蛋白折 5→2、错误分析 3 条→空。**「MCC 0.711」等结论已被项目自己的数据重建推翻，属陈旧快照** |
| **校准层** | 无任何序列化模型文件，运行时也不加载模型；`physical/calibration.py` 是单个案例的硬编码查表（自标 `heuristic`）。**「校准」目前只是命名，不是已训练的模型** |
| **「118 个金案例」** | 实测 127 条，其中 accepted 仅 **9** 条、有结构对 **3** 条、有 ΔΔG **1** 条。`PROJECT-STATE.md` 第 136 行仍留旧数字未清理 |
| **`test_llm_reasoner.py` 的 12 个测试** | 全部 mock，`_MockProvider` 忽略入参返回写死内容；「可追溯性」测试在存在悬空引用的情况下仍通过 |
| **`test_external_validation.py`** | 与 PLIP 的真实一致率**从未被计算过**；关键用例断言自造数据类字段、不可能失败；唯一真实对比用例因 PLIP 与 Python 3.14 不兼容而永久跳过 |
| **「函数数量 / 模块名称」类证据** | 本项目 `physical/` 下确有 12 类计算器、`reasoning/` 下确有多个模块，但**模块的存在与其科学有效性无关**；`evaluation_metrics.py` 的核心匹配逻辑在真实数据上零覆盖即为例证 |
| **`pair_builder`** | 全仓库零调用，死代码 |
| 代码库稳定性 | 验证期间 `src/` 与 `tests/` 被并发修改至少 5 次，**建议在声明任何「已完成/全部通过」之前先冻结修订版本** |

### 11.3 给用户的一句话结论

工程层面：安装、CLI、API、导出、结构解析与几何计算**确实能运行且结果正确**（3.782 Å 与 4 Å 邻域经我独立复算精确吻合，这是真实的科学计算）。
科研层面：**目前不具备可复现性**——默认 LLM 路径同一输入两次产出不同科学结论；校准层没有已训练模型；全部已发布的校准指标（MCC 0.711 等）在当前数据集上无法复现；测试套件中约 87% 的用例是形式化或 mock 断言，且默认会打真实网络。**「V3 已完成」「128 测试全通过」「118 金案例」三个说法经实测均需修正。**

---

*本记录中所有数字均来自实际执行的命令输出；未执行的部分（如 PyMOL 脚本实际运行、PLIP 对比）已明确标注为未核实。*
