"""FastAPI delivery adapter and local analysis workbench."""

from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from psf_reasoner.application.ports import ReportLookupError, StructureInputError
from psf_reasoner.application.runner import AnalysisRunnerProtocol
from psf_reasoner.bootstrap import create_default_runner
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


def create_app(runner: AnalysisRunnerProtocol | None = None) -> FastAPI:
    active_runner = runner or create_default_runner()
    api = FastAPI(
        title="PSF-Reasoner API",
        version="0.1.0",
        description="Bidirectional physical-structural-functional reasoning.",
    )

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
        return _run(active_runner, request)

    @api.post("/reverse", response_model=PSFReport)
    def reverse(request: AnalysisRequest) -> PSFReport:
        if request.phenotype is None or request.mutation is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="reverse requires phenotype and does not accept mutation",
            )
        return _run(active_runner, request)

    @api.post("/analyze", response_model=PSFReport)
    def analyze(request: AnalysisRequest) -> PSFReport:
        if request.mutation is None or request.phenotype is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="analyze requires both mutation and phenotype",
            )
        return _run(active_runner, request)

    @api.post("/analyze-upload", response_model=PSFReport)
    async def analyze_upload(
        reference_file: Annotated[UploadFile, File(description="WT/reference PDB or mmCIF")],
        ligand: Annotated[str, Form()],
        mutation: Annotated[str, Form()],
        mutant_file: Annotated[UploadFile | None, File()] = None,
        chain: Annotated[str | None, Form()] = None,
        phenotype: Annotated[str | None, Form()] = None,
    ) -> PSFReport:
        reference_path = await _store_upload(reference_file)
        mutant_path = (
            await _store_upload(mutant_file) if mutant_file is not None and mutant_file.filename else None
        )
        request = AnalysisRequest(
            structure=StructureInput(path=str(reference_path)),
            mutant_structure=StructureInput(path=str(mutant_path)) if mutant_path else None,
            ligand=LigandSpec(identifier=ligand),
            mutation=MutationSpec(notation=mutation, chain=chain or None),
            phenotype=PhenotypeSpec(name=phenotype) if phenotype else None,
        )
        return _run(active_runner, request)

    @api.get("/reports/{report_id}", response_model=PSFReport)
    def get_report(report_id: str) -> PSFReport:
        try:
            return active_runner.get_report(report_id)
        except ReportLookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found") from error

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


async def _store_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in SUPPORTED_STRUCTURE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="structure upload must be a .pdb, .cif, or .mmcif file",
        )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
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
