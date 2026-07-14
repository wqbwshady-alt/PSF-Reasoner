import time
from pathlib import Path

from psf_reasoner.infrastructure.uploads import (
    cap_upload_count,
    maintain_uploads,
    prune_old_uploads,
    resolve_upload,
)


class TestResolveUpload:
    def test_resolves_existing_file(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "abc123.pdb").write_text("ATOM")

        result = resolve_upload("abc123.pdb", upload_dir)

        assert result.is_file()
        assert result.name == "abc123.pdb"

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()

        import pytest
        with pytest.raises(FileNotFoundError):
            resolve_upload("missing.pdb", upload_dir)

    def test_raises_for_path_separator(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()

        import pytest
        with pytest.raises(ValueError, match="path separator"):
            resolve_upload("../etc/passwd", upload_dir)

    def test_raises_for_backslash(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()

        import pytest
        with pytest.raises(ValueError, match="path separator"):
            resolve_upload("..\\windows\\system32", upload_dir)

    def test_raises_for_outside_upload_dir(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        # Create a symlink that escapes
        escape = tmp_path / "escape.pdb"
        escape.write_text("ESCAPE")
        (upload_dir / "link.pdb").symlink_to(escape)

        import pytest
        with pytest.raises(ValueError, match="outside upload"):
            resolve_upload("link.pdb", upload_dir)


class TestPruneOldUploads:
    def test_removes_old_files(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        old = upload_dir / "old.pdb"
        old.write_text("OLD")
        # Set mtime to 2 days ago
        old_mtime = time.time() - 48 * 3600
        old.touch(exist_ok=True)
        # Actually set mtime via os.utime
        import os
        os.utime(old, (old_mtime, old_mtime))

        fresh = upload_dir / "fresh.pdb"
        fresh.write_text("FRESH")

        removed = prune_old_uploads(upload_dir, max_age_seconds=3600)

        assert removed >= 1
        assert not old.exists()
        assert fresh.exists()

    def test_noop_when_no_old_files(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "fresh.pdb").write_text("FRESH")

        removed = prune_old_uploads(upload_dir, max_age_seconds=3600)

        assert removed == 0

    def test_noop_when_directory_missing(self, tmp_path: Path) -> None:
        removed = prune_old_uploads(tmp_path / "nonexistent")
        assert removed == 0


class TestCapUploadCount:
    def test_removes_excess_files(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        for i in range(10):
            (upload_dir / f"file{i:02d}.pdb").write_text(f"FILE{i}")

        removed = cap_upload_count(upload_dir, max_count=5)

        assert removed == 5
        remaining = list(upload_dir.iterdir())
        assert len(remaining) == 5

    def test_noop_when_under_limit(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "file.pdb").write_text("FILE")

        removed = cap_upload_count(upload_dir, max_count=10)

        assert removed == 0


class TestMaintainUploads:
    def test_runs_both_cleanup_strategies(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        for i in range(20):
            (upload_dir / f"file{i:02d}.pdb").write_text(f"FILE{i}")

        result = maintain_uploads(upload_dir, max_count=5)

        assert "age_removed" in result
        assert "count_removed" in result
        remaining = list(upload_dir.iterdir())
        assert len(remaining) <= 5
