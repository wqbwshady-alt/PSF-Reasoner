"""V3 analysis orchestration — V2 report + structural context + causal graph.

The combined payload is persisted in the shared SQLite storage (see
``psf_reasoner.infrastructure.v3_repository``) so exports survive
restarts and work across processes.
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException, status

from psf_reasoner.api.input_service import resolve_request
from psf_reasoner.application.ports import StructureInputError
from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.infrastructure.v3_repository import V3ReportRepository
from psf_reasoner.physical.identity import extract_protein_identity
from psf_reasoner.schemas.inputs import AnalysisRequest
from psf_reasoner.schemas.report import PSFReport

# Progress callback: (stage, fraction) — used by the background task
# executor to record fine-grained progress.
ProgressCallback = Callable[[str, float], None]

DEFAULT_V3_MAX_AGE_DAYS = 30


def v3_max_age_seconds() -> float:
    """V3 report retention, days (env PSF_V3_MAX_AGE_DAYS, default 30)."""
    import os

    raw = os.environ.get("PSF_V3_MAX_AGE_DAYS", str(DEFAULT_V3_MAX_AGE_DAYS))
    try:
        days = float(raw)
    except ValueError:
        days = DEFAULT_V3_MAX_AGE_DAYS
    return max(days, 1.0) * 86_400


def build_v3_payload(
    runner: AnalysisRunnerProtocol,
    request: AnalysisRequest,
    upload_dir: Path,
    v3_store: V3ReportRepository,
    progress: ProgressCallback | None = None,
) -> dict:
    """Run the full V3 analysis and store the combined payload for export.

    Protein identity comes from the structure header, not from the ligand
    abbreviation.  When the identity cannot be determined, literature
    evidence stays empty rather than falling back to another protein.
    """
    from psf_reasoner.context.structural_context_builder import (
        StructuralContextBuilder,
    )
    from psf_reasoner.knowledge.literature_evidence import get_evidence_summary
    from psf_reasoner.reasoning.mechanism_generator import MechanismGenerator

    if request.mutation is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="v3/analyze requires a mutation (notation like V82A)",
        )
    resolved = resolve_request(request, upload_dir)
    if progress is not None:
        progress("v2_analysis", 0.4)
    v2_report = run_analysis(runner, resolved)
    if progress is not None:
        progress("v3_orchestration", 0.7)

    identity = extract_protein_identity(resolved.structure.path)
    family = identity.family_hint

    if resolved.mutant_structure is not None:
        ctx = StructuralContextBuilder().build(
            resolved,
            qc_report=v2_report.structure_qc,
            protein_family_hint=family,
        )
        graph = MechanismGenerator().generate(ctx, protein_family=family)
    else:
        # No mutant structure: no structural context / causal graph can be
        # honestly computed.  Say so instead of fabricating changes.
        ctx = None
        graph = None

    lit_summary = (
        get_evidence_summary(family, resolved.mutation.notation)
        if family
        else {
            "protein_family": "",
            "total_entries": 0,
            "by_grade": {},
            "has_direct_evidence": False,
            "has_quantitative_evidence": False,
        }
    )

    mutation_site = ctx.mutation_site if ctx else {}
    payload: dict = {
        "report_id": v2_report.report_id,
        "v2_report": v2_report.model_dump(),
        "protein_identity": identity.to_dict(),
        "v3_context": (
            {
                "mutation_site": mutation_site,
                "structural_differences": ctx.structural_differences,
                "ligand_decomposition": ctx.ligand_decomposition,
                "neighborhood_4a": ctx.neighborhood_4a,
                "neighborhood_6a": ctx.neighborhood_6a,
                "qc_grade": ctx.qc_grade,
            }
            if ctx
            else {
                "note": "mutant structure not supplied — structural comparison "
                "was not computed and no structural changes are claimed."
            }
        ),
        "v3_causal_graph": graph.to_dict() if graph else None,
        "v3_literature": lit_summary,
        "evidence_localization": {
            "mutation_chain": resolved.mutation.chain or "",
            "mutation_residue_number": resolved.mutation.residue_number,
            "mutation_label": mutation_site.get("residue_label", ""),
            "ligand": resolved.ligand.identifier,
            "neighborhood_4a": [n.get("label", "") for n in ctx.neighborhood_4a] if ctx else [],
        },
    }
    v3_store.save(payload)
    if progress is not None:
        progress("export_ready", 1.0)
    return payload


def run_analysis(runner: AnalysisRunnerProtocol, request: AnalysisRequest) -> PSFReport:
    """Run an analysis, mapping application errors onto HTTP 422."""
    try:
        return runner.run(request)
    except StructureInputError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
