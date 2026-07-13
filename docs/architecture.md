# PSF-Reasoner Architecture

## System Panorama

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            DELIVERY LAYER                                │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │ CLI (typer)  │  │ FastAPI      │  │ Web Workbench                │   │
│  │              │  │ REST + File  │  │ Static HTML/CSS/JS           │   │
│  │ psf forward  │  │ Upload       │  │ Interactive Report Viewer    │   │
│  │ psf reverse  │  │              │  │ (future: 3D viewer, LLM chat)│   │
│  │ psf analyze  │  │              │  │                              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┬───────────────┘   │
│         │                 │                         │                    │
│         └─────────────────┼─────────────────────────┘                    │
│                           │ AnalysisRunnerProtocol                       │
├───────────────────────────┼──────────────────────────────────────────────┤
│                           ▼                                              │
│              APPLICATION ORCHESTRATOR                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  AnalysisService.analyze(request) → PSFReport                    │   │
│  │                                                                  │   │
│  │  1. Input Validation & Mode Detection                            │   │
│  │  2. Structure Preparation Inspection                             │   │
│  │  3. Mutation Modeling (optional, explicit mutant preferred)       │   │
│  │  4. Physical Evidence Collection (CompositeEvidenceProvider)      │   │
│  │  5. Forward Reasoning  (mutation  → mechanisms → hypotheses)      │   │
│  │  6. Reverse Reasoning  (phenotype → candidates  → required ev.)   │   │
│  │  7. Consistency Verification                                      │   │
│  │  8. Report Assembly (dedup, confidence, limitations)              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│      ┌────────────────────────┼────────────────────────┐                 │
│      │                        │                        │                 │
│      ▼                        ▼                        ▼                 │
│  ┌──────────────┐  ┌──────────────────────┐  ┌──────────────────┐       │
│  │ Physical     │  │ Reasoning Engine     │  │ Consistency &    │       │
│  │ Evidence     │  │ (Framework-Neutral   │  │ Verification     │       │
│  │ Pipeline     │  │  Protocols)          │  │                  │       │
│  │              │  │                      │  │                  │       │
│  │ • Structure  │  │ ForwardReasoner      │  │ ConsistencyChecker│      │
│  │   Parser +   │  │ ReverseReasoner      │  │ (cross-validate  │       │
│  │   Preparation│  │                      │  │  forward/reverse) │       │
│  │ • Interaction│  │ Implementations:     │  │                  │       │
│  │   Classifier │  │  • Baseline (rules)  │  │                  │       │
│  │ • Pocket /   │  │  • LLM (future)      │  │                  │       │
│  │   Network    │  │  • Hybrid (future)   │  │                  │       │
│  │ • Energy /   │  │                      │  │                  │       │
│  │   Scoring    │  │                      │  │                  │       │
│  │ • Mutation   │  │                      │  │                  │       │
│  │   Modeling   │  │                      │  │                  │       │
│  │ • Calibration│  │                      │  │                  │       │
│  │ • Sampling   │  │                      │  │                  │       │
│  │   (future)   │  │                      │  │                  │       │
│  │ • Electro-   │  │                      │  │                  │       │
│  │   statics    │  │                      │  │                  │       │
│  │   (future)   │  │                      │  │                  │       │
│  └──────────────┘  └──────────────────────┘  └──────────────────┘       │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                          SHARED KERNEL                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Immutable Pydantic Schemas (backward-compatible)                │    │
│  │                                                                 │    │
│  │  AnalysisRequest · PhysicalEvidence · StructuralMechanism        │    │
│  │  FunctionalHypothesis · ReverseCandidate · ConsistencyCheck      │    │
│  │  MissingEvidence · ValidationStep · PSFReport                   │    │
│  │                                                                 │    │
│  │  EvidenceStatus: observed | computed | inferred | required       │    │
│  │  Provenance · Claim · Direction · Confidence                     │    │
│  │  Deterministic SHA-256-based report-local IDs                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                     INFRASTRUCTURE (side adapters)                       │
│                                                                          │
│  Execution Backend    Report Repository    LLM Provider Gateway          │
│  InlineExecution ·    InMemoryReport ·     LLMProvider (protocol)        │
│  TaskQueue (future)   SQLite (future)      Anthropic/OpenAI (future)     │
│                                                                          │
│  Literature Source      External Modeler      External Simulation        │
│  Knowledge Base         FoldX / Rosetta       OpenMM / APBS              │
│  (future)               (future)              (future)                   │
└──────────────────────────────────────────────────────────────────────────┘
```

## Dependency Direction

```
Delivery (CLI / FastAPI / Workbench)
    │
    │  depends on  ApplicationRunnerProtocol  +  Schemas
    │  (never imports physical or reasoning internals directly)
    │
    ▼
