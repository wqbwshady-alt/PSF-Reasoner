"""Upload lifecycle — capping, pruning, and resolving uploaded structure files."""

from __future__ import annotations

import time
from pathlib import Path

_DEFAULT_UPLOAD_DIR = Path(".psf_uploads")
_DEFAULT_MAX_AGE_SECONDS = 86_400  # 24 hours
_DEFAULT_MAX_COUNT = 100
MAX_STRUCTURE_MODELS = 100
MAX_STRUCTURE_ATOMS = 2_000_000


class InvalidStructureError(ValueError):
    """The uploaded file is not a usable protein structure."""


def validate_structure_file(path: Path | str) -> None:
    """Parse *path* with gemmi and reject unusable structures.

    Raises ``InvalidStructureError`` for files gemmi cannot parse, files
    with no models, zero atoms, or implausible model/atom counts.
    Error messages never contain filesystem paths or file contents.
    """
    import gemmi

    try:
        structure = gemmi.read_structure(str(path))
    except Exception as exc:
        raise InvalidStructureError(
            f"structure file cannot be parsed: {type(exc).__name__}"
        ) from exc

    model_count = len(structure)
    if model_count < 1:
        raise InvalidStructureError("structure contains no models")
    if model_count > MAX_STRUCTURE_MODELS:
        raise InvalidStructureError(
            f"structure has {model_count} models (limit {MAX_STRUCTURE_MODELS})"
        )
    atom_count = sum(
        1
        for model in structure
        for chain in model
        for residue in chain
        for _ in residue
    )
    if atom_count == 0:
        raise InvalidStructureError("structure contains no atoms")
    if atom_count > MAX_STRUCTURE_ATOMS:
        raise InvalidStructureError(
            f"structure has {atom_count} atoms (limit {MAX_STRUCTURE_ATOMS})"
        )


def resolve_upload(
    upload_id: str,
    upload_dir: Path | str = _DEFAULT_UPLOAD_DIR,
) -> Path:
    """Look up an uploaded structure file by its ID.

    *upload_id* must be a plain filename (no path separators) that exists
    inside *upload_dir*.  Returns the resolved ``Path``.

    Raises ``FileNotFoundError`` if the file does not exist.
    Raises ``ValueError`` if *upload_id* contains path separators.
    """
    if "/" in upload_id or "\\" in upload_id:
        raise ValueError(f"upload_id must not contain path separators: {upload_id!r}")
    directory = Path(upload_dir)
    target = (directory / upload_id).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"upload not found: {upload_id}")
    if not str(target).startswith(str(directory.resolve())):
        raise ValueError(f"upload_id resolves outside upload directory: {upload_id!r}")
    return target


def prune_old_uploads(
    upload_dir: Path | str = _DEFAULT_UPLOAD_DIR,
    max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS,
) -> int:
    """Remove uploaded structure files older than *max_age_seconds*.

    Returns the number of files removed.
    """
    directory = Path(upload_dir)
    if not directory.is_dir():
        return 0

    now = time.time()
    removed = 0
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".pdb", ".cif", ".mmcif"}:
            continue
        try:
            age = now - path.stat().st_mtime
            if age > max_age_seconds:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def cap_upload_count(
    upload_dir: Path | str = _DEFAULT_UPLOAD_DIR,
    max_count: int = _DEFAULT_MAX_COUNT,
) -> int:
    """Keep at most *max_count* upload files, removing the oldest first.

    Returns the number of files removed.
    """
    directory = Path(upload_dir)
    if not directory.is_dir():
        return 0

    structure_files = sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".pdb", ".cif", ".mmcif"}
        ),
        key=lambda p: p.stat().st_mtime,
    )
    excess = len(structure_files) - max_count
    if excess <= 0:
        return 0

    removed = 0
    for path in structure_files[:excess]:
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def maintain_uploads(
    upload_dir: Path | str = _DEFAULT_UPLOAD_DIR,
    max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS,
    max_count: int = _DEFAULT_MAX_COUNT,
) -> dict:
    """Run both age-based and count-based cleanup.  Returns counts."""
    age_removed = prune_old_uploads(upload_dir, max_age_seconds)
    count_removed = cap_upload_count(upload_dir, max_count)
    return {"age_removed": age_removed, "count_removed": count_removed}
