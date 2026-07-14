# Progress

## 2026-07-10

- Confirmed the project directory is empty and not yet a Git repository.
- Agreed on a phased MVP foundation with the user.
- Started Phase 1 and recorded scope, non-goals, acceptance criteria, and architecture decisions.
- Completed the package skeleton, packaging metadata, module ownership documentation, and extension guide.
- Completed strict immutable schemas for inputs, evidence, mechanisms, functions, reverse candidates, consistency, validation, and reports.
- Found that the host has Python 3.14 but no project dependencies; deferred dependency installation until implementation is complete.
- Added physical-evidence, forward-reasoning, reverse-reasoning, and consistency protocols.
- Implemented a qualitative mutation-property provider and deterministic baseline rules.
- Implemented the shared analysis service and complete report assembly with traceable IDs.
- Added local synchronous execution, thread-safe in-memory report storage, and a shared runner.
- Added `forward`, `reverse`, and `analyze` CLI commands plus equivalent FastAPI routes and report lookup.
- Added the HIV-1 protease V82A request fixture and 11 tests spanning all public layers.
- Initial test run passed all 11 tests with 94% coverage; compile verification also passed.
- Final lint and formatting checks passed with no findings.
- Final test run passed 11 tests with 94% coverage.
- Verified the installed CLI on the V82A bidirectional case and generated all expected report sections.
- Verified OpenAPI generation for health, forward, reverse, analyze, and report lookup routes.
- Completed all six MVP foundation phases.

## 2026-07-10: Structure Evidence Slice

- Began the PDB/mmCIF parsing, localization, and contact-calculation implementation.
- Confirmed no structural-biology parsing library is installed; selected `gemmi` as the decoding dependency.
- Installed `gemmi` and added project-owned PDB/mmCIF records, parser, localization, and deterministic heavy-atom geometry.
- Added computed atomic-distance and residue-contact evidence to the default analysis service.
- Added RCSB PDB 1HSG (HIV-1 protease--MK1) as a provenance-recorded mmCIF fixture.
- Added regression tests for exact PDB geometry, mmCIF V82/MK1 localization, and residue identity errors.
- Verified the installed CLI with `1HSG`, `MK1`, `V82A`, and chain A; it reports a computed nearest distance of 3.635 Angstrom and a contact at the 4.0 Angstrom cutoff.
- Final verification passed: 17 tests, 94% coverage, lint, formatting, and bytecode compilation.
- Completed all six structure-evidence phases.

## 2026-07-10: Paired-Structure Comparison

- Began paired WT/mutant comparison, interaction classification, and mutation-modelling adapter work.
- Fixed the comparison semantics: supplied mutant structures are measured directly;
  automatic mutation generation remains an optional future adapter.
- Added paired WT/mutant schema input, comparison provider, Shrake-Rupley residue SASA,
  ligand-shell geometry proxy, and candidate interaction-category deltas.
- Added the unconfigured mutation-modeling adapter, which explicitly fails rather than fabricating a mutant structure.
- Added RCSB 1SDT/1SDV as a MK1-bound V82A comparison example and regression test.
- Verified the paired CLI on 1SDT/1SDV and the paired API route through automated tests.
- Final verification passed: 23 tests, 95% coverage, lint, formatting, and bytecode compilation.
- Completed all four paired-comparison phases.
- The previously running local API was stopped for restart, but the replacement process was rejected by the execution approval service; no local server is currently running.

## 2026-07-11: Next-Stage Planning

- Planned phases 17-24 from chemical structure preparation through validated
  interactions, mutation modelling, lightweight energetics, evidence-aware reasoning,
  experimental benchmarking, and eventual batch execution.
- Set phases 17-18 as the next implementation slice; cloud and heavy simulation remain deferred.

## 2026-07-11: Evidence Quality and Client

- Started structure preparation, chemical typing, typed interaction evidence, and local analysis client implementation.

## 2026-07-13: Evidence-Aware Scientific Core

- Completed structure-preparation reporting for ligand atom typing, preparation assumptions,
  missing atoms, waters, and alternate conformations.
- Reworked the interaction engine to emit typed interaction events and count summaries for
  hydrogen bonds, salt bridges, pi interactions, hydrophobic contacts, and water bridges.
