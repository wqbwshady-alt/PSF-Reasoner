# Findings

## Initial State

- The project directory was confirmed empty.
- It was not initialized as a Git repository.
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

## 2026-07-14 Phase 26: Gap and Risk Assessment

Gaps are ranked by **impact × uncertainty × dependency** — a gap that blocks multiple
downstream items and has high uncertainty is ranked higher than one that is isolated.

### Tier 1 — Critical (blocks scientific credibility)

**G1. 无校准基准 (No Calibration Benchmark)**

Phase 23 claims "实验验证基准" exists, but the implementation has only one qualitative
V82A/MK1 label. There is no curated numeric dataset (Ki, Kd, IC50, fold-change), no
multi-case benchmark, no held-out test set. Without this, it is impossible to:
- Know whether the inference engine ranks mechanisms correctly
- Calibrate heuristic confidence values into actual probabilities
- Compare baseline vs LLM reasoning quality
- Publish or present quantitative results

Impact: blocks publication, clinical credibility, and any claim of "validation."
Uncertainty: medium (curation is mechanical but tedious; finding the right data sources
requires domain judgment).
Dependency: blocks G3 (confidence calibration), G8 (reasoning comparison).

**G2. 相互作用引擎未经验证 (Interaction Engine Not Validated)**

Phase 18 claims a "validated interaction engine" but the implementation is a heuristic
baseline. Specific unvalidated aspects:
- H-bond geometry: H positions estimated (not observed), angle check uses heavy-atom proxy
  fallback at 90° (vs standard 110°)
- Aromaticity: name/connectivity heuristic, not quantum-chemical or database-derived
- Water bridges: distance-only partner selection, no H-bond geometry on water
- Ligand atom typing: confidence as low as 0.30 for carbon, element-only for O/S without
  neighbors
- No comparison against established tools (HBPLUS, DSSP, Arpeggio, PLIP)

Impact: every downstream mechanism and hypothesis inherits these uncertainties.
Uncertainty: low (the limitations are well understood).
Dependency: blocks G10 (interaction engine rebuild/validation).

**G3. 置信度未校准 (Confidence Values Not Calibrated)**

The report explicitly states confidence is heuristic and uncalibrated, which is honest.
But without calibration, the 93%/87%/72% numbers shown in the UI are indistinguishable
from random numbers to a reader. The calibration provider has one qualitative label;
there is no calibration curve, reliability diagram, or Brier score.

Impact: the primary output metric is scientifically unactionable.
Uncertainty: medium (requires G1 first, then calibration methodology).
Dependency: depends on G1.

### Tier 2 — High (blocks product readiness)

**G4. 突变建模仅支持截断型 (Mutation Modeling: Truncation Only)**

The LocalSideChainMutationModeler can only handle V→A, I→A, F→A — cases where the
target residue is a subset of the source. It removes incompatible atoms but never
adds them. It cannot model:
- A→V (adding CG1/CG2)
- A→F (adding aromatic ring)
- Any gain-of-size mutation
- Any mutation requiring rotamer sampling or backbone relaxation

Impact: the automatically-generated mutant path is unavailable for the majority of
clinically relevant mutations.
Uncertainty: low (the limitation is inherent in the design).
Dependency: requires integration with an external modeler (FoldX, Rosetta, SCWRL)
or a more sophisticated internal implementation.

**G5. 前端审计字段缺失 (Frontend Omits Audit Fields)**

The web UI renders evidence, mechanisms, hypotheses, candidates, consistency checks, and
validation steps. But it does NOT render:
- `missing_evidence` — the "what we need to measure to confirm" section
- `supports`/`contradicts` references — the causal graph edges
- `provenance` details beyond source name — method + parameters not shown
- `limitations` on individual claims (shown on some items but not systematically)
- The non-calibration warning that exists in the Python report

Impact: the web UI presents results as a flat list of claims without the audit trail
that makes PSF-Reasoner distinct from a black-box predictor.
Uncertainty: low (pure UI work).
Dependency: none.

