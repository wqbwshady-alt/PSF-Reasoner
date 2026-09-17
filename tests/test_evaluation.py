import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from psf_reasoner.evaluation.benchmark_runner import (
    case_to_request,
    load_benchmark,
)
from psf_reasoner.evaluation.protocols import BenchmarkCase, BenchmarkDataset


def _minimal_case(**overrides) -> dict:
    data = {
        "case_id": "hiv1-v82a-mk1",
        "protein_family": "HIV-1_protease",
        "wt_pdb_id": "1SDT",
        "wt_chain": "A",
        "mutant_pdb_id": "1SDV",
        "mutant_source": "experimental",
        "mutation_notation": "V82A",
        "mutation_chain": "A",
        "ligand_identifier": "MK1",
        "assay_type": "IC50",
        "assay_conditions": "pH 4.7, 25°C, 0.1 M NaCl",
        "wt_value": 0.5,
        "wt_unit": "nM",
        "mutant_value": 5.0,
        "mutant_unit": "nM",
        "fold_change": 10.0,
        "direction": "increase",
        "phenotype": "drug_resistance",
        "pmid": "12345678",
        "source_table_or_figure": "Table 2, row 3",
        "mechanism_label": "loss of hydrophobic packing at S1 pocket",
        "mechanism_evidence": "literature",
        "mechanism_source": "PMID:12345678, Figure 4",
        "mechanism_review_status": "single_reviewer",
        "mechanism_confidence": 0.8,
    }
    data.update(overrides)
    return data


class TestBenchmarkCase:
    def test_valid_minimal_case(self) -> None:
        case = BenchmarkCase(**_minimal_case())
        assert case.case_id == "hiv1-v82a-mk1"
        assert case.direction == "increase"
        assert case.mechanism_label == "loss of hydrophobic packing at S1 pocket"

    def test_mechanism_label_can_be_none(self) -> None:
        case = BenchmarkCase(**_minimal_case(mechanism_label=None))
        assert case.mechanism_label is None

    def test_mechanism_evidence_defaults_to_none(self) -> None:
        case = BenchmarkCase(
            **_minimal_case(
                mechanism_label=None,
                mechanism_evidence="none",
                mechanism_source=None,
                mechanism_review_status="unreviewed",
                mechanism_confidence=0.0,
            )
        )
        assert case.mechanism_evidence == "none"
        assert case.mechanism_review_status == "unreviewed"

    def test_excluded_case_should_record_reason(self) -> None:
        case = BenchmarkCase(
            **_minimal_case(
                excluded_from_calibration=True,
                exclusion_reason="background mutation M46I present",
            )
        )
        assert case.excluded_from_calibration is True
        assert case.exclusion_reason is not None

    def test_excluded_without_reason_is_valid_but_noted(self) -> None:
        """Schema allows exclusion without reason — curators should fill it in."""
        case = BenchmarkCase(
            **_minimal_case(
                excluded_from_calibration=True,
                exclusion_reason=None,
            )
        )
        assert case.excluded_from_calibration is True
        assert case.exclusion_reason is None

    def test_mutant_pdb_id_can_be_none(self) -> None:
        case = BenchmarkCase(**_minimal_case(mutant_pdb_id=None, mutant_source="modelled"))
        assert case.mutant_pdb_id is None
        assert case.mutant_source == "modelled"

    def test_json_round_trip(self) -> None:
        case = BenchmarkCase(**_minimal_case())
        serialized = case.model_dump_json()
        deserialized = BenchmarkCase.model_validate_json(serialized)
        assert deserialized == case

    def test_json_round_trip_with_none_mechanism_label(self) -> None:
        case = BenchmarkCase(**_minimal_case(mechanism_label=None))
        serialized = case.model_dump_json()
        deserialized = BenchmarkCase.model_validate_json(serialized)
        assert deserialized.mechanism_label is None

    def test_missing_required_field_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            BenchmarkCase(case_id="missing-fields")

    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            BenchmarkCase(**_minimal_case(extra_field="should not be here"))

    def test_background_mutations_defaults_to_empty(self) -> None:
        case = BenchmarkCase(**_minimal_case())
        assert case.wt_mutation_background == []

    def test_background_mutations_recorded(self) -> None:
        case = BenchmarkCase(
            **_minimal_case(
                wt_mutation_background=["M46I", "I54V"],
                notes="Clinical isolate with multiple resistance mutations",
            )
        )
        assert len(case.wt_mutation_background) == 2

    def test_list_of_cases_can_be_serialized(self) -> None:
        case1 = BenchmarkCase(**_minimal_case())
        case2 = BenchmarkCase(
            **_minimal_case(
                case_id="hiv1-i84v-mk1",
                mutation_notation="I84V",
                mechanism_label=None,
                mechanism_evidence="none",
                mechanism_confidence=0.0,
            )
        )
        dataset = [case1, case2]
        serialized = json.dumps([c.model_dump() for c in dataset])
        loaded = [BenchmarkCase.model_validate(c) for c in json.loads(serialized)]
        assert len(loaded) == 2
        assert loaded[0].case_id == "hiv1-v82a-mk1"
        assert loaded[1].case_id == "hiv1-i84v-mk1"

    def test_fold_change_can_be_none(self) -> None:
        """Fold change may not be reported in the source."""
        case = BenchmarkCase(**_minimal_case(fold_change=None))
        assert case.fold_change is None

    def test_protein_uniprot_is_optional(self) -> None:
        case = BenchmarkCase(**_minimal_case(protein_uniprot=None))
        assert case.protein_uniprot is None

    def test_default_split_is_development(self) -> None:
        case = BenchmarkCase(**_minimal_case())
        assert case.split == "development"


