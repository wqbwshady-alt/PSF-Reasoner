from pathlib import Path

import pytest

from psf_reasoner.evaluation.external_validation import (
    _SYSTEMATIC_DIFFERENCES,
    InteractionComparison,
    PerTypeAgreement,
    compare_interactions,
)
from psf_reasoner.physical.interactions import InteractionCounts


def _plip_available() -> bool:
    try:
        import plip  # noqa: F401

        return True
    except ImportError:
        return False


plip_skip = pytest.mark.skipif(
    not _plip_available(),
    reason="PLIP not installed (requires Python ≤3.12, OpenBabel)",
)


class TestPerTypeAgreement:
    def test_match_when_counts_equal(self) -> None:
        a = PerTypeAgreement(interaction_type="hydrogen_bond", psf_count=3, plip_count=3, match=True)
        assert a.match is True

    def test_mismatch_when_counts_differ(self) -> None:
        a = PerTypeAgreement(interaction_type="hydrogen_bond", psf_count=3, plip_count=5, match=False)
        assert a.match is False


class TestInteractionComparison:
    def test_total_agreement_rate(self) -> None:
        comp = InteractionComparison(
            pdb_path="/tmp/test.pdb",
            ligand_id="MK1",
            psf_counts=InteractionCounts(2, 10, 0, 1, 3),
            plip_counts={"hydrogen_bond": 2, "hydrophobic_contact": 8},
            by_type=[
                PerTypeAgreement("hydrogen_bond", 2, 2, match=True),
                PerTypeAgreement("hydrophobic_contact", 10, 8, match=False),
            ],
        )
        assert comp.total_agreement_rate == 0.5

    def test_empty_by_type_gives_zero_rate(self) -> None:
        comp = InteractionComparison(
            pdb_path="/tmp/test.pdb",
            ligand_id="MK1",
            psf_counts=InteractionCounts(0, 0, 0, 0, 0),
        )
        assert comp.total_agreement_rate == 0.0

    def test_hydrophobic_residue_overlap_has_separate_metrics(self) -> None:
        comp = InteractionComparison(
            pdb_path="example.pdb",
            ligand_id="MK1",
            psf_counts=InteractionCounts(0, 4, 0, 0, 0),
            psf_hydrophobic_residues=frozenset({"A:VAL82", "A:ILE84"}),
            plip_hydrophobic_residues=frozenset({"A:VAL82"}),
        )
        assert comp.hydrophobic_residue_precision == 0.5
        assert comp.hydrophobic_residue_recall == 1.0


class TestSystematicDifferences:
    def test_all_interaction_types_have_notes(self) -> None:
        expected_types = {
            "hydrogen_bond",
            "hydrophobic_contact",
            "salt_bridge",
            "pi_interaction",
            "water_bridge",
        }
        assert expected_types <= set(_SYSTEMATIC_DIFFERENCES)


class TestCompareInteractions:
    def test_missing_plip_is_not_reported_as_zero_agreement(self, monkeypatch) -> None:
        from psf_reasoner.evaluation import external_validation as module

        def missing_plip(*_args):
            raise ImportError("PLIP unavailable")

        monkeypatch.setattr(module, "_run_plip_with_residues", missing_plip)
        with pytest.raises(ImportError, match="PLIP unavailable"):
            compare_interactions(Path("examples/data/1sdt.cif"), "MK1")

    def test_nonexistent_file_fails_validation(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            compare_interactions(tmp_path / "nonexistent.pdb", "MK1")

    def test_missing_ligand_fails_validation(self, tmp_path) -> None:
        pdb = tmp_path / "minimal.pdb"
        pdb.write_text(
            "ATOM      1  N   ALA A   1       0.0   0.0   0.0  1.00  0.00           N\n"
            "ATOM      2  CA  ALA A   1       1.5   0.0   0.0  1.00  0.00           C\n"
            "END\n"
        )
        with pytest.raises(ValueError, match="PSF did not identify ligand MK1"):
            compare_interactions(pdb, "MK1")

    @plip_skip
    def test_runs_with_plip_on_real_complex(self) -> None:
        """The reference tool must detect the ligand and real interactions."""
        result = compare_interactions(Path("examples/data/1sdt.cif"), "MK1")
        assert result.plip_counts["hydrogen_bond"] > 0
        assert result.plip_counts["hydrophobic_contact"] > 0
        assert "A:VAL82" in result.psf_hydrophobic_residues
        assert "A:VAL82" in result.plip_hydrophobic_residues
        assert result.hydrophobic_residue_recall is not None