**G6. 文档不一致 (Documentation Drift)**

`docs/architecture.md` describes LLM reasoners as "future," mutation modeling as
"future interface," and electrostatics as "future." All three are now implemented.
The README is more current but still incomplete — it doesn't mention the cloud
pipeline, DeepSeek provider, or reverse-mode UI.

Impact: new contributors or collaborators reading the docs would underestimate
capabilities.
Uncertainty: low (known exactly what to update).
Dependency: none.

**G7. API 路径访问风险 (API Path-Access Security)**

The JSON API accepts server-side filesystem paths in `AnalysisRequest.structure.path`.
This works for a trusted local workbench but would be a path-traversal vulnerability
in any multi-user deployment. The file-upload endpoints bypass this, but the JSON
endpoints remain.

Impact: blocks any shared or deployed API usage.
Uncertainty: low (well-known pattern).
Dependency: requires an artifact abstraction (upload first, then reference by ID).

### Tier 3 — Medium (blocks robustness and scale)

**G8. LLM vs Baseline 推理无对比基准 (No Reasoning Comparison Framework)**

Both the Baseline and LLM reasoning engines run on the same inputs, but there is no
systematic way to compare their outputs — no shared test cases with known answers,
no inter-rater agreement metrics, no mechanism-level precision/recall. The current
test suite only checks that LLM output is structurally valid JSON, not that it is
scientifically correct.

Impact: cannot know whether adding LLM improves or degrades reasoning quality.
Uncertainty: high (requires designing comparison methodology).
Dependency: depends on G1 (benchmark).

**G9. 测试覆盖有盲区 (Test Coverage Blind Spots)**

