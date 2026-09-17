"""FastAPI delivery adapter and local analysis workbench."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from psf_reasoner.api.exports import report_to_csv, report_to_json, report_to_pymol
from psf_reasoner.application.ports import ReportLookupError, StructureInputError
from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.uploads import (
    InvalidStructureError,
    maintain_uploads,
    resolve_upload,
    validate_structure_file,
)
from psf_reasoner.infrastructure.v3_repository import V3ReportNotFoundError, V3ReportRepository
from psf_reasoner.physical.identity import extract_protein_identity
from psf_reasoner.schemas.inputs import (
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    PhenotypeSpec,
    StructureInput,
)
from psf_reasoner.schemas.report import PSFReport

STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = Path.cwd() / ".psf_uploads"
EXAMPLES_DIR = Path(__file__).parents[3] / "examples" / "data"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_STRUCTURE_SUFFIXES = frozenset({".cif", ".mmcif", ".pdb"})
DEFAULT_V3_MAX_AGE_DAYS = 30


def _resolve_structure_input(si: StructureInput, upload_dir: Path) -> StructureInput:
    """Validate and resolve a ``StructureInput`` for API use.

    API endpoints must NOT accept raw filesystem paths.  Callers must either
    upload a file (multipart) and reference it by ``upload_id``, or use one
    of the bundled example structures.  The CLI is the entry point for
    arbitrary user-provided local files — this boundary keeps the web API
    from reading any path a request happens to name.

    Returns a new ``StructureInput`` whose ``path`` is resolved from the
    upload store.  Raises ``HTTPException`` (400) if a raw filesystem path
    is provided without an upload ID.
    """
    if si.upload_id:
        try:
            resolved = resolve_upload(si.upload_id, upload_dir)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"upload_id not found: {si.upload_id}",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        return StructureInput(
            path=str(resolved),
            upload_id=si.upload_id,
            format=si.format,
            model_index=si.model_index,
        )

    # No upload_id — path must be set (enforced by schema validator) and
    # must stay inside the upload store or the bundled examples.  The
    # resolve()-based containment check also rejects escaping symlinks,
    # absolute paths, and parent traversal.
    if si.path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="structure must provide either upload_id or path",
        )
    resolved = Path(si.path).resolve()
    allowed_roots = (upload_dir.resolve(), EXAMPLES_DIR.resolve())
    if not any(root == resolved or root in resolved.parents for root in allowed_roots):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "path is not allowed: the web API only accepts uploaded files "
                "(by upload_id) or bundled example structures.  Use the CLI "
                "to analyze an arbitrary local file."
            ),
        )
    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "structure file not found.  Upload the file via multipart "
                "form first, then reference it by upload_id."
            ),
        )
    return si


def _resolve_request(
    request: AnalysisRequest,
    upload_dir: Path,
) -> AnalysisRequest:
    """Resolve all ``StructureInput`` fields in *request* through the upload store."""
    return AnalysisRequest(
        structure=_resolve_structure_input(request.structure, upload_dir),
        mutant_structure=_resolve_structure_input(request.mutant_structure, upload_dir)
        if request.mutant_structure
        else None,
        ligand=request.ligand,
        mutation=request.mutation,
        phenotype=request.phenotype,
        study_context=request.study_context,
    )


def create_app(
    runner: AnalysisRunnerProtocol | None = None,
    upload_dir: Path | None = None,
    v3_store: V3ReportRepository | None = None,
) -> FastAPI:
    # The workbench persists reports by default so exports survive
    # restarts; PSF_PERSIST=0 restores in-memory behaviour.
    active_runner = runner or create_default_runner(
        persist=os.environ.get("PSF_PERSIST", "1") != "0"
    )
    _upload_dir = upload_dir or UPLOAD_DIR
    _v3_store = v3_store or V3ReportRepository()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Directory creation and pruning run at startup, never at import
        # time.  Both maintenance calls are idempotent.
        _upload_dir.mkdir(parents=True, exist_ok=True)
        maintain_uploads(_upload_dir)
        _v3_store.prune_old(max_age_seconds=_v3_max_age_seconds())
        yield

    api = FastAPI(
        title="PSF-Reasoner API",
        version="0.1.0",
        description="Bidirectional physical-structural-functional reasoning.",
        lifespan=lifespan,
    )

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/v3/status")
    def v3_status() -> dict:
        """V3 dataset status — case inventory and review state.

        Calibration-model audit numbers are NOT re-trained per request here;
        see pilot_validity_audit/ for the offline snapshot and its caveats.
        """
        from psf_reasoner.datasets.golden_cases import load_golden_cases
        from psf_reasoner.datasets.quality_control import run_dataset_qc

        cases = load_golden_cases()
        qc = run_dataset_qc(cases)
        return {
            "dataset": {
                "total_cases": qc.total_samples,
                "accepted": qc.accepted,
                "pending": qc.pending,
                "rejected": qc.rejected,
                "needs_clarification": qc.needs_clarification,
                "structure_pairs": qc.has_structure_pair,
                "with_ddg": qc.has_ddg,
                "protein_systems": qc.protein_systems,
                "sample_issues": qc.sample_issues[:20],
            },
            "calibration_note": (
                "calibration models are NOT trained per request.  Offline audit "
                "snapshot lives in pilot_validity_audit/; all report confidence "
                "values remain heuristic (uncalibrated)."
            ),
        }

    @api.get("/", include_in_schema=False)
    def workbench() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @api.post("/forward", response_model=PSFReport)
    def forward(request: AnalysisRequest) -> PSFReport:
        if request.mutation is None or request.phenotype is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="forward requires mutation and does not accept phenotype",
            )
        return _run(active_runner, _resolve_request(request, _upload_dir))

    @api.post("/reverse", response_model=PSFReport)
    def reverse(request: AnalysisRequest) -> PSFReport:
        if request.phenotype is None or request.mutation is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="reverse requires phenotype and does not accept mutation",
            )
        return _run(active_runner, _resolve_request(request, _upload_dir))

    @api.post("/analyze", response_model=PSFReport)
    def analyze(request: AnalysisRequest) -> PSFReport:
        if request.mutation is None or request.phenotype is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="analyze requires both mutation and phenotype",
            )
        return _run(active_runner, _resolve_request(request, _upload_dir))

    @api.post("/analyze-upload", response_model=PSFReport)
    async def analyze_upload(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        mutation: Annotated[str, Form()],
        mutant_file: Annotated[UploadFile | None, File()] = None,
        chain: Annotated[str | None, Form()] = None,
        phenotype: Annotated[str | None, Form()] = None,
    ) -> PSFReport:
        reference_path = await _store_upload(reference_file, _upload_dir)
        mutant_path = (
            await _store_upload(mutant_file, _upload_dir)
            if mutant_file is not None and mutant_file.filename
            else None
        )
        request = AnalysisRequest(
            structure=StructureInput(path=str(reference_path), upload_id=reference_path.name),
            mutant_structure=StructureInput(path=str(mutant_path), upload_id=mutant_path.name)
            if mutant_path
            else None,
            ligand=LigandSpec(identifier=ligand),
            mutation=MutationSpec(notation=mutation, chain=chain or None),
            phenotype=PhenotypeSpec(name=phenotype) if phenotype else None,
        )
        return _run(active_runner, request)

    @api.post("/reverse-upload", response_model=PSFReport)
    async def reverse_upload(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        phenotype: Annotated[str, Form()],
    ) -> PSFReport:
        reference_path = await _store_upload(reference_file, _upload_dir)
        request = AnalysisRequest(
            structure=StructureInput(path=str(reference_path), upload_id=reference_path.name),
            ligand=LigandSpec(identifier=ligand),
            phenotype=PhenotypeSpec(name=phenotype),
        )
        return _run(active_runner, request)

    @api.get("/reports/{report_id}", response_model=PSFReport)
    def get_report(report_id: str) -> PSFReport:
        try:
            return active_runner.get_report(report_id)
        except ReportLookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found") from error

    @api.get("/structure")
    def get_structure(upload_id: str | None = None, path: str | None = None) -> PlainTextResponse:
        """Serve an uploaded structure file as PDB text for the 3D viewer.

        Prefer *upload_id* to look up a previously uploaded file.  The
        *path* parameter is accepted only for backward compatibility with
        files already inside the upload store.
        """
        import gemmi

        if upload_id:
            try:
                file_path = resolve_upload(upload_id, _upload_dir)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        elif path:
            # Only serve files inside the upload directory or the bundled
            # examples/data directory (the local workbench demo fixtures).
            file_path = Path(path).resolve()
            upload_root = _upload_dir.resolve()
            examples_root = EXAMPLES_DIR.resolve()
            allowed = (
                str(file_path).startswith(str(upload_root) + "/")
                or file_path == upload_root
                or str(file_path).startswith(str(examples_root) + "/")
            )
            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail="only uploaded or bundled example structure files can be served",
                )
            if not file_path.is_file():
                raise HTTPException(status_code=404, detail="structure file not found")
        else:
            raise HTTPException(
                status_code=400,
                detail="upload_id or path query parameter is required",
            )
        try:
            structure = gemmi.read_structure(str(file_path))
            pdb_text = structure.make_minimal_pdb()
            # Strip ANISOU lines (3Dmol.js can choke on them)
            lines = [line for line in pdb_text.splitlines() if not line.startswith("ANISOU")]
            if lines and not lines[-1].startswith("END"):
                lines.append("END")
            pdb_text = "\n".join(lines)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"failed to read structure: {e}") from e
        return PlainTextResponse(pdb_text, media_type="text/plain")

    @api.post("/v3/analyze", response_model=dict)
    def v3_analyze(request: AnalysisRequest) -> dict:
        """V3 analysis — V2 report + structural context + causal graph + literature."""
        return _build_v3_payload(active_runner, request, _upload_dir, _v3_store)

    @api.post("/v3/analyze-upload", response_model=dict)
    async def v3_analyze_upload(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        mutation: Annotated[str, Form()],
        mutant_file: Annotated[UploadFile | None, File()] = None,
        chain: Annotated[str | None, Form()] = None,
        phenotype: Annotated[str | None, Form()] = None,
    ) -> dict:
        """V3 analysis from multipart uploads — the main workbench entry point."""
        reference_path = await _store_upload(reference_file, _upload_dir)
        mutant_path = (
            await _store_upload(mutant_file, _upload_dir)
            if mutant_file is not None and mutant_file.filename
            else None
        )
        request = AnalysisRequest(
            structure=StructureInput(path=str(reference_path), upload_id=reference_path.name),
            mutant_structure=StructureInput(path=str(mutant_path), upload_id=mutant_path.name)
            if mutant_path
            else None,
            ligand=LigandSpec(identifier=ligand),
            mutation=MutationSpec(notation=mutation, chain=chain or None),
            phenotype=PhenotypeSpec(name=phenotype) if phenotype else None,
        )
        return _build_v3_payload(active_runner, request, _upload_dir, _v3_store)

    @api.get("/export/{report_id}")
    def export_report(report_id: str, format: str = "json") -> PlainTextResponse:
        """Export a completed V3 analysis as JSON, CSV, or a PyMOL script."""
        try:
            payload = _v3_store.get(report_id)
        except V3ReportNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "no V3 analysis found for this report_id.  Run a V3 "
                    "analysis first; reports are stored on disk and survive "
                    "restarts."
                ),
            ) from error
        if format == "json":
            content = report_to_json(payload)
            media_type = "application/json"
            filename = f"psf_report_{report_id}.json"
        elif format == "csv":
            content = report_to_csv(payload)
            media_type = "text/csv"
            filename = f"psf_report_{report_id}.csv"
        elif format == "pymol":
            content = report_to_pymol(payload)
            media_type = "text/plain"
            filename = f"psf_session_{report_id}.pml"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="format must be one of: json, csv, pymol",
            )
        return PlainTextResponse(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @api.delete("/v3/reports/{report_id}")
    def delete_v3_report(report_id: str) -> dict:
        """Delete a stored V3 analysis.  Idempotent."""
        deleted = _v3_store.delete(report_id)
        return {"status": "ok", "deleted": deleted}

    api.mount("/client", StaticFiles(directory=STATIC_DIR), name="client")
    return api


def _v3_max_age_seconds() -> float:
    """V3 report retention, days (env PSF_V3_MAX_AGE_DAYS, default 30)."""
    raw = os.environ.get("PSF_V3_MAX_AGE_DAYS", str(DEFAULT_V3_MAX_AGE_DAYS))
    try:
        days = float(raw)
    except ValueError:
        days = DEFAULT_V3_MAX_AGE_DAYS
    return max(days, 1.0) * 86_400


def _run(runner: AnalysisRunnerProtocol, request: AnalysisRequest) -> PSFReport:
    try:
        return runner.run(request)
    except StructureInputError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


def _build_v3_payload(
    runner: AnalysisRunnerProtocol,
    request: AnalysisRequest,
    upload_dir: Path,
    v3_store: V3ReportRepository,
) -> dict:
    """Run the full V3 analysis and store the combined payload for export.

    The payload is persisted in the shared SQLite storage so exports
    survive restarts and work across processes.

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
    resolved = _resolve_request(request, upload_dir)
    v2_report = _run(runner, resolved)

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
    return payload


async def _store_upload(upload: UploadFile, upload_dir: Path) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in SUPPORTED_STRUCTURE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="structure upload must be a .pdb, .cif, or .mmcif file",
        )
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{uuid4().hex}{suffix}"
    size = 0
    try:
        with destination.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="structure upload exceeds the 25 MB local limit",
                    )
                handle.write(chunk)
        # Extension and size alone are not enough: the file must parse as
        # a usable protein structure.  Rejections delete the written file
        # and never leak server paths in the error detail.
        validate_structure_file(destination)
    except InvalidStructureError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return destination


app = create_app()
