"""FastAPI delivery adapter and local analysis workbench."""

from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from psf_reasoner.application.ports import ReportLookupError, StructureInputError
from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.uploads import maintain_uploads, resolve_upload
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
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_STRUCTURE_SUFFIXES = frozenset({".cif", ".mmcif", ".pdb"})


def _resolve_structure_input(si: StructureInput, upload_dir: Path) -> StructureInput:
    """Validate and resolve a ``StructureInput`` for API use.

    API endpoints must NOT accept raw filesystem paths.  Callers must either
    upload a file (multipart) and reference it by ``upload_id``, or use the
    upload-ID returned by a prior upload.

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

    # No upload_id — path must be set (enforced by schema validator).
    # Accept paths inside the upload store or any local file that exists
    # (the API is a local workbench, not a public service).
    if si.path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="structure must provide either upload_id or path",
        )
    resolved = Path(si.path).resolve()
    upload_root = upload_dir.resolve()
    if str(resolved).startswith(str(upload_root) + "/") or resolved == upload_root:
        return si
    # Accept any local file that exists (for CLI/example parity)
    if resolved.is_file():
        return si

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Structure file not found. "
            "Upload the file via multipart form first, then "
            "reference it by upload_id, or provide a valid local path."
        ),
    )


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
) -> FastAPI:
    active_runner = runner or create_default_runner()
    _upload_dir = upload_dir or UPLOAD_DIR
    _upload_dir.mkdir(parents=True, exist_ok=True)
    api = FastAPI(
        title="PSF-Reasoner API",
        version="0.1.0",
        description="Bidirectional physical-structural-functional reasoning.",
    )

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/v3/status")
    def v3_status() -> dict:
        """V3 research dashboard — dataset, model, and audit status."""
        from psf_reasoner.datasets.expansion import audit_expansion
        from psf_reasoner.calibration.identity_audit import run_identity_audit

        exp = audit_expansion()
        identity = run_identity_audit()

        return {
            "dataset": {
                "total_cases": exp.total,
                "target": exp.target,
                "families": exp.total_families,
                "families_can_evaluate_within": exp.can_evaluate_within_family,
                "structure_coverage": round(exp.structure_coverage, 2),
                "contact_coverage": round(exp.contact_coverage, 2),
                "family_label_matrix": {k: dict(v) for k, v in exp.family_label_matrix.items()},
            },
            "identity_audit": {
                "baselines": identity["identity_baselines"],
                "within_family_evaluable": sum(
                    1 for v in identity["within_family"].values() if v.get("can_evaluate")
                ),
                "within_family_total": len(identity["within_family"]),
                "cross_family_mean_mcc": round(
                    sum(v.get("mcc", 0) for v in identity["cross_family"].values())
                    / max(len(identity["cross_family"]), 1), 3
                ),
            },
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
            # Legacy fallback — only serve files inside the upload directory.
            file_path = Path(path).resolve()
            upload_root = _upload_dir.resolve()
            if not (str(file_path).startswith(str(upload_root) + "/") or file_path == upload_root):
                raise HTTPException(
                    status_code=403,
                    detail="only uploaded structure files can be served",
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
        """V3 analysis — returns structural context + causal graph + V2 report."""
        if request.mutation is None or request.mutant_structure is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="v3/analyze requires both mutation and mutant_structure",
            )
        resolved = _resolve_request(request, _upload_dir)
        # V2 report as baseline
        v2_report = _run(active_runner, resolved)

        # V3 structural context + causal graph
        from psf_reasoner.context.structural_context_builder import StructuralContextBuilder
        from psf_reasoner.reasoning.mechanism_generator import MechanismGenerator
        from psf_reasoner.knowledge.literature_evidence import get_evidence_summary
        import dataclasses

        ctx_builder = StructuralContextBuilder()
        ctx = ctx_builder.build(resolved, qc_report=v2_report.structure_qc)

        gen = MechanismGenerator()
        graph = gen.generate(ctx)

        lit_summary = get_evidence_summary(
            "HIV-1_PROTEASE" if "MK1" in resolved.ligand.identifier.upper()
            else "DHFR" if "MTX" in resolved.ligand.identifier.upper()
            else "",
            resolved.mutation.notation,
        )

        return {
            "v2_report": v2_report.model_dump(),
            "v3_context": {
                "mutation_site": ctx.mutation_site,
                "structural_differences": ctx.structural_differences,
                "ligand_decomposition": ctx.ligand_decomposition,
                "neighborhood_4a": ctx.neighborhood_4a,
                "neighborhood_6a": ctx.neighborhood_6a,
                "qc_grade": ctx.qc_grade,
            },
            "v3_causal_graph": graph.to_dict(),
            "v3_literature": lit_summary,
        }

    @api.post("/admin/maintain-uploads")
    def maintain_uploads_endpoint() -> dict:
        """Remove expired and excess upload files.  Idempotent."""
        result = maintain_uploads(_upload_dir)
        return {"status": "ok", **result}

    # Run upload maintenance once at startup.
    maintain_uploads(_upload_dir)

    api.mount("/client", StaticFiles(directory=STATIC_DIR), name="client")
    return api


def _run(runner: AnalysisRunnerProtocol, request: AnalysisRequest) -> PSFReport:
    try:
        return runner.run(request)
    except StructureInputError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


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
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return destination


app = create_app()
