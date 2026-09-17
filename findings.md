# Findings

## Initial State

- The project directory was confirmed empty.
- It was not initialized as a Git repository. [HISTORICAL — resolved 2026-07-13: repo initialized with 17 commits on `main` as of 2026-07-14.]
- The user approved implementation of a clean first foundation after reviewing the phased plan.

## Scientific/Product Constraints

- The core report must support both Physical -> Structural -> Functional and Functional -> Structural -> Physical reasoning.
- Every conclusion needs provenance, confidence, limitations, and an explicit path to validation.
- The first case is HIV-1 protease with an inhibitor and V82A, but the domain model must not encode that protein as a special case.
- Real calculators will arrive incrementally, so calculator output contracts must be stable before implementations are sophisticated.

## Engineering Constraints

- CLI and API must share one framework-neutral application service.
- Local synchronous execution is the first adapter; future workers and storage systems should implement narrow protocols.
- The baseline must distinguish inferred/expected evidence from measured evidence.

## Structure Calculation Phase

- No structure parser is installed in the project environment.
- `gemmi` is selected for robust PDB/mmCIF parsing and coordinate access.
- The first real evidence slice will report only observed coordinates and deterministic geometry:
  ligand localization, mutation-residue localization, nearest atom distance, and
  residue-ligand contacts. It will not construct a V82A mutant model.
- A compact synthetic PDB fixture will test exact geometry. A separate real-format
  HIV-1 protease fixture will be added only when its provenance can be recorded.

## Implemented Geometry Slice

- RCSB PDB 1HSG was added as an mmCIF regression fixture with recorded provenance.
- In 1HSG, MK1 is located at chain B residue 902. The V82 mutation maps to Val82
  in both protein chains when no chain is supplied.
- The coordinate provider reports the nearest heavy-atom distance and a contact
  when the distance is at or below the declared 4.0 Angstrom cutoff.
- For the 1HSG fixture, the nearest V82-to-MK1 distances are 3.635 Angstrom for
  chain A and 3.905 Angstrom for chain B. These are parser/geometry regression
  values, not claims about mutant-induced changes.

## Paired Comparison Phase

- `AnalysisRequest` will retain `structure` as the reference (WT) input and add an
  optional `mutant_structure` input to preserve backward compatibility.
- Comparison is only emitted when an explicit mutant structure is supplied.
- Mutant and reference measurements are taken separately around their selected ligand,
  so global coordinate alignment is not required for distance, SASA, or local-shell metrics.
- The first pocket measure is deliberately named a ligand-shell geometry proxy. An
  absolute pocket volume requires a separately validated cavity definition.
- RCSB entries 1SDT and 1SDV form a compatible MK1-bound V82A example pair for
  chain A. The direct comparison must still be interpreted as a structure-pair
  result, not a binding free-energy estimate.

## Next Scientific Roadmap

- The largest current scientific risk is chemical interpretation, not runtime cost.
- Candidate hydrogen bonds and hydrophobic contacts are geometry proxies and should
  be replaced by atom-typed, parameterized interaction rules before adding more cases.
- Structure preparation must record missing atoms, alternate conformations, explicit
  waters, protonation assumptions, and ligand typing because they directly control
  hydrogen-bond, salt-bridge, and energy conclusions.
- Automatic mutation modelling should follow interaction validation so generated
  structures can be assessed with trusted evidence calculations.
- Quantitative function claims require curated affinity/resistance data and confidence
  calibration; fixed rule scores remain hypotheses until that benchmark exists.
- Batch/cloud work should begin only after local per-case workloads and scientific
  reproducibility requirements are measured.

## Evidence-Aware Reasoning Slice

- Structure preparation now records ligand atom typing, explicit waters, alternate
  conformation reduction, missing protein heavy atoms, and preparation assumptions.
- The interaction engine emits typed interaction events and count summaries for
  hydrogen bonds, salt bridges, pi interactions, hydrophobic contacts, and water bridges.
- Pocket evidence now includes an operational ligand-centered residue definition and
  mutation-site residue-network degree deltas.
- The default service can generate conservative local side-chain truncation mutant
  models such as V82A and marks this evidence as modelled computation rather than an
  experimental mutant structure.
- Local interaction scoring is intentionally labelled in local score units and must
  not be interpreted as binding free energy.
