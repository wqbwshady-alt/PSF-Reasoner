"""Upload lifecycle — capping and pruning uploaded structure files."""

from __future__ import annotations

import time
from pathlib import Path

_DEFAULT_UPLOAD_DIR = Path(".psf_uploads")
_DEFAULT_MAX_AGE_SECONDS = 86_400  # 24 hours
_DEFAULT_MAX_COUNT = 100


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
