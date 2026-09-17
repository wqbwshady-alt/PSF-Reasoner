"""FastAPI delivery adapter and local analysis workbench.

Route definitions live here; structure-input resolution, upload
handling, and V3 orchestration live in ``input_service``,
``upload_service``, and ``v3_service`` respectively.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from psf_reasoner.api.exports import report_to_csv, report_to_json, report_to_pymol
from psf_reasoner.api.input_service import EXAMPLES_DIR, resolve_request
from psf_reasoner.api.task_service import TaskService
from psf_reasoner.api.upload_service import store_upload
from psf_reasoner.api.v3_service import build_v3_payload, run_analysis, v3_max_age_seconds
from psf_reasoner.application.ports import ReportLookupError
from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.component_status import component_registry
from psf_reasoner.infrastructure.task_repository import TaskRepository
from psf_reasoner.infrastructure.uploads import maintain_uploads, resolve_upload
from psf_reasoner.infrastructure.v3_repository import V3ReportNotFoundError, V3ReportRepository
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


def create_app(
    runner: AnalysisRunnerProtocol | None = None,
    upload_dir: Path | None = None,
    v3_store: V3ReportRepository | None = None,
    task_store: TaskRepository | None = None,
) -> FastAPI:
    # The workbench persists reports by default so exports survive
    # restarts; PSF_PERSIST=0 restores in-memory behaviour.
    active_runner = runner or create_default_runner(persist=os.environ.get("PSF_PERSIST", "1") != "0")
    _upload_dir = upload_dir or UPLOAD_DIR
    _v3_store = v3_store or V3ReportRepository()
    _task_store = task_store or TaskRepository()
    _task_service = TaskService(
        _task_store,
        active_runner,
        _upload_dir,
        _v3_store,
        max_queue=int(os.environ.get("PSF_TASK_MAX_QUEUE", "8")),
        max_workers=int(os.environ.get("PSF_TASK_WORKERS", "2")),
        timeout_seconds=float(os.environ.get("PSF_TASK_TIMEOUT_SECONDS", "600")),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Directory creation and pruning run at startup, never at import
        # time.  All maintenance calls are idempotent; stale running
        # tasks from a previous process are failed here.
        _upload_dir.mkdir(parents=True, exist_ok=True)
        maintain_uploads(_upload_dir)
        _v3_store.prune_old(max_age_seconds=v3_max_age_seconds())
        _task_store.prune_old_finished(max_age_seconds=7 * 86_400)
        _task_service.start()
        try:
            yield
        finally:
            _task_service.shutdown()

    api = FastAPI(
        title="PSF-Reasoner API",
        version="0.1.0",
        description="Bidirectional physical-structural-functional reasoning.",
        lifespan=lifespan,
    )

    @api.get("/health")
    def health() -> dict:
        """Liveness plus optional-component status.

        The components block reports which optional integrations (LLM,
        cloud compute, FoldX, …) are enabled, available, and which
        implementation is actually in use.
        """
        return {"status": "ok", "components": component_registry.snapshot()}

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
        return run_analysis(active_runner, resolve_request(request, _upload_dir))

    @api.post("/reverse", response_model=PSFReport)
    def reverse(request: AnalysisRequest) -> PSFReport:
        if request.phenotype is None or request.mutation is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="reverse requires phenotype and does not accept mutation",
            )
        return run_analysis(active_runner, resolve_request(request, _upload_dir))

    @api.post("/analyze", response_model=PSFReport)
    def analyze(request: AnalysisRequest) -> PSFReport:
        if request.mutation is None or request.phenotype is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="analyze requires both mutation and phenotype",
            )
        return run_analysis(active_runner, resolve_request(request, _upload_dir))

    @api.post("/analyze-upload", response_model=PSFReport)
    async def analyze_upload(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        mutation: Annotated[str, Form()],
        mutant_file: Annotated[UploadFile | None, File()] = None,
        chain: Annotated[str | None, Form()] = None,
        phenotype: Annotated[str | None, Form()] = None,
    ) -> PSFReport:
        request = await _multipart_request(
            _upload_dir,
            reference_file=reference_file,
            ligand=ligand,
            mutation=mutation,
            mutant_file=mutant_file,
            chain=chain,
            phenotype=phenotype,
        )
        return run_analysis(active_runner, request)

    @api.post("/reverse-upload", response_model=PSFReport)
    async def reverse_upload(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        phenotype: Annotated[str, Form()],
    ) -> PSFReport:
        request = await _multipart_request(
            _upload_dir,
            reference_file=reference_file,
            ligand=ligand,
            phenotype=phenotype,
        )
        return run_analysis(active_runner, request)

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
        """V3 analysis — compatibility synchronous interface.

        Prefer ``POST /v3/analyze/async`` for long-running analyses so
        request threads are not blocked.
        """
        return build_v3_payload(active_runner, request, _upload_dir, _v3_store)

    @api.post("/v3/analyze/async", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
    def v3_analyze_async(request: AnalysisRequest) -> dict:
        """Submit a V3 analysis to the background queue; poll GET /tasks/{task_id}."""
        task_id = _task_service.submit(request)
        return {"task_id": task_id, "status_url": f"/tasks/{task_id}"}

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
        request = await _multipart_request(
            _upload_dir,
            reference_file=reference_file,
            ligand=ligand,
            mutation=mutation,
            mutant_file=mutant_file,
            chain=chain,
            phenotype=phenotype,
        )
        return build_v3_payload(active_runner, request, _upload_dir, _v3_store)

    @api.post("/v3/analyze-upload/async", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
    async def v3_analyze_upload_async(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        mutation: Annotated[str, Form()],
        mutant_file: Annotated[UploadFile | None, File()] = None,
        chain: Annotated[str | None, Form()] = None,
        phenotype: Annotated[str | None, Form()] = None,
    ) -> dict:
        """Submit a multipart V3 analysis to the background queue."""
        request = await _multipart_request(
            _upload_dir,
            reference_file=reference_file,
            ligand=ligand,
            mutation=mutation,
            mutant_file=mutant_file,
            chain=chain,
            phenotype=phenotype,
        )
        task_id = _task_service.submit(request, stage="structure_parse")
        return {"task_id": task_id, "status_url": f"/tasks/{task_id}"}

    @api.get("/tasks/{task_id}")
    def get_task(task_id: str) -> dict:
        """Background task status: queued/running/succeeded/failed + stage."""
        return _task_service.get_view(task_id)

    @api.get("/tasks")
    def list_tasks(limit: int = 20) -> dict:
        """Recent background tasks, newest first."""
        return {"tasks": _task_service.list_views(limit=limit)}

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


async def _multipart_request(
    upload_dir: Path,
    *,
    reference_file: UploadFile,
    ligand: str,
    mutation: str | None = None,
    mutant_file: UploadFile | None = None,
    chain: str | None = None,
    phenotype: str | None = None,
) -> AnalysisRequest:
    """Store multipart uploads and build the matching ``AnalysisRequest``."""
    reference_path = await store_upload(reference_file, upload_dir)
    mutant_path = (
        await store_upload(mutant_file, upload_dir)
        if mutant_file is not None and mutant_file.filename
        else None
    )
    return AnalysisRequest(
        structure=StructureInput(path=str(reference_path), upload_id=reference_path.name),
        mutant_structure=StructureInput(path=str(mutant_path), upload_id=mutant_path.name)
        if mutant_path
        else None,
        ligand=LigandSpec(identifier=ligand),
        mutation=MutationSpec(notation=mutation, chain=chain or None) if mutation else None,
        phenotype=PhenotypeSpec(name=phenotype) if phenotype else None,
    )


app = create_app()