- HIV-1 protease calibration is currently qualitative: RCSB 1SDT/1SDV and the
  Mahalingam et al. 2004 primary structure paper support a V82A/MK1 binding-site
  resistance calibration label, but the project does not yet include curated numeric
  Ki, Kd, IC50, or fold-change values.

## 2026-07-13 Implementation Audit

- The workspace still is not a Git repository, so there is no commit history, branch
  state, or diff baseline for assessing change ownership and release readiness.
- The repository contains a Python virtual environment and generated cache/build
  artifacts alongside source, tests, docs, examples, and a local upload directory.
- No `AGENTS.md` file was found in the workspace.
- The maintained Python code and tests total about 4,483 lines; two files dominate
  complexity: `reasoning/baseline.py` (703 lines) and `physical/interactions.py`
  (418 lines), indicating likely refactoring and targeted test needs.
- Documentation is internally inconsistent with the newer implementation: the README
  says a conservative local modeler exists, while `docs/architecture.md` still says
  mutation modelling is only an unconfigured future interface and describes interaction
  categories as initial geometry proxies.
- Several roadmap labels appear stronger than the evidence currently recorded. In
  particular, Phase 23 claims an experimental validation benchmark measuring accuracy,
  ranking, calibration, and failure modes, while the implementation record describes only
  one qualitative V82A/MK1 calibration label with no numeric affinity/resistance data.
- The delivery/application boundaries are clean for an MVP: CLI and FastAPI use the same
  `AnalysisRunner`, execution and report storage are protocols, and scientific services do
  not depend on the delivery frameworks.
- Persistence is process-local only. API reports disappear on restart, execution is fully
  synchronous, there is no job state/manifest, and uploaded structures accumulate in
  `.psf_uploads` without a lifecycle/cleanup policy.
- The JSON API accepts server-side filesystem paths in `AnalysisRequest`. This is useful for
  a trusted local workbench but should not be exposed as a production multi-user API without
  an artifact abstraction and path-access policy.
- Automatic mutation modelling is a deterministic atom-deletion/renaming operation, not a
  general mutation modeller or local relaxation engine. The implementation does not limit
  target residues to true truncation cases, does not add required atoms, and can therefore
  write chemically incomplete larger-side-chain targets. Phase 20 is only a narrow plumbing
  prototype, not complete against its own acceptance criterion.
- Interaction typing remains heuristic. Hydrogen-bond angle checks are skipped when explicit
  hydrogens are absent; ligand bond order/protonation is inferred from distances; aromaticity
  is name/connectivity-based; water bridges use distance-only partner selection. These are
  useful conservative signals, but Phase 18 should be described as a typed baseline requiring
  external validation rather than a validated interaction engine.
- The report exposes heuristic confidence values and explicitly says they are not calibrated
  probabilities. This is scientifically honest, but it also means Phase 22 is only evidence-
  responsive ranking, not calibrated evidence-aware inference.
- Current verification is healthy: all 30 tests pass, Ruff lint and formatting checks pass,
  and line coverage is 93% on Python 3.14.6. The only emitted warning is an upstream
  Starlette/FastAPI TestClient deprecation.
- High line coverage should not be confused with scientific validation. The interaction
  engine has only two focused unit tests; preparation has one; the real 1SDT/1SDV test checks
  two geometric deltas; there are no benchmark metrics, multi-case calibration tests,
  property-based tests, performance tests, persistence/restart tests, or security tests.
- The local workbench is functional and responsive, but it renders only a subset of the
  report. It omits provenance, limitations, causal supports/contradictions, reverse
  candidates, consistency checks, and missing evidence—the very fields that make the
  reasoner auditable.
- The UI displays heuristic report confidence as a percentage without the report's
  non-calibration warning, which can be misread as a probability. Its note says files remain
  only while the service runs, but uploaded files are not deleted; 22 upload artifacts
  (about 80 KB) are already present.
- The built-in example depends on server working-directory-relative paths, so it is not a
  robust packaged/deployed demo yet.
- A warm local paired 1SDT/1SDV analysis averages about 0.291 seconds across ten runs on the
  current machine and emits 20 evidence items, 6 mechanisms, 2 hypotheses, 3 reverse
  candidates, and 5 validation steps. Current per-case runtime does not justify cloud
  execution; batch work should first target reproducibility, manifests, persistence, and
  measured profiling rather than distributed compute.

