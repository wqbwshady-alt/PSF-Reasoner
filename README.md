# PSF-Reasoner

PSF-Reasoner is a bidirectional Physical-Structural-Functional reasoning system
for protein-ligand complexes and mutations.  It combines deterministic physical
computation with structured scientific reasoning to generate auditable,
evidence-backed hypotheses and validation plans.

The first version establishes stable scientific contracts and replaceable system
boundaries. Its built-in rules produce explicit, testable hypotheses; they do
not replace structure-derived measurements or experimental evidence.

## Reasoning directions

```text
Forward: mutation/physical perturbation → physical evidence
        → structural mechanism → functional hypothesis

Reverse: functional phenotype → candidate structural mechanism
        → required physical evidence → validation plan
```

Both directions cross-validate through a shared consistency checker.

## Quick start

Python 3.12 is the reference runtime.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

# Forward: mutation → function
psf forward --structure examples/data/1hsg.cif --ligand MK1 --mutation V82A --chain A

# Forward with paired WT/mutant structures
psf forward --structure wild_type.pdb --mutant-structure v82a.pdb --ligand MK1 --mutation V82A --chain A

# Bidirectional: forward + reverse + consistency
psf analyze --structure examples/data/1sdt.cif --mutant-structure examples/data/1sdv.cif --ligand MK1 --mutation V82A --chain A --phenotype drug_resistance

# Reverse: phenotype → candidate mechanisms
psf reverse --structure examples/data/1hsg.cif --ligand MK1 --phenotype drug_resistance

# Web API + local workbench
uvicorn psf_reasoner.api.app:app --reload
```

The coordinate provider reads PDB/mmCIF structures and reports the nearest heavy-atom
distance and residue-ligand contact under a declared cutoff. Structure preparation
records missing atoms, alternate conformations, explicit waters, preparation
assumptions, and ligand atom typing inferred from local chemistry.

When an explicit `--mutant-structure` is supplied, PSF-Reasoner compares it to
the reference structure at the requested mutation site. It reports deltas for
nearest distance, contact state, residue SASA, ligand-shell geometry proxy, and
typed hydrogen-bond, salt-bridge, pi, hydrophobic-contact, and water-bridge
events. It also computes ligand-pocket residue membership, pocket residue-network
deltas, and a lightweight local interaction score.

If no mutant structure is supplied, the default local modeler attempts conservative
side-chain truncation cases such as V82A and marks the resulting evidence as
modelled. Unsupported mutations fall back to reference-only evidence instead of
fabricating coordinates. Local scores are reproducible structure-derived scores,
not binding free energies.

The built-in HIV-1 protease heuristic currently covers the MK1-bound V82A case
using the public RCSB 1SDT/1SDV structural benchmark and its primary literature
label. The label is qualitative and uncalibrated; it is not a numeric Ki,
Kd, IC50, or resistance fold-change substitute.

The September 2026 evidence audit retains nine literature-verified cases for
evaluation and excludes unverified records from calibration inputs. The first
end-to-end verified example is V82A/MK1. An independent PLIP comparison on
1SDT, 1SDV, and 1SDU is documented in `docs/interaction-validation.md`;
hydrogen bonds remain under-detected in the distributed crystal files, and
the three related structures do not establish cross-system accuracy.

## Architecture

```
DELIVERY: CLI (typer) · FastAPI REST · Web Workbench
              │
              ▼
APPLICATION:  AnalysisService (orchestrator)
              AnalysisRunner (execution + persistence facade)
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
 Physical  Reasoning  Consistency
 Evidence  Engines    & Verification
 Pipeline  (protocols)
              │
              ▼
SHARED KERNEL: Schemas (immutable Pydantic contracts)

INFRASTRUCTURE: Execution · Repository · LLM Gateway (side adapters)
```

**Core packages:**

| Package | Role |
|---------|------|
| `schemas/` | Shared Kernel — immutable scientific contracts (evidence, mechanisms, hypotheses, reports) |
| `physical/` | Deterministic computation — PDB/mmCIF parsing, interaction classification, pocket analysis, mutation modeling |
| `reasoning/` | Reasoning protocols + baseline engine — forward/reverse/consistency, all framework-neutral |
| `application/` | Orchestrator — `AnalysisService` coordinates the pipeline, `AnalysisRunner` provides the delivery facade |
| `infrastructure/` | Side adapters — execution backend, report repository, LLM provider gateway |
| `api/` + `cli.py` | Delivery adapters — FastAPI and Typer, no computation or reasoning logic |
| `bootstrap.py` | Composition root — wires default implementations |

**Design principles:**

- Physical and Reasoning are **peer capability domains** orchestrated by Application, not layers in a hierarchy.
- All reasoning engines (`Baseline`, `LLM`, `Hybrid`) implement the same `ForwardReasoner` / `ReverseReasoner` / `ConsistencyChecker` protocols.
- Evidence status (`observed` | `computed` | `inferred` | `required`) makes the distinction between measurement, computation, and prediction explicit.
- Every claim has a stable ID and `supports`/`contradicts` references — the full causal graph is auditable.
- Core domain code never imports FastAPI, Typer, task queues, or vendor SDKs.

See `docs/architecture.md` for the full system panorama, extension rules, and scientific-status semantics.
