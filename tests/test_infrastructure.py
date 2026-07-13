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