## 2026-07-14 Phase 26: Gap and Risk Assessment (Corrected)

Gaps are ranked by **impact × urgency × dependency** — a gap that is actively exploitable
or blocks multiple downstream items is ranked higher than one that is isolated.

### Tier 1 — Critical (blocks safety, scientific credibility, or fundamental validation)

**G1. 公网 API 接受任意服务器文件路径 (Public API Accepts Arbitrary Filesystem Paths)**

The JSON API endpoints (`/analyze`, `/forward`, `/reverse`) accept server-side filesystem
paths in `AnalysisRequest.structure.path`. Cloud Run service is deployed and publicly
accessible at `https://psf-cloud-compute-800903726899.us-central1.run.app`. This is a
path-traversal vulnerability in any multi-user or publicly reachable deployment. The
file-upload endpoints bypass this issue, but the JSON endpoints do not.

Impact: blocks any shared or public API usage. Currently exploitable.
Urgency: immediate — the service is deployed.
Dependency: requires artifact abstraction (upload → ID → reference).

**G2. 相互作用引擎未经验证 (Interaction Engine Not Validated)**

Phase 18 is marked complete but the implementation is a typed/heuristic baseline.
Specific unvalidated aspects:
- H-bond geometry: H positions estimated (not observed), angle check uses heavy-atom proxy
  fallback at 90° (vs standard 110° in HBPLUS/DSSP)
- Aromaticity: name/connectivity heuristic, not quantum-chemical or database-derived
- Water bridges: distance-only partner selection, no H-bond geometry on water
- Ligand atom typing: confidence as low as 0.30 for carbon, element-only for O/S without
  neighbors
- No comparison against established tools (HBPLUS, DSSP, Arpeggio, PLIP)

Impact: every downstream mechanism and hypothesis inherits these uncertainties.
Dependency: blocks meaningful benchmark evaluation and mechanism comparison.

**G3. 无校准基准 (No Calibration Benchmark — Pilot Dataset Required)**

Phase 23 is marked complete but the implementation has only one qualitative V82A/MK1
calibration label. There is no curated numeric dataset, no multi-case collection, no
held-out test set, and — critically — no mechanism gold labels. Without mechanism-level
ground truth, it is impossible to:
- Know whether the inference engine ranks mechanisms correctly
- Compare baseline vs LLM reasoning quality
- Assess whether confidence scores carry any signal

Experimental affinity/resistance data (Ki, Kd, IC50, fold-change) measures functional
outcome, not mechanism correctness. A mutation can change binding affinity through
multiple distinct structural mechanisms, and the correct mechanism is not automatically
identified by the functional measurement.

Impact: blocks any claim of mechanism-ranking validity.
Dependency: must be preceded by G2 (interaction validation) so the physical evidence
feeding into the benchmark is itself defensible.

### Tier 2 — High (blocks product readiness and development velocity)

**G4. 突变建模仅支持截断型 (Mutation Modeling: Truncation Only)**

The LocalSideChainMutationModeler removes incompatible atoms but never adds them.
Cannot model gain-of-size mutations (A→V, A→F, any mutation requiring new atoms,
rotamer sampling, or backbone relaxation). Phase 20 is marked complete but is a
truncation-only prototype.

Impact: automatically-generated mutant path unavailable for the majority of clinically
relevant mutations.
Dependency: requires integration with an external modeler or more sophisticated
internal implementation.

**G5. 前端审计字段缺失 (Frontend Omits Audit Fields)**

The web UI does not render: `missing_evidence`, `supports`/`contradicts` causal graph,
full `provenance` (method + parameters), systematic `limitations`, or the
non-calibration warning. The UI displays heuristic confidence as a percentage without
context that it is uncalibrated.

Impact: the primary user-facing output omits the audit trail that distinguishes
PSF-Reasoner from a black-box predictor.
Dependency: none — pure UI work.

**G6. 文档不一致 (Documentation Drift)**

`docs/architecture.md` describes LLM reasoners as "future," mutation modeling as
"future interface," and electrostatics as "future." All three are now implemented
(at prototype level). README is more current but still incomplete.

Impact: new contributors/collaborators would underestimate capabilities.
Dependency: none.