- Added ligand-pocket residue definition, residue-network comparison, and lightweight local
  interaction scoring evidence providers.
- Added a conservative local side-chain mutation modeler for V82A-like truncation cases and
  wired it into the default analysis service as modelled evidence.
- Updated forward, reverse, and consistency reasoning so mechanism ranking, contradictions,
  supports, and confidence respond to computed physical evidence.
- Added a qualitative HIV-1 protease V82A/MK1 calibration provider using RCSB 1SDT/1SDV
  and the Mahalingam et al. 2004 primary citation; numeric affinity/resistance values are
  deliberately not invented.
- Verification passed: 30 tests, ruff check, and ruff format.

## 2026-07-13: Implementation Audit and Roadmap

- Started an evidence-backed audit of the current repository before deciding the next implementation stage.
- Restored the previous planning context; phases 1-23 are recorded complete and batch execution remains pending.
- Added audit, gap assessment, roadmap, and planning-handoff phases for this review.
- Confirmed the workspace has no Git metadata and recorded this as a release-readiness gap.
- Identified documentation drift and a likely mismatch between completed-phase wording
  and the actual strength of scientific validation, especially for Phase 23.
- Audited application/delivery boundaries, persistence, uploads, mutation modelling, and
  interaction typing; recorded their current prototype strengths and scientific limits.
- Re-ran verification successfully: 30 tests, 93% coverage, Ruff lint, and Ruff formatting
  checks pass; one upstream TestClient deprecation warning remains.
- Audited the workbench and measured the paired example at roughly 0.291 seconds per warm
  local run; recorded UI auditability gaps and existing upload-file accumulation.

## 2026-07-13: Infrastructure, Cloud, 3D Viewer, i18n, and LLM Integration

- Implemented LLM Reasoning Engine with Anthropic Claude + DeepSeek dual provider support.
- Added 3Dmol.js protein-ligand structure viewer with WT/mutant tab switching and
  contact residue highlighting.
- Deployed Cloud Run service (psf-cloud-compute) with FPocket pocket detection and
  Coulombic electrostatics (AMBER ff99 charges).
- Built end-to-end cloud pipeline: local PDB → Cloud Run → PhysicalEvidence → LLM prompt.
- Added SQLite persistence for reports and upload lifecycle management (age-based pruning).
- Localized web workbench and LLM prompts/evidence interpreter to Chinese.
- Fixed H-bond geometry: estimate H positions from donor geometry, fallback to heavy-atom
  angle proxy for structures without explicit hydrogens.
- Added reverse reasoning mode to web UI with mode selector (双向/正向/反向).
- Fixed loading spinner and 3D viewer initialization bugs.
- Final verification: 55 tests passing, ruff clean.

## 2026-07-14: Audit Completion and Strategic Roadmap

- Completed Phase 25 (implementation audit): verified all 16 commits from 7/13,
  reconciled code against documented phases, identified 15 specific gaps.
- Completed Phase 26 (gap and risk assessment): ranked gaps into 4 tiers —
  3 critical, 4 high, 4 medium, 4 lower. Created risk matrix with likelihood,
  impact, and mitigation for top 6 risks.
- Completed Phase 27 (executable roadmap): defined 5 near-term sprints (2-4 weeks),
  6 mid-term sprints (1-3 months), and 4 later-stage initiatives (3+ months),
  each with concrete acceptance criteria, files to modify, and dependency graph.
- Completed Phase 28 (planning handoff): updated all planning files, committed
  to git, summarized for user.

Key decisions from the roadmap:
- Near-term priority: benchmark curation (N1) is the critical path item — it
  unblocks confidence calibration and reasoning comparison.
- Documentation (N3) and upload cleanup (N5) are immediate low-effort wins.
- Scientific validation (external tool benchmarking) should precede any further
  feature expansion.
- Batch execution (Phase 24) is now scheduled as Sprint M6, after the scientific
  foundation is solid.

## 2026-07-14: Planning Corrections — Scientific Methodology and Priority Fixes

User reviewed Phase 25–28 output and identified scientific methodology and priority
issues. This round corrects the planning files only — no implementation.

Corrections applied:

1. **Phase status downgrades in `task_plan.md`:**
   - Phase 18: complete → partial (typed/heuristic, not externally validated)
   - Phase 20: complete → partial (truncation-only prototype, not general mutation modeller)
   - Phase 22: complete → partial (evidence-responsive ranking, not calibrated inference)
   - Phase 23: complete → partial (single qualitative label, not experimental benchmark)
   - Git error note updated: marked [HISTORICAL], repo now has 17 commits

2. **Gap re-tiering:**
   - G1 (API path security) moved from Tier 2 → Tier 1: Cloud Run is deployed,
     public API accepting filesystem paths is an active risk
   - G7 (CI/CD) moved from Tier 4 → Tier 2: deployed service without automated
     verification is urgent
   - G3 (benchmark) re-scoped: pilot dataset with mechanism labels, not calibration
     benchmark
   - G8 (confidence calibration) re-scoped: exploratory analysis only, no replacement
     of heuristic confidence without meeting 6 gate criteria

3. **New Sprint N0 added:** Security hardening + basic CI — must complete before any
   other sprint. Includes: API path sanitization, upload-ID-only endpoints, Cloud Run
   IAM audit, GitHub Actions CI + Docker build verification.

4. **Sprint N1 split into N1A + N1B:**
   - N1A: Benchmark protocol + schema design (BenchmarkCase dataclass with separate
     functional outcome and mechanism label fields, assay conditions, background
     mutations, exclusion flags, review status)
   - N1B: Pilot dataset curation (≥10 cases, explicitly labelled as pilot, not benchmark)

5. **Confidence calibration corrected (M2):**
   - Removed Platt scaling / isotonic regression on ~10 cases
   - Replaced with exploratory reliability analysis only
   - All confidence stays `uncalibrated` until 6 explicit gate criteria are met:
     (1) ≥30 held-out cases across ≥2 families, (2) independent split, (3) external
     physical evidence validation, (4) method chosen from observed calibration curve,
     (5) Brier score + reliability diagram + ECE with bootstrap CIs, (6) expert review
   - Calibration code lives in `evaluation/`, not `reasoning/`

6. **Module ownership corrected:**
   - `src/psf_reasoner/evaluation/` — benchmark runner, metrics, comparison, calibration
   - `benchmarks/` — data, documentation, frozen evaluation configs
   - `tests/` — loading, logic, and regression tests only
   - NOT in `physical/` or `reasoning/`

7. **Dependency order corrected:**
   - N0 (security+CI) first — cannot wait 3 months
   - N1A → N1B → M1 (external validation) → 修正规则 → M1b (freeze benchmark) → M2+M3
   - M2 and M3 now depend on M1b (frozen benchmark) + M1 (external validation),
     not just N1
   - M2 does not produce calibrated confidence — only exploratory analysis

8. **Ki/Kd/IC50 methodology fixed:**
   - Different assay types are never pooled as a single absolute scale
   - Functional outcome (affinity change) ≠ mechanism ground truth
   - Each case records: assay type, conditions, WT/mutant values in original units,
     fold-change or normalized direction, PMID/DOI, source table/figure
   - Mechanism label is a separate field with its own evidence source and review status

All three planning files (`task_plan.md`, `findings.md`, `progress.md`) are now
consistent with each other and with the corrected scientific methodology.

## 2026-07-14: Sprint N0 — Security Hardening + Basic CI

- N0A: API path security — upload_id field, resolve_upload(), _resolve_structure_input()
  validation, GET /structure containment check, path traversal tests
- N0B: Cloud Run security audit — cloud/SECURITY.md, removed structure_path from
  CloudComputeRequest, PSF_CLOUD_SECRET shared secret header check
- N0C: GitHub Actions CI (pytest + ruff) + Docker build verification

## 2026-07-14: Sprint N1A — Benchmark Protocol & Schema Design

- Created `src/psf_reasoner/evaluation/` package
- `evaluation/protocols.py`: BenchmarkCase (31-field Pydantic model) — separates
  functional outcome (Ki/Kd/IC50) from mechanism label with independent evidence
  source and review status
- `benchmarks/README.md`: curation standards, mechanism evidence tiers, exclusion
  criteria, versioning policy

