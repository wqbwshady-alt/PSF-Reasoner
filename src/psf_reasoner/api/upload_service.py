"""Multipart structure-upload handling for the web API.

Uploads are written into the upload store with a generated name, capped
at ``MAX_UPLOAD_BYTES``, and gemmi-validated before use.  Rejected
uploads never leave files behind and error messages never contain
server paths.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from psf_reasoner.infrastructure.uploads import (
    InvalidStructureError,
    validate_structure_file,
)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SUPPORTED_STRUCTURE_SUFFIXES = frozenset({".cif", ".mmcif", ".pdb"})


async def store_upload(upload: UploadFile, upload_dir: Path) -> Path:
    """Persist an uploaded structure file into *upload_dir*.

    Returns the stored ``Path``.  Raises ``HTTPException`` 422 for
    unsupported extensions or unparseable content and 413 for files
    above the size limit; rejected uploads are removed from disk.
    """
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
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
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