**G7. 无 CI/CD (No CI/CD Pipeline)**

No GitHub Actions, no automated test runs on push, no Docker build verification for
the cloud service, no lint/format enforcement in CI. Cloud Run is deployed: any push
could break the deployed service without automated signal. This was previously
classified as Tier 4 (later-stage) but is urgent given the deployed Cloud Run service.

Impact: regressions can reach the deployed service undetected.
Dependency: none (setup is mechanical).

**G8. 置信度未校准且方法论需审慎设计 (Confidence Not Calibrated — Methodological Caution Required)**

The report honestly states confidence is heuristic and uncalibrated. However, the
previous roadmap proposed Platt scaling or isotonic regression on ~10 pilot cases to
"replace" heuristic confidence. This is methodologically premature:
- ~10 cases cannot support distribution-level calibration
- Pilot cases are not an independent held-out set
- Mechanism labels are not yet externally validated
- Ki/Kd/IC50 cannot be pooled as a single absolute scale

Impact: confidence values cannot be interpreted as probabilities.
Dependency: requires G1 benchmark protocol, G2 external interaction validation,
and a frozen held-out set of sufficient size before any calibration is attempted.

### Tier 3 — Medium (blocks robustness and scale)

**G9. LLM vs Baseline 推理无对比框架 (No Reasoning Comparison Framework)**

No systematic comparison methodology, no shared test cases with mechanism ground truth,
no inter-rater agreement metrics. Current test suite only checks that LLM output is
structurally valid JSON. Comparison must depend on a frozen benchmark with mechanism
labels (not just functional outcomes) and externally validated physical evidence.

Impact: cannot assess whether LLM improves or degrades reasoning quality.
Dependency: depends on G2 (interaction validation) and G3 (benchmark with mechanism labels).

**G10. 测试覆盖有盲区 (Test Coverage Blind Spots)**

55 tests / 93% line coverage masks gaps: interaction engine has 2 tests, preparation has
1 test, no property-based tests, no edge-case tests (empty structures, all-glycine, no
ligand), no security tests (path traversal, malicious PDB), no persistence/restart tests.

Impact: regressions in critical paths could go undetected.
Dependency: none.

**G11. 上传文件累积 (Upload Artifact Accumulation)**

`.psf_uploads` has 90 entries. Cleanup mechanism exists but effectiveness unverified.

Impact: disk space grows unbounded if cleanup is not working.
Dependency: none.

### Tier 4 — Lower (nice-to-have, deferred)

**G12. 无批量执行** — Phase 24 explicitly deferred.
**G13. 单点蛋白质家族** — HIV-1 protease only; kinases, GPCRs untested.
**G14. web 工作台示例依赖服务器路径** — Fails in packaged/deployed contexts.

### Risk Matrix (Corrected)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Path traversal on deployed Cloud Run API | Low (single-user now) | Critical | N0: artifact abstraction + upload-ID-only API |
| Interaction engine produces false negatives | Medium | High | M1: validate against PLIP/Arpeggio before benchmark freeze |
| Mechanism ranking evaluated without ground truth | High | High | N1A+N1B: protocol + pilot dataset with mechanism labels |
| Confidence numbers misinterpreted as probabilities | High | Medium | M2 gate criteria: stay uncalibrated until held-out set and external validation complete |
| Cloud Run regression from unreviewed push | Medium | High | N0: GitHub Actions CI + Docker build check |
| LLM generates plausible but wrong mechanisms | Medium | High | M3: comparison against frozen benchmark with mechanism labels |

## 2026-07-14 Phase 27: Executable Next-Stage Roadmap (Corrected)

### Corrected Dependency Order

```
N0 (security + CI)
  → N1A (benchmark protocol + schema design)
  → N1B (pilot dataset curation with mechanism labels)
  → M1 (external interaction validation against PLIP/Arpeggio)
  → 根据外部验证结果修正物理规则
  → 冻结 formal benchmark + held-out set
  → M3 (Baseline vs LLM comparison)
  → 评估样本量是否支持校准 → M2 (calibration evaluation, exploratory only)
```

### Near-Term (2-4 weeks): Safety Foundation + Scientific Protocol Design

---

**Sprint N0. 安全加固 + 基础 CI (Security Hardening + Basic CI)** ← addresses G1, G7

