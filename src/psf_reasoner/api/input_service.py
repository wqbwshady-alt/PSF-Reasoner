"""Structure-input resolution for the web API.

The web API must not read arbitrary filesystem paths from requests.
Inputs are resolved through the upload store (``upload_id``) or the
bundled example fixtures; the CLI is the entry point for arbitrary
user-provided local files.
"""

from pathlib import Path

from fastapi import HTTPException, status

from psf_reasoner.infrastructure.uploads import resolve_upload
from psf_reasoner.schemas.inputs import AnalysisRequest, StructureInput

EXAMPLES_DIR = Path(__file__).parents[3] / "examples" / "data"


def resolve_structure_input(si: StructureInput, upload_dir: Path) -> StructureInput:
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


def resolve_request(
    request: AnalysisRequest,
    upload_dir: Path,
) -> AnalysisRequest:
    """Resolve all ``StructureInput`` fields in *request* through the upload store."""
    return AnalysisRequest(
        structure=resolve_structure_input(request.structure, upload_dir),
        mutant_structure=resolve_structure_input(request.mutant_structure, upload_dir)
        if request.mutant_structure
        else None,
        ligand=request.ligand,
        mutation=request.mutation,
        phenotype=request.phenotype,
        study_context=request.study_context,
    )
