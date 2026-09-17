"""Protein identity extraction — family mapping from structure headers."""

from __future__ import annotations

from pathlib import Path

from psf_reasoner.physical.identity import extract_protein_identity

REPO_ROOT = Path(__file__).parent.parent


def test_hiv_pair_maps_to_hiv_protease() -> None:
    identity = extract_protein_identity(REPO_ROOT / "examples/data/1sdt.cif")
    assert identity.family_hint == "HIV-1_PROTEASE"


def test_dhfr_title_typo_maps_to_dhfr() -> None:
    """1U72's deposited title spells 'DIHYDRFOLATE REDUCTASE' (missing O)."""
    identity = extract_protein_identity(REPO_ROOT / "examples/data/1U72.pdb")
    assert identity.family_hint == "DHFR"


def test_unknown_title_never_fabricates_family(tmp_path: Path) -> None:
    path = tmp_path / "mystery.pdb"
    path.write_text(
        "HEADER    MYSTERY PROTEIN OF UNKNOWN FUNCTION\n"
        "ATOM      1  N   VAL A  82       0.000   0.000   0.000  1.00 20.00           N\n"
        "END\n",
        encoding="ascii",
    )
    identity = extract_protein_identity(path)
    assert identity.family_hint == ""