Priority: **最高. Must complete before any other sprint.** Cloud Run 已部署,
公开 API 接受任意文件路径是不可接受的风险。

Acceptance criteria:

N0A — API 安全:
- JSON API endpoints (`/analyze`, `/forward`, `/reverse`) no longer accept server-side
  filesystem paths in `structure.path` or `mutant_structure.path`
- Endpoints accept only: (a) multipart file upload, or (b) a previously-uploaded
  artifact ID
- `StructureInput` gains optional `upload_id: str | None` field; when present,
  the path is resolved from the upload store, not the filesystem
- Path traversal tests added: `../../etc/passwd`, absolute paths, symlink attacks
- Malformed PDB/CIF uploads return 422, not 500

N0B — Cloud Run 安全审查:
- Verify Cloud Run IAM configuration: who can invoke the service?
- Confirm authentication status (public / IAM-gated / API-key)
- Document the current exposure surface in `cloud/SECURITY.md`
- If service is publicly invokable, add minimum protection (even a shared secret
  header check is better than wide open)

N0C — 基础 CI:
- `.github/workflows/ci.yml`: pytest + ruff format --check + ruff check on push/PR
- `.github/workflows/cloud-build.yml`: Docker build verification for `cloud/Dockerfile`
  (does not need to push/deploy, just verify the build succeeds)
- CI runs on Python 3.12 (reference runtime)
- Both workflows must pass before any future PR merge

Files to create/modify:
- `src/psf_reasoner/api/app.py` — strip filesystem path acceptance, add upload ID resolution
- `src/psf_reasoner/schemas/inputs.py` — `StructureInput.upload_id`
- `src/psf_reasoner/infrastructure/uploads.py` — `resolve_upload(upload_id) -> Path`
- `tests/test_api.py` — path traversal, malicious upload, upload-ID flow tests
- `.github/workflows/ci.yml` — new
- `.github/workflows/cloud-build.yml` — new
- `cloud/SECURITY.md` — new

---

**Sprint N1A. 基准协议与 Schema 设计 (Benchmark Protocol & Schema Design)** ← addresses G3

Prerequisite: N0 complete.
Priority: 必须先于任何数据整理,确保协议能区分 functional outcome 和 mechanism label.

Acceptance criteria:

Benchmark data schema (per case):
```python
class BenchmarkCase:
    # --- Identity ---
    case_id: str  # e.g. "hiv1-v82a-mk1"
    protein_family: str  # e.g. "HIV-1_protease"
    protein_uniprot: str | None  # optional

    # --- WT structure ---
    wt_pdb_id: str  # e.g. "1SDT"
    wt_chain: str
    wt_mutation_background: list[str]  # background mutations relative to reference

    # --- Mutant structure ---
    mutant_pdb_id: str | None  # None if mutant is modelled only
    mutant_source: str  # "experimental" | "modelled" | "unknown"
    mutation_notation: str  # e.g. "V82A"
    mutation_chain: str

    # --- Ligand ---
    ligand_identifier: str  # e.g. "MK1"
    ligand_chain: str | None

    # --- Functional outcome (experimental) ---
    assay_type: str  # e.g. "IC50", "Ki", "Kd", "fold_change"
    assay_conditions: str  # e.g. "pH 4.7, 25°C, 0.1 M NaCl"
    wt_value: float
    wt_unit: str
    mutant_value: float
    mutant_unit: str  # must match wt_unit
    fold_change: float | None  # computed or reported
    direction: str  # "increase" | "decrease" | "unchanged"
    phenotype: str  # e.g. "drug_resistance", "activity_loss"

    # --- Literature provenance ---
    pmid: str
    doi: str | None
    source_table_or_figure: str  # e.g. "Table 2, row 3"
    notes: str  # free-text: any caveats, data extraction notes

    # --- Mechanism label (expert-curated, separate from functional outcome) ---
    mechanism_label: str | None  # e.g. "loss of hydrophobic packing at S1 pocket"
    mechanism_evidence: str  # "literature" | "structural_analysis" | "expert_review" | "none"
    mechanism_source: str | None  # e.g. "PMID:12345678, Figure 4"
    mechanism_review_status: str  # "unreviewed" | "single_reviewer" | "consensus"
    mechanism_confidence: float  # 0.0-1.0, curator's confidence in this label

    # --- Exclusion flags ---
    excluded_from_calibration: bool  # True if data quality issues, background mutations, etc.
    exclusion_reason: str | None
```