55 tests and 93% line coverage mask important gaps:
- Interaction engine: 2 tests (H-bond + pi), no salt bridge, hydrophobic, or water bridge tests
- Preparation: 1 test on a 6-atom synthetic fixture
- No property-based tests (e.g., "any pair of oppositely charged atoms within 4Å should
  form a salt bridge")
- No edge-case tests: empty structures, all-glycine, no ligand, multi-model NMR
- No performance regression tests
- No security tests (path traversal, file upload limits, malicious PDB)
- No persistence/restart tests for SQLite repository

Impact: regressions in the interaction engine or parser could go undetected.
Uncertainty: low (gap analysis is straightforward).
Dependency: none.

**G10. 物理证据未与外部工具对标 (No External Tool Benchmarking)**

The interaction engine, pocket analysis, and energy scoring have never been compared
against established tools:
- Interactions: PLIP, Arpeggio, HBPLUS, DSSP
- Pocket: FPocket (local), SiteMap, CASTp
- Energy: FoldX, Rosetta, Amber

Without this, the project cannot claim its physical evidence is scientifically
defensible — only that it is internally consistent.

Impact: reviewers will ask "how does this compare to PLIP/FoldX?"
Uncertainty: medium (requires running external tools on the same structures).
Dependency: none directly, but benefits from G1.

**G11. 上传文件累积 (Upload Artifact Accumulation)**

`.psf_uploads` has 90 entries. The SQLite persistence and upload lifecycle management
(age-based pruning + count cap) were implemented in commit f282d98, but the existing
accumulation suggests either the cleanup is not running or the default limits are too
high. A startup cleanup hook exists in the API.

Impact: disk space grows unbounded if cleanup is not verified.
Uncertainty: low (verify cleanup runs, adjust defaults).
Dependency: none.

### Tier 4 — Lower (nice-to-have, future stage)

**G12. 无批量执行 (No Batch Execution)** — Phase 24 explicitly deferred. Single-case
latency (~0.3s) is fine; the gap is manifest management, resumability, and progress
tracking for multi-mutation jobs.

**G13. 无 CI/CD** — No GitHub Actions, no automated test runs on push, no Docker
build verification for the cloud service.

**G14. 单点蛋白质 (Single Protein Family)** — All testing and calibration is on
HIV-1 protease. The system claims to be general but has never been run on kinases,
GPCRs, or other therapeutically relevant families.

**G15. web 工作台示例依赖服务器路径** — The built-in example uses
`examples/data/1sdt.cif` which is relative to the server working directory. This
fails in packaged/deployed contexts.

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Reviewer rejects quantitative claims due to uncalibrated confidence | High | High | G1+G3: add benchmark + calibration before any publication |
| Interaction engine produces false negatives (missed H-bonds) | Medium | Medium | G2+G10: validate against PLIP/Arpeggio |
| LLM generates plausible but scientifically wrong mechanisms | Medium | High | G8: comparison framework with expert review |
| Path traversal in shared deployment | Low (single-user now) | High | G7: artifact abstraction before any shared deployment |
| Disk exhaustion from upload accumulation | Low | Low | G11: verify cleanup, add monitoring |
| Documentation misleads new contributors | Medium | Low | G6: docs refresh pass |

## 2026-07-14 Phase 27: Executable Next-Stage Roadmap

### Near-Term (2-4 weeks): Audit Closure + Credibility Foundation

These items close the Phase 25 audit findings and lay the groundwork for all later
scientific work. Each is independent enough to be worked on in parallel.

---

**Sprint N1. 构建最小校准基准 (Minimal Calibration Benchmark)** ← addresses G1

Acceptance criteria:
- A CSV/JSON file checked into `examples/benchmarks/` with ≥10 HIV-1 protease
  mutation cases
- Each row: PDB ID(s), mutation, ligand, experimental Ki/Kd/IC50 or fold-change,
  literature PMID
- A `benchmark.py` module that loads cases and runs the full pipeline on each,
  comparing mechanism ranking to experimental outcome
- A summary metric: "mechanism ranking accuracy" (does the top-ranked mechanism
  match the known resistance mechanism?)

Files to create/modify:
- `examples/benchmarks/hiv1_protease_benchmark.json` — curated data
- `tests/test_benchmark.py` — ≥3 test cases that verify benchmark loads and runs
- `src/psf_reasoner/physical/benchmark.py` — benchmark runner

---

**Sprint N2. 前端审计追踪补全 (Web UI Audit Trail)** ← addresses G5

Acceptance criteria:
- Report renders `missing_evidence` section with each item's description and
  required measurement
- Report renders `supports`/`contradicts` as links between claim cards (clicking
  a support reference scrolls to that evidence item)
- Claim cards expand to show full `provenance` (method + parameters), not just
  source name
- A visible calibration warning: "置信度为启发式排序值，非校准概率。参考基准测试
  评估推理质量。"
- Confidence badge uses a color scale (red→yellow→green) instead of raw percentage

Files to modify:
- `src/psf_reasoner/api/static/app.js` — `renderReport()`, `claimCard()`
- `src/psf_reasoner/api/static/styles.css` — new styles for graph edges, expanded
  provenance, calibration warning

---

**Sprint N3. 文档刷新 (Documentation Refresh)** ← addresses G6

Acceptance criteria:
- `docs/architecture.md` updated: LLM reasoners marked as implemented, mutation
  modeling described as prototype/local-truncation, electrostatics/cloud pipeline
  documented, Cloud Run architecture added to panorama
- `README.md` updated: cloud pipeline, DeepSeek provider, reverse-mode UI,
  H-bond geometry estimation, Chinese i18n all mentioned
- `findings.md` audit gap summary added to a new `docs/known-gaps.md` (or linked
  from README)

Files to modify:
- `docs/architecture.md`
- `README.md`
- New: `docs/known-gaps.md` (optional, could also be a link to findings.md)

---

**Sprint N4. 关键测试缺口补全 (Critical Test Gap Closure)** ← addresses G9 (partial)

Acceptance criteria:
- Interaction engine: ≥8 tests covering every interaction type (H-bond, salt bridge,
  hydrophobic, pi, water bridge) + edge cases (no donor/acceptor, out of cutoff,
  empty waters, no aromatic rings)
- Preparation inspector: ≥3 tests (synthetic fixture with explicit waters, fixture
  with altlocs, fixture with missing atoms)
- Property-based test: "for any random pair of oppositely charged atoms within 4Å,
  a salt bridge is formed" (using a small hand-written property check, not a full
  Hypothesis framework)