Application Orchestrator (AnalysisService, AnalysisRunner)
    │
    │  depends on  Reasoning Protocols  +  PhysicalEvidenceProvider  +  Schemas
    │  (orchestrates; does not own computation or reasoning logic)
    │
    ├──────────────┬──────────────────┐
    ▼              ▼                  ▼
Physical        Reasoning          Consistency
Evidence        Engines            & Verification
Pipeline
    │              │                  │
    └──────────────┴──────────────────┘
                   │
                   ▼
             Shared Kernel (Schemas)
```

**Core rules:**

- Physical and Reasoning are **peer capability domains** orchestrated by Application, not layers in a hierarchy.
- Application depends on protocols (`ForwardReasoner`, `PhysicalEvidenceProvider`), never on concrete implementations.
- Schemas (Shared Kernel) are imported by every layer.  They are immutable value objects, not a "bottom" runtime layer.
- Infrastructure adapters sit **beside** the core, not above or below it.
- Delivery adapters (CLI, API) depend only on `AnalysisRunnerProtocol` and schemas.  They call `bootstrap.create_default_runner()` at startup.
- Composition root (`bootstrap.py`) wires concrete implementations; domain code never imports it.

## Key Packages

| Package | Role | Depends On |
|---------|------|-----------|
| `schemas/` | Shared Kernel — immutable scientific contracts | nothing internal |
| `physical/` | Physical evidence computation | `schemas/`, `identifiers.py` |
| `reasoning/` | Reasoning protocols + baseline engine + LLM port | `schemas/`, `identifiers.py` |
| `application/` | Orchestration, runner facade, application ports | `reasoning/` protocols, `physical/` protocols, `schemas/` |
| `infrastructure/` | Concrete adapters (execution, storage) | `application/ports.py` (protocols), `schemas/` |
| `api/` | FastAPI delivery adapter | `application/` (ports + runner), `bootstrap.py`, `schemas/` |
| `cli.py` | Typer delivery adapter | `application/ports.py`, `bootstrap.py`, `schemas/` |
| `bootstrap.py` | Composition root | `application/`, `physical/`, `reasoning/`, `infrastructure/` |

## Evidence Status Semantics

| Status | Meaning | Example |
|--------|---------|---------|
| `observed` | Directly measured or parsed from a supplied source | Atom coordinates from a PDB file |
| `computed` | Produced by a declared computational method with parameters | Nearest heavy-atom distance via `gemmi` geometry |
| `inferred` | Derived from a rule or scientific prior | Side-chain size class from residue identity |
| `required` | Predicted evidence that should exist if a reverse mechanism is true | Expected contact loss for a packing mechanism |

Every evidence item records its method, parameters, provenance, and limitations.  Computed evidence must never be labelled as observed.

## Causal Traceability

Every evidence item, mechanism, hypothesis, reverse candidate, and consistency
check carries a stable report-local ID derived from its content
(`SHA-256`).  `supports` and `contradicts` fields reference upstream claim
IDs, forming a directed acyclic graph that a client can render and audit.

## Reasoning Protocols

```python
class ForwardReasoner(Protocol):
    def reason(self, request: AnalysisRequest, evidence: tuple[PhysicalEvidence, ...]) -> ForwardResult: ...

class ReverseReasoner(Protocol):
    def reason(self, request: AnalysisRequest, evidence: tuple[PhysicalEvidence, ...]) -> ReverseResult: ...