Key design decisions encoded in the schema:
- **Functional outcome and mechanism label are separate fields.** Ki/Kd/IC50 values
  do not automatically prove any particular structural mechanism.
- **Fold-change direction is recorded alongside absolute values.** Different assays
  (Ki vs IC50 vs Kd) measure different things and MUST NOT be pooled as a single
  absolute numeric scale.
- **Assay conditions are mandatory.** pH, temperature, and buffer composition affect
  affinity measurements and limit cross-case comparability.
- **Background mutations are explicit.** HIV-1 protease clinical isolates often carry
  multiple mutations; the benchmark must record which mutations are present beyond
  the primary one under study.
- **Mechanism label tracks review status.** A label from literature is different from
  a label the curator assigned by inspection; both are different from a consensus
  multi-reviewer label.
- **Exclusion flags** allow cases to be in the dataset without contaminating evaluation.
  A case with 4 background mutations and uncertain mechanism may still be useful for
  qualitative inspection.

Evaluation protocol (separate from data):
- `evaluation/benchmark_runner.py`: loads `BenchmarkCase` list, runs each through
  the full pipeline, collects `PSFReport`
- `evaluation/metrics.py`: mechanism ranking metrics (top-N accuracy, mean reciprocal
  rank, mechanism agreement with label where mechanism_label is not None)
- `evaluation/comparison.py`: side-by-side Baseline vs LLM comparison on the same cases
- NOT in `physical/` — evaluation is a separate domain from physical evidence computation

Files to create:
- `src/psf_reasoner/evaluation/__init__.py`
- `src/psf_reasoner/evaluation/protocols.py` — `BenchmarkCase` dataclass, `BenchmarkDataset`
- `src/psf_reasoner/evaluation/benchmark_runner.py`
- `src/psf_reasoner/evaluation/metrics.py`
- `src/psf_reasoner/evaluation/comparison.py`
- `benchmarks/README.md` — data documentation, curation standards
- `tests/test_evaluation.py` — verify loading, runner, metrics on synthetic data

---

**Sprint N1B. Pilot 数据整理 (Pilot Dataset Curation)** ← addresses G3

Prerequisite: N1A complete (schema frozen).
Priority: 产生首批可用于评估的数据,但必须明确标注为 pilot。

Acceptance criteria:
- ≥10 HIV-1 protease mutation cases curated into `benchmarks/hiv1_protease/pilot.json`
- Each case follows the N1A BenchmarkCase schema
- At least 5 cases have mechanism labels with evidence source (literature or
  structural analysis)
- At least 3 cases are excluded from quantitative evaluation with documented reasons
- Each case has PMID/DOI and source table/figure reference
- Ki/Kd/IC50 values are recorded in their original units with assay conditions —
  NOT normalized to a single scale
- The dataset is explicitly labelled as **pilot** — not "benchmark," not "gold standard"
- A `benchmarks/hiv1_protease/pilot.md` documents: search strategy, inclusion/exclusion
  criteria, known limitations, and the distinction between functional outcome labels
  and mechanism labels

Files to create:
- `benchmarks/hiv1_protease/pilot.json`
- `benchmarks/hiv1_protease/pilot.md`
- `benchmarks/hiv1_protease/README.md` — family context, known biases

---

**Sprint N2. 前端审计追踪补全 (Web UI Audit Trail)** ← addresses G5

Acceptance criteria: (unchanged from previous version — still valid)
- Report renders `missing_evidence` section
- Report renders `supports`/`contradicts` causal links
- Claim cards expand to show full `provenance`
- Calibration warning: "置信度为启发式排序值，非校准概率。"
- Confidence badge uses color scale instead of raw percentage

Files to modify:
- `src/psf_reasoner/api/static/app.js`
- `src/psf_reasoner/api/static/styles.css`

---

**Sprint N3. 文档刷新 (Documentation Refresh)** ← addresses G6

Acceptance criteria:
- `docs/architecture.md`: mark LLM reasoners as implemented (prototype), mutation
  modeling as truncation-only prototype, document Cloud Run architecture
- `README.md`: add cloud pipeline, DeepSeek, reverse-mode UI, H-bond estimation, i18n
- Phase statuses for 18/20/22/23 accurately reflect partial/prototype implementation

