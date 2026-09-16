"""Regression tests for the calibration feature matrix (2026-09-10 fixes).

Locks in:
- experimental ΔΔG is never written into a feature (label leakage),
- a structure whose ligand does not match the case ligand is recorded as
  a build error instead of silently using another molecule.
"""

from __future__ import annotations

from psf_reasoner.calibration.build_feature_matrix import build_feature_matrix
from psf_reasoner.calibration.feature_schema import FeatureVector
from psf_reasoner.datasets.golden_cases import load_verified_cases


def _make_case(**overrides):
    from psf_reasoner.datasets.schemas import (
        AssayType,
        EffectDirection,
        MutationLigandPair,
    )

    base = dict(
        sample_id="TEST_CASE",
        protein_accession="P03367",
        protein_name="HIV-1 Protease",
        organism="HIV-1",
        mutation_notation="V82A",
        wt_residue="V",
        mutant_residue="A",
        uniprot_position=82,
        pdb_position=82,
        pdb_chain="A",
        ligand_id="MK1",
        ligand_name="MK1",
        ligand_role="inhibitor",
        assay_type=AssayType.KI,
        wt_value=1.0,
        mutant_value=3.3,
        value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif",
        pmid="15066177",
        split_group="P03367",
    )
    base.update(overrides)
    return MutationLigandPair(**base)


def test_no_ddg_label_leakage_into_features() -> None:
    # A case carrying an experimental ΔΔG must NOT have that value appear
    # in f_volume_delta (or any feature of the same name order).
    case = _make_case(delta_delta_g=2.1)
    matrix = build_feature_matrix([case])
    assert matrix.samples, "case with 1sdt structure should build features"
    fv: FeatureVector = matrix.samples[0]
    assert fv.f_volume_delta != 2.1, "experimental delta_delta_g leaked into f_volume_delta"


def test_ligand_mismatch_records_build_error() -> None:
    # A DRV case whose WT structure binds MK1 must produce a build error,
    # not a feature vector computed from the wrong ligand.
    case = _make_case(sample_id="TEST_DRV_MISMATCH", ligand_id="DRV", ligand_name="Darunavir")
    matrix = build_feature_matrix([case])
    assert not matrix.samples
    assert matrix.build_errors, "ligand mismatch must be recorded"
    assert "DRV" in matrix.build_errors[0]["error"]


def test_verified_cases_build_without_ligand_mismatch_errors() -> None:
    # Verified structure cases (MK1 pairs) must build cleanly.
    verified = load_verified_cases()
    cases = [c for c in verified if c.wt_pdb and c.mutant_pdb]
    assert cases, "expected at least one verified structure pair"
    matrix = build_feature_matrix(cases)
    mismatch_errors = [e for e in matrix.build_errors if "not found" in e["error"]]
    assert not mismatch_errors, mismatch_errors
    assert len(matrix.samples) == len(cases)