class TestBenchmarkDataset:
    def test_empty_dataset(self) -> None:
        ds = BenchmarkDataset(benchmark_id="test", version="0.1.0")
        assert len(ds.cases) == 0
        assert len(ds.development_set) == 0
        assert len(ds.held_out_set) == 0
        assert len(ds.calibration_ready) == 0

    def test_split_assignment(self) -> None:
        dev = BenchmarkCase(**_minimal_case(case_id="dev", split="development"))
        ho = BenchmarkCase(**_minimal_case(case_id="ho", split="held_out"))
        ds = BenchmarkDataset(benchmark_id="test", version="0.1.0", cases=(dev, ho))
        assert len(ds.development_set) == 1
        assert len(ds.held_out_set) == 1
        assert ds.development_set[0].case_id == "dev"
        assert ds.held_out_set[0].case_id == "ho"

    def test_calibration_ready_filters_excluded(self) -> None:
        ok = BenchmarkCase(**_minimal_case(case_id="ok"))
        excluded = BenchmarkCase(
            **_minimal_case(
                case_id="ex",
                excluded_from_calibration=True,
                exclusion_reason="no mechanism label",
                mechanism_label=None,
                mechanism_evidence="none",
                mechanism_confidence=0.0,
            )
        )
        ds = BenchmarkDataset(benchmark_id="test", version="0.1.0", cases=(ok, excluded))
        assert len(ds.calibration_ready) == 1
        assert ds.calibration_ready[0].case_id == "ok"

    def test_calibration_ready_filters_no_mechanism_label(self) -> None:
        no_label = BenchmarkCase(
            **_minimal_case(
                case_id="nl",
                mechanism_label=None,
                mechanism_evidence="none",
                mechanism_confidence=0.0,
            )
        )
        ds = BenchmarkDataset(benchmark_id="test", version="0.1.0", cases=(no_label,))
        assert len(ds.calibration_ready) == 0

    def test_load_benchmark_from_file(self, tmp_path: Path) -> None:
        path = tmp_path / "benchmark.json"
        case = _minimal_case()
        data = {
            "benchmark_id": "test-benchmark",
            "version": "1.0.0",
            "description": "test",
            "cases": [case],
        }
        path.write_text(json.dumps(data))

        ds = load_benchmark(path)
        assert ds.benchmark_id == "test-benchmark"
        assert len(ds.cases) == 1
        assert ds.cases[0].case_id == "hiv1-v82a-mk1"

    def test_case_to_request_converts_correctly(self) -> None:
        case = BenchmarkCase(**_minimal_case())
        request = case_to_request(case)
        assert request.ligand.identifier == "MK1"
        assert request.mutation.notation == "V82A"
        assert request.phenotype.name == "drug_resistance"

    def test_load_frozen_benchmark(self) -> None:
        """The frozen v1.0.0 benchmark should load successfully."""
        path = Path("benchmarks/hiv1_protease/v1.0.0.json")
        if not path.exists():
            pytest.skip("v1.0.0 benchmark not found")
        ds = load_benchmark(path)
        assert ds.version == "1.0.0"
        assert len(ds.cases) == 2
        assert len(ds.calibration_ready) == 2