Files to modify:
- `docs/architecture.md`
- `README.md`
- `task_plan.md` (already corrected in this round)

---

**Sprint N4. 关键测试缺口补全 (Critical Test Gap Closure)** ← addresses G10 (partial)

Acceptance criteria: (unchanged from previous version)
- Interaction engine: ≥8 tests covering all types + edge cases
- Preparation inspector: ≥3 tests
- Security tests: path traversal, malicious upload (added scope from N0)

---

**Sprint N5. 上传清理验证 (Upload Cleanup Verification)** ← addresses G11

Acceptance criteria: (unchanged from previous version)

---

### Mid-Term (1-3 months): Scientific Validation

These items depend on near-term completion and must proceed in the corrected dependency order.

---

**Sprint M1. 相互作用引擎外部验证 (External Interaction Validation)** ← addresses G2

Prerequisite: N1A (protocol), N1B (pilot data), N4 (interaction tests).
Must complete BEFORE benchmark freeze and before any mechanism-level comparison.

Acceptance criteria:
- Run PLIP and/or Arpeggio on the structures in the pilot dataset
- Compare interaction counts by type (H-bond, salt bridge, hydrophobic, pi, water bridge)
  between PSF-Reasoner and each reference tool
- Document per-type agreement rates and systematic differences
- Where PSF-Reasoner systematically disagrees with ≥2 reference tools, adjust
  parameters (cutoffs, angle thresholds, typing rules)
- Re-run pilot dataset through corrected interaction engine
- Publish comparison table in `docs/interaction-validation.md`

New dependency: PLIP (`pip install plip`) or Arpeggio web service

---

**Sprint M1b. 基准冻结 (Formal Benchmark Freeze)** ← new sprint

Prerequisite: M1 complete (physical evidence validated externally).

Acceptance criteria:
- Pilot dataset expanded or pruned to a formal benchmark
- Mechanism labels reviewed by at least one additional reviewer (or consensus review)
- Held-out test set split from training/development cases
- Split strategy documented: mutation-level split (same mutation's WT/mutant structures
  must go to the same split); structure-family-level split preferred to avoid
  data leakage across closely related PDB entries
- Benchmark versioned (`v1.0.0`) with frozen hash and changelog
- No further changes to cases, labels, or splits without version bump

Files to modify:
- `benchmarks/hiv1_protease/` — move pilot → formal, add split metadata

---

**Sprint M2. 置信度校准评估 (Confidence Calibration Evaluation)** ← addresses G8

Prerequisite: M1b (frozen benchmark with held-out set).
Methodology constraint: this is an EXPLORATORY evaluation, not a calibration deployment.

Acceptance criteria:
- Run the frozen benchmark through the pipeline; collect heuristic confidence values
  and mechanism-ranking outcomes
- Compute exploratory reliability metrics: reliability diagram (binned), Brier score,
  expected calibration error (ECE), bootstrap confidence intervals on each metric
- Analysis is performed ONLY on the held-out test set — development cases used for
  any parameter tuning are excluded from the final report
- Results are reported in `docs/calibration-analysis.md` with all caveats
- Confidence values REMAIN marked `uncalibrated` in the report output
- The `calibration_status` field stays `"uncalibrated"` — there is no code path
  that replaces heuristic confidence with "calibrated" values

**Gate criteria — when may calibrated confidence be enabled?**

All of the following must be true before the `calibration_status` may change from
`"uncalibrated"` to anything else:

1. **Sample size:** ≥30 cases in the held-out set with mechanism labels, spanning
   ≥2 protein families.
2. **Independence:** Held-out set is a mutation-level or structure-family-level split
   from the development set; no case-ID overlap; documented in versioned split metadata.
3. **Physical evidence validation:** Interaction engine has been compared to ≥2
   external reference tools and systematic disagreements have been resolved (M1).
4. **Calibration method:** Method is chosen based on calibration curve shape observed
   in exploratory analysis (not pre-committed to Platt scaling or isotonic regression).
5. **Metric:** Brier score + reliability diagram + ECE reported with bootstrap CIs.
6. **Expert review:** At least one structural biologist who is not the primary developer
   has reviewed the calibration methodology and output.