- Upload cleanup: 1 test verifying that `cleanup_uploads()` removes files older
  than the configured age

Files to modify:
- `tests/test_interactions.py`
- `tests/test_preparation.py`
- New: `tests/test_uploads.py`

---

**Sprint N5. 上传清理验证 (Upload Cleanup Verification)** ← addresses G11

Acceptance criteria:
- `.psf_uploads` directory has ≤20 files after running the startup cleanup
- Age-based pruning verified: files older than 7 days are removed
- Count cap verified: when >50 files, oldest are removed first
- Cleanup runs on API startup and via `/admin/maintain-uploads`

Files to modify:
- `src/psf_reasoner/infrastructure/uploads.py` — verify/update defaults
- `src/psf_reasoner/api/app.py` — ensure startup event triggers cleanup

---

### Mid-Term (1-3 months): Scientific Validation + Robustness

These items require the near-term work as foundation and involve deeper scientific
validation.

---

**Sprint M1. 相互作用引擎外部验证 (External Interaction Validation)** ← addresses G2+G10

Acceptance criteria:
- Run PLIP (or Arpeggio) on the same 1SDT/1SDV structure pair
- Compare H-bond, salt bridge, hydrophobic, and pi interaction counts between
  PSF-Reasoner and the reference tool
- Document agreement rate and systematic differences
- Adjust interaction parameters (cutoffs, angle thresholds) where PSF-Reasoner
  systematically disagrees with reference tools
- Publish comparison table in `docs/interaction-validation.md`

New dependency: PLIP (Python package) or Arpeggio (web service)

---

**Sprint M2. 置信度校准 (Confidence Calibration)** ← addresses G3

Prerequisite: Sprint N1 (benchmark)

Acceptance criteria:
- Using the benchmark from N1, produce a calibration curve: heuristic confidence
  vs actual mechanism-ranking accuracy
- Implement a simple Platt scaling or isotonic regression calibrator
- Calibrated confidence values replace heuristic ones when benchmark data is available
- Report gains a `calibration_status` field: "uncalibrated" | "calibrated_against_hiv1"

Files to create/modify:
- `src/psf_reasoner/reasoning/calibration.py` — calibrator
- `src/psf_reasoner/schemas/report.py` — add `calibration_status`

---

**Sprint M3. LLM vs Baseline 对比框架 (Reasoning Comparison Framework)** ← addresses G8

Prerequisite: Sprint N1 (benchmark)

Acceptance criteria:
- A `compare_reasoners.py` script runs both Baseline and LLM on the full benchmark
- Outputs per-case: mechanism agreement (Jaccard), top-mechanism agreement,
  confidence correlation
- Summary report: cases where LLM disagrees with Baseline and which is correct
  (per experimental outcome)
- ≥3 test cases in `tests/test_reasoning_comparison.py`

Files to create:
- `src/psf_reasoner/reasoning/comparison.py`
- `tests/test_reasoning_comparison.py`

---

**Sprint M4. 外部突变建模集成 (External Mutation Modeler Integration)** ← addresses G4

Acceptance criteria:
- A `FoldXMutationModeler` adapter (or SCWRL/Rosetta equivalent) that implements
  the existing `MutationModeler` protocol
- Handles gain-of-size mutations (A→V, A→F, etc.)
- Records engine version, settings, and explicit "modelled" status
- Falls back to LocalSideChainMutationModeler for truncation cases (faster, no
  external dependency)
- ≥2 test cases: one truncation (uses local), one gain-of-size (uses external)

New dependency: FoldX (binary, free for academic use) or PyRosetta

---

**Sprint M5. API 安全加固 (API Security Hardening)** ← addresses G7

Acceptance criteria:
- JSON API endpoints (`/analyze`, `/forward`, `/reverse`) no longer accept
  filesystem paths in `structure.path` — they require an upload ID or inline
  file upload
