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
