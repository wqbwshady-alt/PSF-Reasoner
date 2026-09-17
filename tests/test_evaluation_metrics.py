from psf_reasoner.evaluation.comparison import (
    ComparisonResult,
    ReasonerOutput,
    summarize_comparison,
)
from psf_reasoner.evaluation.metrics import (
    CalibrationAnalysis,
    CalibrationBin,
    compute_calibration_analysis,
    compute_mechanism_ranking,
)
from psf_reasoner.evaluation.protocols import BenchmarkCase


def _case(**kw) -> BenchmarkCase:
    defaults = {
        "case_id": "test",
        "protein_family": "HIV-1_protease",
        "wt_pdb_id": "1SDT",
        "wt_chain": "A",
        "mutant_pdb_id": "1SDU",
        "mutant_source": "experimental",
        "mutation_notation": "V82A",
        "mutation_chain": "A",
        "ligand_identifier": "MK1",
        "assay_type": "Ki",
        "assay_conditions": "test",
        "wt_value": 1.0,
        "wt_unit": "nM",
        "mutant_value": 3.0,
        "mutant_unit": "nM",
        "direction": "increase",
        "phenotype": "drug_resistance",
        "pmid": "12345678",
        "source_table_or_figure": "Table 1",
    }
    defaults.update(kw)
    return BenchmarkCase(**defaults)


class TestMechanismRankingMetrics:
    def test_empty_mechanisms(self) -> None:
        from psf_reasoner.schemas.inputs import (
            AnalysisRequest,
            LigandSpec,
            PhenotypeSpec,
            StructureInput,
        )
        from psf_reasoner.schemas.report import PSFReport

        report = PSFReport(
            report_id="report-123456789012",
            mode="bidirectional",
            request=AnalysisRequest(
                structure=StructureInput(path="/tmp/test.pdb"),
                ligand=LigandSpec(identifier="MK1"),
                mutation=None,
                phenotype=PhenotypeSpec(name="drug_resistance"),
            ),
            confidence=0.5,
        )
        metrics = compute_mechanism_ranking(_case(), report)
        assert metrics.num_mechanisms == 0
        assert not metrics.mechanism_label_match
        assert metrics.mean_reciprocal_rank == 0.0


class TestCalibrationAnalysis:
    def test_empty_results(self) -> None:
        analysis = compute_calibration_analysis([])
        assert analysis.n_cases == 0
        assert analysis.brier_score is None

    def test_empty_results_note(self) -> None:
        analysis = compute_calibration_analysis([])
        assert isinstance(analysis, CalibrationAnalysis)
        assert analysis.n_cases == 0

    def test_bin_centers_cover_0_to_1(self) -> None:
        analysis = CalibrationAnalysis(
            benchmark_id="test",
            n_cases=0,
            n_held_out=0,
            bins=[
                CalibrationBin(0.1, 0, 0, 0),
                CalibrationBin(0.3, 0, 0, 0),
                CalibrationBin(0.5, 0, 0, 0),
                CalibrationBin(0.7, 0, 0, 0),
                CalibrationBin(0.9, 0, 0, 0),
            ],
        )
        assert len(analysis.bins) == 5
        assert analysis.bins[0].bin_center == 0.1
        assert analysis.bins[-1].bin_center == 0.9


class TestReasonerComparison:
    def test_comparison_without_llm(self) -> None:
        result = ComparisonResult(case_id="test")
        assert result.llm is None
        assert not result.mechanism_types_match

    def test_reasoner_output_fields(self) -> None:
        output = ReasonerOutput(
            case_id="test",
            engine="baseline",
            num_mechanisms=3,
            top_mechanism_type="pocket_packing",
            top_mechanism_title="Test mechanism",
        )
        assert output.engine == "baseline"
        assert output.num_mechanisms == 3

    def test_summary_empty_results(self) -> None:
        summary = summarize_comparison([])
        assert summary.n_cases == 0
        assert "No results" in summary.note

    def test_summary_with_llm_unavailable(self) -> None:
        results = [ComparisonResult(case_id="test")]
        summary = summarize_comparison(results)
        assert summary.n_cases == 1
        assert summary.n_llm_available == 0
        assert summary.mechanism_type_agreement_rate == 0.0

    def test_summary_with_matching_types(self) -> None:
        baseline = ReasonerOutput(
            case_id="test",
            engine="baseline",
            top_mechanism_type="pocket_packing",
            confidence=0.7,
        )
        llm = ReasonerOutput(
            case_id="test",
            engine="llm",
            top_mechanism_type="pocket_packing",
            confidence=0.8,
        )
        result = ComparisonResult(
            case_id="test",
            baseline=baseline,
            llm=llm,
            mechanism_types_match=True,
            top_mechanism_jaccard=0.5,
        )
        summary = summarize_comparison([result])
        assert summary.mechanism_type_agreement_rate == 1.0
        assert summary.mean_jaccard == 0.5