class ConsistencyChecker(Protocol):
    def check(self, forward: ForwardResult, reverse: ReverseResult, evidence: tuple[PhysicalEvidence, ...]) -> tuple[ConsistencyCheck, ...]: ...
```

**Current implementations (all in `reasoning/baseline.py`):**

- `BaselineForwardReasoner` — deterministic rule-based forward chain
- `BaselineReverseReasoner` — deterministic rule-based reverse chain
- `BaselineConsistencyChecker` — mechanism-type convergence check

**Future implementations (all implement the same protocols):**

- `LLMForwardReasoner` / `LLMReverseReasoner` — LLM interprets evidence, proposes mechanisms, integrates literature
- `HybridRouter` — selects, combines, or compares baseline and LLM outputs
- `EnsembleReasoner` — runs multiple reasoners and reconciles results

## Adding a Physical Evidence Provider

1. Implement `PhysicalEvidenceProvider` protocol (`physical/base.py`).
2. Return typed `PhysicalEvidence` with method, parameters, status, and confidence.
3. Register in `bootstrap.py` — no changes to CLI, API, or `AnalysisService` needed.
4. Add fixtures with known geometric or energetic expectations.
5. Update reasoning rules only when a new evidence type changes interpretation.

## Adding a Reasoning Engine

1. Implement `ForwardReasoner`, `ReverseReasoner`, or `ConsistencyChecker` protocol.
2. Wire into `bootstrap.py` alongside or in place of the baseline engine.
3. All delivery adapters and the orchestrator are protocol-compatible — no changes needed.

## Application Ports

`application/ports.py` defines the stable interfaces that infrastructure
adapters implement:

- `ExecutionBackend` — synchronous or asynchronous analysis execution
- `ReportRepository` — report persistence and retrieval
- `ReportNotFoundError` — raised when a report does not exist
- `AnalysisError` / `StructureInputError` / `ReportLookupError` — application-level
  exceptions that delivery adapters depend on

`AnalysisRunner` converts domain-level exceptions (`StructureAnalysisError`
from physical, `ReportNotFoundError` from the repository contract) into
these application exceptions so that CLI and API never import physical or
infrastructure error types directly.

## Adding an Infrastructure Adapter

1. Implement the protocol defined in `application/ports.py`.
2. Inject through `bootstrap.py`.
3. Core domain code never imports the concrete adapter.

## LLM Provider Port (Future)

`reasoning/ports.py` defines the `LLMProvider` protocol, `LLMCompletion`, and
`LLMUsage`.  LLM-powered reasoners depend on this protocol, not on specific
vendor SDKs.  The protocol lives in `reasoning/` (not `infrastructure/`) so
future reasoners never need to import from the infrastructure layer.

Concrete implementations (Anthropic, OpenAI, local models) are infrastructure
adapters injected through the composition root.

**Current status:** protocol + DTOs defined; no concrete provider implemented.

## Composition Root

`bootstrap.py` wires default implementations.  It is the **only** module that
imports both domain interfaces and concrete infrastructure adapters.  Delivery
adapters call `create_default_runner()` at startup; tests may call
`create_default_service()` for integration coverage.

## Extension Rules

1. Scientific calculators implement `PhysicalEvidenceProvider` — never depend on delivery frameworks.
2. Reasoning engines implement `ForwardReasoner` / `ReverseReasoner` / `ConsistencyChecker` (from `reasoning/protocols.py`).
3. LLM-powered reasoners depend on `LLMProvider` (from `reasoning/ports.py`), never on vendor SDKs.
4. Infrastructure adapters implement protocols defined in `application/ports.py`.
5. Application exceptions (`application/ports.py`) are the only error types delivery adapters catch.
6. Schemas are immutable and backward-compatible — use `model_copy(update=...)` for derived values.
7. Domain code never imports `FastAPI`, `Typer`, task queues, database drivers, or vendor SDKs.
8. Core packages (`schemas`, `physical`, `reasoning`, `application/service.py`) never import from `infrastructure/`.
