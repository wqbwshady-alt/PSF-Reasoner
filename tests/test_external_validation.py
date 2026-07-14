import pytest

from psf_reasoner.evaluation.external_validation import (
    InteractionComparison,
    PerTypeAgreement,
    _SYSTEMATIC_DIFFERENCES,
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


class TestSystematicDifferences:
    def test_all_interaction_types_have_notes(self) -> None:
        expected_types = {
            "hydrogen_bond", "hydrophobic_contact", "salt_bridge",
            "pi_interaction", "water_bridge",
        }
        assert expected_types <= set(_SYSTEMATIC_DIFFERENCES)


class TestCompareInteractions:
    def test_graceful_with_nonexistent_file(self, tmp_path) -> None:
        """Should handle missing files gracefully."""
        result = compare_interactions(tmp_path / "nonexistent.pdb", "MK1")
        assert result.ligand_id == "MK1"
        assert result.psf_counts.hydrogen_bonds == 0

    def test_graceful_with_missing_ligand(self, tmp_path) -> None:
        """Should handle structures where the ligand is not found."""
        pdb = tmp_path / "minimal.pdb"
        pdb.write_text(
            "ATOM      1  N   ALA A   1       0.0   0.0   0.0  1.00  0.00           N\n"
            "ATOM      2  CA  ALA A   1       1.5   0.0   0.0  1.00  0.00           C\n"
            "END\n"
        )
        result = compare_interactions(pdb, "MK1")
        assert result.ligand_id == "MK1"
        assert result.psf_counts.hydrogen_bonds == 0

    @plip_skip
    def test_runs_with_plip_when_available(self, tmp_path) -> None:
        """Integration test — requires PLIP to be installed."""
        pdb = tmp_path / "test.pdb"
        pdb.write_text(
            "HEADER    TEST\n"
            "ATOM      1  N   LYS A  82       0.0   0.0   0.0  1.00  0.00           N\n"
            "ATOM      2  CA  LYS A  82       1.5   0.0   0.0  1.00  0.00           C\n"
            "ATOM      3  CB  LYS A  82       2.0   0.5   0.0  1.00  0.00           C\n"
            "ATOM      4  CG  LYS A  82       3.0   1.0   0.0  1.00  0.00           C\n"
            "ATOM      5  CD  LYS A  82       4.0   1.5   0.0  1.00  0.00           C\n"
            "ATOM      6  CE  LYS A  82       5.0   2.0   0.0  1.00  0.00           C\n"
            "ATOM      7  NZ  LYS A  82       6.0   2.5   0.0  1.00  0.00           N\n"
            "HETATM    8  O1  MK1 B901       8.5   2.5   0.0  1.00  0.00           O\n"
            "END\n"
        )
        result = compare_interactions(pdb, "MK1")
        # Should produce a valid comparison object
        assert result.ligand_id == "MK1"
        assert result.psf_counts is not None
        # PLIP may or may not detect interactions on this minimal structure
        assert isinstance(result.total_agreement_rate, float)