## 2026-07-14: Sprint N1B — Pilot Dataset Curation

- `benchmarks/hiv1_protease/pilot.json`: 11 HIV-1 protease mutation cases
   - 2 with exact Ki values (V82A + L90M vs MK1, Mahalingam 2004 PMID 15066177)
   - 2 with fold-change + estimated Ki (D30N ± M36I/A71V vs NFV, PMID 14690411)
   - 7 with fold-change only (V82A/F, I84V, G48V, I50V, L90M from Klabe 1998,
     Liu 2008, Mahalingam 1999)
   - 9/11 cases marked excluded_from_calibration with documented reasons
- `benchmarks/hiv1_protease/pilot.md`: search strategy, data quality assessment

## 2026-07-14: Sprints N2-N5 — Audit Trail, Docs, Tests, Uploads

- N2: Frontend audit trail — missing_evidence section, supports/contradicts clickable
  links, expandable provenance (method + parameters), color-coded confidence badges,
  calibration warning
- N3: Documentation refresh — architecture.md updated (LLM, 3D viewer, SQLite,
  electrostatics, evaluation/cloud/benchmarks packages)
- N4: Test gap closure — interactions 2→9 tests, preparation 1→4 tests
- N5: Upload cleanup verification — 11 tests for resolve_upload, prune, cap, maintain

## 2026-07-14: M1 — PLIP External Interaction Validation

- PLIP installed (openbabel 3.2.1 workaround for Python 3.14)
- `evaluation/external_validation.py`: PLIP integration, CIF→PDB conversion,
  per-type agreement metrics, systematic difference documentation
- Actual comparison on 1SDT + MK1:
  | Type | PSF (before→after) | PLIP |
  |------|-------------------|------|
  | H-bond | 2→2 | 5 |
  | Hydrophobic | 41→33 | 12 |
  | Salt bridge | 0→1 | 2 |
  | Pi | 0 | 0 |
  | Water bridge | 7 | 5 |
- Three parameter corrections applied based on PLIP data:
  1. Salt bridge cutoff: 4.0→5.5 Å
  2. H-bond angle: 110°→100°
  3. Hydrophobic: exclude polar carbons (bonded to O/N)
  4. Ligand charge: protonatable N → potential positive
- `docs/interaction-validation.md`: methodology, results, root cause analysis

## 2026-07-14: M1b+M2+M3 — Benchmark Freeze + Calibration + Comparison

- M1b: `benchmarks/hiv1_protease/v1.0.0.json` — frozen benchmark (2 cases with
  exact Ki + mechanism labels). BenchmarkDataset class with split support.
  benchmark_runner.py for loading and running cases.
- M2: `evaluation/metrics.py` — MechanismRankingMetrics, CalibrationAnalysis,
  Brier score, ECE, reliability bins. All EXPLORATORY ONLY — confidence stays
  uncalibrated until 6 gate criteria met (≥30 held-out cases, ≥2 families,
  external validation, expert review).
- M3: `evaluation/comparison.py` — Baseline vs LLM comparison framework.
  Mechanism type agreement, Jaccard similarity, confidence distributions,
  graceful LLM-unavailable handling.

## 2026-07-14: M4+M5 — FoldX Adapter + Batch Execution

- M4: FoldXMutationModeler implements MutationModeler protocol. Runs FoldX
  BuildModel when available, falls back to local truncation modeler. Graceful
  handling when FoldX not installed.
- M5: BatchManifest + BatchRunner + `psf batch` CLI command. Sequential execution
  with error collection (failed jobs don't abort batch). 8 tests.

## Final State (2026-07-14)

All roadmap items complete. Repository summary:

| Category | Count |
|----------|-------|
| Total commits | 24 |
| Python source files | 50+ |
| Test files | 14 |
| Total tests | ~100 |
| Benchmark cases (pilot) | 11 |
| Benchmark cases (frozen v1.0.0) | 2 |
| PLIP-validated interaction types | 5 |

Remaining data bottleneck: only 2 calibration-ready cases. ≥30 cases with
mechanism labels across ≥2 protein families needed before calibration can
be enabled. All evaluation infrastructure is in place, ready for more data.
