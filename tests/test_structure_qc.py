"""Structure-pair QC — RMSD must be invariant to rigid coordinate frames."""

from __future__ import annotations

from pathlib import Path

from psf_reasoner.physical.structure import StructureParser
from psf_reasoner.physical.structure_qc import _ca_rmsd
from psf_reasoner.schemas.inputs import StructureInput

REPO_ROOT = Path(__file__).parent.parent


def _write_pdb(path: Path, atoms: list[tuple[float, float, float]]) -> None:
    lines = ["HEADER    FRAME TEST"]
    for i, (x, y, z) in enumerate(atoms, start=1):
        lines.append(f"ATOM  {i:5d}  CA  GLY A {i:3d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C")
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_ca_rmsd_is_frame_invariant(tmp_path: Path) -> None:
    """A rigidly transformed copy must yield ~0 RMSD after superposition."""
    coords = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]
    # Rotate 90 degrees about z and translate — same shape, new frame.
    transformed = [(-y + 10.0, x - 5.0, z + 3.0) for x, y, z in coords]

    ref_path = tmp_path / "ref.pdb"
    mut_path = tmp_path / "mut.pdb"
    _write_pdb(ref_path, coords)
    _write_pdb(mut_path, transformed)

    parser = StructureParser()
    rmsd = _ca_rmsd(
        parser.parse(StructureInput(path=str(ref_path))),
        parser.parse(StructureInput(path=str(mut_path))),
    )
    assert rmsd is not None
    assert rmsd < 0.01, f"expected frame-invariant RMSD, got {rmsd}"


def test_l90m_pair_grades_comparable() -> None:
    """1SDT/1SDU are the same crystal form in different frames: after
    superposition the pair must grade as comparable, not poorly."""
    parser = StructureParser()
    rmsd = _ca_rmsd(
        parser.parse(StructureInput(path=str(REPO_ROOT / "examples/data/1sdt.cif"))),
        parser.parse(StructureInput(path=str(REPO_ROOT / "examples/data/1sdu.cif"))),
    )
    assert rmsd is not None
    assert rmsd < 1.0, f"1SDT vs 1SDU superimposed Cα RMSD should be < 1 Å, got {rmsd:.2f}"
