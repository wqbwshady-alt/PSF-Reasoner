import pytest

from psf_reasoner.application.ports import ReportLookupError
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.schemas.inputs import AnalysisRequest


def test_runner_persists_completed_report(bidirectional_request: AnalysisRequest) -> None:
    runner = create_default_runner()

    report = runner.run(bidirectional_request)

    assert runner.get_report(report.report_id) == report


def test_missing_report_raises_application_error() -> None:
    runner = create_default_runner()

    with pytest.raises(ReportLookupError):
        runner.get_report("report-000000000000")


class TestSqliteReportRepository:
    """The SQLite repository must survive re-creation and prune old reports."""

    def test_survives_recreation(self, bidirectional_request: AnalysisRequest, tmp_path) -> None:
        from psf_reasoner.infrastructure.sqlite_repository import SqliteReportRepository

        db = tmp_path / "reports.db"
        from psf_reasoner.application.runner import AnalysisRunner
        from psf_reasoner.infrastructure.execution import InlineExecutionBackend

        repo = SqliteReportRepository(db)
        service = create_default_runner()._service
        runner = AnalysisRunner(
            service=service,
            execution=InlineExecutionBackend(),
            reports=repo,
        )
        report = runner.run(bidirectional_request)

        restored = SqliteReportRepository(db)
        assert restored.get(report.report_id) == report
        assert report.report_id in restored.list_ids()
        assert restored.count() >= 1

    def test_delete_and_missing(self, bidirectional_request: AnalysisRequest, tmp_path) -> None:
        from psf_reasoner.infrastructure.sqlite_repository import SqliteReportRepository

        db = tmp_path / "reports.db"
        from psf_reasoner.application.runner import AnalysisRunner
        from psf_reasoner.infrastructure.execution import InlineExecutionBackend

        runner = AnalysisRunner(
            service=create_default_runner()._service,
            execution=InlineExecutionBackend(),
            reports=SqliteReportRepository(db),
        )
        report = runner.run(bidirectional_request)

        repo = SqliteReportRepository(db)
        assert repo.delete(report.report_id) is True
        assert repo.delete(report.report_id) is False
        with pytest.raises(Exception):
            repo.get(report.report_id)

    def test_prune_old(self, bidirectional_request: AnalysisRequest, tmp_path) -> None:
        import sqlite3
        import time

        from psf_reasoner.infrastructure.sqlite_repository import SqliteReportRepository

        db = tmp_path / "reports.db"
        from psf_reasoner.application.runner import AnalysisRunner
        from psf_reasoner.infrastructure.execution import InlineExecutionBackend

        runner = AnalysisRunner(
            service=create_default_runner()._service,
            execution=InlineExecutionBackend(),
            reports=SqliteReportRepository(db),
        )
        report = runner.run(bidirectional_request)

        cutoff = time.time() - 48 * 3600
        aged = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(cutoff))
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "UPDATE reports SET generated_at = ? WHERE report_id = ?",
                (aged, report.report_id),
            )
        repo = SqliteReportRepository(db)
        assert repo.prune_old(max_age_seconds=3600) == 1
        assert repo.count() == 0

    def test_lazy_init_has_no_side_effects(self, tmp_path) -> None:
        from psf_reasoner.infrastructure.sqlite_repository import SqliteReportRepository

        db = tmp_path / "nested" / "reports.db"
        repo = SqliteReportRepository(db)
        assert not db.parent.exists(), "construction must not create the database"
        repo.count()  # first use initialises the schema
        assert db.parent.exists()
