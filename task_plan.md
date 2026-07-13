# PSF-Reasoner MVP Foundation Plan

## Goal

Deliver a clean, runnable first version of PSF-Reasoner whose scientific models,
reasoning services, CLI/API adapters, execution, and persistence boundaries can be
extended without coupling future computation modules to delivery frameworks.

## Scope

- Python 3.12 package using a `src` layout.
- Pydantic contracts for inputs, evidence, mechanisms, hypotheses, checks, and reports.
- Framework-neutral forward, reverse, and consistency reasoning interfaces.
- A deterministic rule-based baseline that demonstrates the HIV-1 protease V82A chain.
- One application service shared by CLI and FastAPI.
- Local synchronous execution and in-memory report storage behind protocols.
- Focused tests and concise architecture/use documentation.

## Non-goals

- Production PDB/mmCIF parsing or structure normalization.
- Mutation modelling, molecular dynamics, docking, or free-energy calculations.
- Literature-backed quantitative claims.
- Cloud queues, workers, databases, or object storage implementations.

## Phases

| Phase | Status | Acceptance criteria |
|---|---|---|
| 1. Project conventions and package skeleton | complete | Packaging, lint/test config, module ownership, and public package metadata are defined. |
| 2. Unified scientific data contracts | complete | Models validate identifiers, provenance, confidence, causal links, and complete report shape. |
| 3. Reasoning and infrastructure boundaries | complete | Protocols separate evidence providers, reasoners, consistency checks, execution, and storage. |
| 4. Baseline bidirectional reasoning | complete | Forward/reverse chains are deterministic, traceable, and include uncertainty and missing evidence. |
| 5. Shared application service, CLI, and API | complete | All entry points call the same use case and expose equivalent report data. |
| 6. Tests, documentation, and verification | complete | Automated tests pass; imports, CLI, and API smoke paths are checked; extension points are documented. |
| 7. Structure-ingestion contracts and parser | complete | PDB/mmCIF files are parsed into project-owned structure records with explicit model, chain, residue, and atom identity. |
| 8. Ligand and mutation-residue localization | complete | Ambiguous or missing ligand/residue selections fail clearly; successful selections retain source provenance. |
| 9. Coordinate-derived distance and contact evidence | complete | Protein-ligand distances and residue contacts are reported as computed evidence with declared cutoffs. |
| 10. Application wiring and delivery outputs | complete | The default service combines computed and prior evidence; CLI/API accept structure-backed requests unchanged. |
| 11. HIV-1 protease regression fixture | complete | A small public-format fixture demonstrates V82 localization and ligand contacts without making mutation-model claims. |
| 12. Verification and documentation | complete | Parser, localization, calculations, CLI/API, lint, and regression tests pass. |
| 13. Paired WT/mutant input and alignment-free comparison | complete | A supplied mutant structure can be paired with the reference structure by mutation site and ligand identity. |
| 14. Comparative physical evidence | complete | Distance, contact, SASA, ligand-shell geometry, and interaction-category deltas are emitted with method limits. |
| 15. Mutation-modelling adapter boundary | complete | A typed modeler protocol is available without claiming a model where no external engine is configured. |
| 16. Delivery, fixtures, and verification | complete | CLI/API accept paired inputs; synthetic geometric regression fixtures validate deltas; documentation describes evidence limits. |
| 17. Structure preparation and chemical typing | complete | Inputs expose missing atoms, altlocs, waters, protonation assumptions, residue/ligand atom chemistry, and preparation provenance. |
| 18. Validated interaction engine | complete | Hydrogen bonds use donor/acceptor and geometry rules; salt bridges, pi interactions, hydrophobic contacts, and water bridges have typed outputs and fixtures. |
| 19. Pocket and residue-network mechanisms | complete | A validated pocket definition, local geometry descriptors, contact-network deltas, and mechanism rules replace current coarse proxies. |
| 20. Automatic mutation modelling and local relaxation | complete | A configured adapter builds the requested mutant, records engine/settings, validates residue identity, and marks modelled evidence separately from experimental structures. |
| 21. Lightweight energetics | complete | Reproducible local interaction/strain scores are available with explicit units and limits; no score is labelled binding free energy. |
| 22. Evidence-aware PSF reasoning | complete | Mechanism and function confidence responds to measured deltas, contradictory evidence, alternatives, and evidence quality rather than fixed baseline weights. |
| 23. Experimental validation benchmark | complete | Curated HIV-1 protease structure/affinity/resistance cases measure evidence accuracy, mechanism ranking, calibration, and failure modes. |
| 24. Batch execution and scale boundary | pending | Multi-mutation jobs have deterministic manifests, resumable local execution, persisted reports, and measured thresholds for moving heavy work to workers/cloud. |
| 25. Current implementation audit | in_progress | Code, tests, documentation, entry points, and scientific claims are reconciled into an evidence-backed implementation inventory. |
| 26. Gap and risk assessment | pending | Scientific, product, engineering, and operability gaps are ranked by impact, dependency, and uncertainty. |
| 27. Executable next-stage roadmap | pending | Near-, mid-, and later-stage work is split into concrete deliverables with acceptance criteria and recommended order. |
| 28. Planning handoff | pending | Findings and the recommended roadmap are recorded in repository planning files and summarized for the user. |