Until ALL six gates are met, confidence values stay `uncalibrated` and the report
carries the uncalibrated warning. Individual exploratory analyses may be published
as supplementary material with appropriate caveats.

Files to create/modify:
- `src/psf_reasoner/evaluation/calibration.py` — exploratory analysis only, does NOT
  modify report confidence
- `docs/calibration-analysis.md` — methodology, results, caveats
- `tests/test_calibration_evaluation.py`

---

**Sprint M3. Baseline vs LLM 对比 (Reasoning Comparison)** ← addresses G9

Prerequisite: M1b (frozen benchmark) + M1 (external physical validation).
NOT only N1 — the benchmark must be frozen and physical evidence validated before
mechanism-level comparison is meaningful.

Acceptance criteria:
- Run both Baseline and LLM reasoners on the frozen benchmark (held-out set only
  for final metrics; development set may be used for prompt engineering)
- Per-case: mechanism-type agreement (Jaccard), top-mechanism agreement with label
- Aggregate: mean reciprocal rank, top-N accuracy against mechanism labels
- Report cases where LLM disagrees with Baseline, and which (if either) matches the label
- Qualitative error analysis: what kinds of mechanisms does each engine miss?
- Separate report for development set (prompt tuning) vs held-out set (final metrics)

Files to create:
- `src/psf_reasoner/evaluation/comparison.py` — moved from `reasoning/comparison.py`
- `tests/test_comparison_evaluation.py`

---

**Sprint M4. 外部突变建模集成 (External Mutation Modeler Integration)** ← addresses G4

(unchanged from previous version)

---

**Sprint M5. 批量执行 (Batch Execution)** ← Phase 24, addresses G12

(unchanged from previous version)

---

### Later-Stage (3+ months): Scale + Generalization

- **L1. 多蛋白家族验证** ← requires M1b (frozen benchmark protocol proven on one family)
- **L2. 生产部署硬化** — rate limiting, authentication, PostgreSQL migration, monitoring
- **L3. 云端管线扩展** — MD/MM-PBSA/docking adapters
- **L4. 多评估者机制标签审查** — formal inter-rater reliability study for mechanism labels

### Corrected Dependency Graph

```
Near-Term:
  N0 (security + CI) ──────────────────────── 最高优先级, 无前置依赖
    │
    ├── N1A (benchmark protocol) ◄── N0
    │     │
    │     └── N1B (pilot data) ◄── N1A
    │
    ├── N2 (UI audit trail) ◄── (独立, 可与 N1A 并行)
    ├── N3 (docs refresh) ◄── (独立)
    ├── N4 (test gaps) ◄── (独立)
    └── N5 (upload cleanup) ◄── (独立)

Mid-Term (respects dependencies):
  N1B ──→ M1 (external interaction validation)
              │
              └──→ 修正物理规则 ──→ M1b (freeze benchmark + held-out split)
                                        │
                        ┌───────────────┤
                        │               │
                        ▼               ▼
                M2 (calibration     M3 (reasoning
                    evaluation,         comparison)
                    exploratory
                    only)
                        │               │
                        └───────┬───────┘
                                │
                                ▼
                        M4 (external modeler)
                        M5 (batch execution)

Later-Stage (deferred):
  L1 ← M1b
  L2 ← M5
  L3 ← M4
  L4 ← M1b
```

### Corrected Recommended Execution Order

1. **Week 1 (立即开始):** N0 (security + CI) — Cloud Run 已部署, 安全风险不能等
2. **Week 1-2:** N1A (benchmark protocol) + N3 (docs) + N5 (uploads) 并行
3. **Week 2-3:** N1B (pilot data curation) ← 等 N1A schema 稳定
4. **Week 2-4:** N2 (UI audit trail) + N4 (test gaps) 并行
5. **Month 2:** M1 (PLIP/Arpeggio validation) ← 依赖 N1B pilot 数据
6. **Month 2:** 根据 M1 结果修正物理规则 → M1b (freeze benchmark)
7. **Month 2-3:** M2 (exploratory calibration) + M3 (reasoning comparison) 并行 ← 都依赖 M1b
8. **Month 3:** M4 (external modeler) + M5 (batch execution)
9. **Month 4+:** 基于 M2 样本量评估是否满足 calibration gate criteria; 若满足则重新评估 L1-L4 优先级
