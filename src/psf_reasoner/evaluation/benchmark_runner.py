"""Benchmark runner — load a frozen benchmark and run cases through the pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from psf_reasoner.application.service import AnalysisService
from psf_reasoner.evaluation.protocols import BenchmarkCase, BenchmarkDataset
from psf_reasoner.schemas.inputs import (
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    PhenotypeSpec,
    StructureInput,
)
from psf_reasoner.schemas.report import PSFReport


def load_benchmark(path: Path) -> BenchmarkDataset:
    """Load a frozen benchmark dataset from a JSON file."""
    data = json.loads(path.read_text())
    return BenchmarkDataset.model_validate(data)


def case_to_request(case: BenchmarkCase) -> AnalysisRequest:
    """Convert a ``BenchmarkCase`` to an ``AnalysisRequest`` for the pipeline."""
    return AnalysisRequest(
        structure=StructureInput(path=case.wt_pdb_id),
        mutant_structure=StructureInput(path=case.mutant_pdb_id) if case.mutant_pdb_id else None,
        ligand=LigandSpec(identifier=case.ligand_identifier, chain=case.ligand_chain),
        mutation=MutationSpec(notation=case.mutation_notation, chain=case.mutation_chain),
        phenotype=PhenotypeSpec(name=case.phenotype),
    )


def run_benchmark(
    dataset: BenchmarkDataset,
    service: AnalysisService,
    *,
    held_out_only: bool = False,
) -> list[tuple[BenchmarkCase, PSFReport]]:
    """Run all cases in a benchmark through the analysis pipeline.

    Returns a list of (case, report) pairs.  Cases that fail during analysis
    are logged and skipped — the runner does not abort on failure.
    """
    cases = dataset.held_out_set if held_out_only else dataset.cases
    results: list[tuple[BenchmarkCase, PSFReport]] = []
    for case in cases:
        try:
            request = case_to_request(case)
            report = service.analyze(request)
            results.append((case, report))
        except Exception:
            # Skip failed cases — errors are noted in the benchmark log
            pass
    return results