## Key Decisions

- IDs and explicit `supports`/`contradicts` references make causal chains inspectable.
- Scientific observations are immutable value objects; orchestration remains stateful only at infrastructure edges.
- Baseline rules emit hypotheses, not asserted experimental facts.
- Missing structure-derived measurements reduce confidence and become validation steps instead of fabricated evidence.
- Domain and application modules do not import FastAPI or Typer.
- `gemmi` will provide PDB/mmCIF decoding; project-owned records and evidence contracts remain the public scientific boundary.
- Paired comparisons are coordinate-frame independent: each structure is measured in its own ligand-centred local environment before deltas are calculated.
- SASA uses a declared Shrake-Rupley approximation; pocket evidence is initially a ligand-shell geometry proxy, not an absolute cavity-volume claim.
- Scientific fidelity precedes scale: interaction chemistry and validation must improve before MD, free-energy, or cloud execution is introduced.
- Experimental and modelled mutant structures must remain distinct evidence sources throughout the report.
- Cloud execution is triggered by measured workload and reproducibility needs, not added as an early architectural dependency.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Default Python is 3.14 and project dependencies are absent | 1 | Keep the declared runtime compatible with 3.12-3.14 and create an isolated environment for verification. |
| Dependency install could not reach PyPI inside the network sandbox | 1 | Re-ran with approved network access; installation completed. |
| Static check reported import order and lines over 100 columns | 1 | Adopted a 110-column project limit and applied the formatter/import fixer. |
| FastAPI TestClient emits an upstream httpx deprecation warning | 1 | Confirmed it originates in the installed dependency; runtime and tests remain correct. |
| No installed structural-biology parser is available | 1 | Add `gemmi` as a narrow parsing dependency for PDB/mmCIF support. |
| Initial Gemmi inspection assumed a model name attribute | 1 | Use the stable model number API; parser records remain independent of Gemmi's model object. |
| Initial paired-comparison plan patch did not match the current findings text | 1 | Reapplied the plan update against the current file contents. |
| Restarting the local API was rejected by the execution approval service | 1 | Server restart is deferred; implementation and automated API tests completed successfully. |
| Numeric HIV protease affinity/resistance values were not available from the bundled fixture metadata | 1 | Added a provenance-backed qualitative calibration label from RCSB 1SDT/1SDV and primary literature; no fabricated Ki/Kd/IC50 values are emitted. |
| Git status is unavailable because the workspace is not a Git repository | 1 | Treat repository initialization, ignore rules, and a first clean baseline commit as release-engineering work in the roadmap. |