- File upload endpoints (`/analyze-upload`, `/reverse-upload`) become the
  primary API surface
- Uploaded files stored with content-hash-based names, not original names
- Path traversal tests added (attempt `../../etc/passwd` style paths)

Files to modify:
- `src/psf_reasoner/api/app.py`
- `src/psf_reasoner/schemas/inputs.py` — `StructureInput` gains upload_id field
- `tests/test_api.py`

---

**Sprint M6. 批量执行 (Batch Execution)** ← Phase 24, addresses G12

Acceptance criteria:
- A `BatchManifest` schema: list of `AnalysisRequest`s with shared config
- `BatchRunner`: runs jobs sequentially with progress tracking, writes per-job
  reports to SQLite
- Failed jobs don't abort the batch; errors collected in manifest
- `psf batch run manifest.json` CLI command
- ≥2 tests: successful batch, batch with one failure

Files to create/modify:
- `src/psf_reasoner/schemas/batch.py` — BatchManifest, BatchResult
- `src/psf_reasoner/application/batch_runner.py`
- `src/psf_reasoner/cli.py` — add `batch` command
- `tests/test_batch.py`

---

### Later-Stage (3+ months): Scale + Generalization

These items are explicitly deferred and should be re-evaluated after the mid-term
milestones are complete.

---

**L1. 多蛋白家族验证 (Multi-Protein-Family Validation)** ← addresses G14

- Curate benchmarks for ≥2 additional protein families (kinases, GPCRs, or
  serine proteases)
- Run full pipeline on each, compare mechanism ranking accuracy across families
- Identify family-specific parameter adjustments or limitations

---

**L2. CI/CD 管线 (CI/CD Pipeline)** ← addresses G13

- GitHub Actions: test suite on push/PR, ruff lint, type checking
- Docker build verification for cloud service
- Benchmark regression test: fails if mechanism ranking accuracy drops below threshold

---

**L3. 云端管线扩展 (Cloud Pipeline Expansion)**

- MD simulation adapter (OpenMM/GROMACS) for local relaxation of modelled mutants
- MM/PBSA or MM/GBSA binding free energy estimation
- Docking adapter (AutoDock Vina/Smina) for binding pose prediction

---

**L4. 生产部署硬化 (Production Hardening)**

- Rate limiting, authentication, HTTPS enforcement
- Database migration framework for SQLite → PostgreSQL
- Monitoring, logging, alerting

---

### Dependency Graph

```
Near-Term (parallelizable):
  N1 (benchmark) ─────────────────────────┐
  N2 (UI audit trail)                      │
  N3 (docs refresh)                        │
  N4 (test gaps)                           │
  N5 (upload cleanup)                      │
                                           │
Mid-Term (respects dependencies):          │
  M1 (external validation) ◄───────────────┤
  M2 (confidence calibration) ◄── N1       │
  M3 (reasoning comparison) ◄── N1         │
  M4 (external modeler) ◄──────────────────┤
  M5 (API security) ◄──────────────────────┤
  M6 (batch execution) ◄───────────────────┘

Later-Stage (deferred):
  L1 ← M2, M3
  L2 ← CI readiness
  L3 ← M4
  L4 ← M5, M6
```

### Recommended Execution Order

1. **Week 1-2:** N3 (docs) + N5 (uploads) in parallel — both are low-effort,
   immediate wins
2. **Week 1-4:** N1 (benchmark) — start early because M2 and M3 depend on it
3. **Week 2-4:** N2 (UI audit trail) + N4 (test gaps) in parallel
4. **Month 2:** M1 (external validation) + M5 (API security) — no shared
   dependencies
5. **Month 2-3:** M2 (calibration) + M3 (comparison) — both depend on N1
6. **Month 3:** M4 (external modeler) + M6 (batch execution)
7. **Month 4+:** Re-evaluate. If M1-M3 show strong scientific signal, prioritize
   L1+L3. If engineering gaps are the bottleneck, prioritize L2+L4.
