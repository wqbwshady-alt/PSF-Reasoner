"""Build feature matrix from golden cases (V3 Pilot Calibrator).

Runs every golden case through Physical Evidence + Structural Context
to produce a fixed-version feature matrix for model training.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from psf_reasoner.calibration.feature_schema import FeatureVector, extract_features
from psf_reasoner.context.structural_context_builder import StructuralContextBuilder
from psf_reasoner.datasets.golden_cases import load_verified_cases
from psf_reasoner.datasets.schemas import EffectDirection, MutationLigandPair
from psf_reasoner.knowledge.literature_evidence import get_evidence_summary
from psf_reasoner.schemas.inputs import StructureInput

# Project root for resolving relative paths in golden cases
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class FeatureMatrix:
    """Fixed-version feature matrix for pilot calibration."""

    version: str = "pilot_v1"
    samples: list[FeatureVector] = None
    sample_ids: list[str] = None
    labels: list[float] = None
    label_directions: list[str] = None
    split_groups: list[str] = None
    n_features: int = 0
    n_samples: int = 0
    build_errors: list[dict] = None

    def __post_init__(self):
        self.samples = self.samples or []
        self.sample_ids = self.sample_ids or []
        self.labels = self.labels or []
        self.label_directions = self.label_directions or []
        self.split_groups = self.split_groups or []
        self.build_errors = self.build_errors or []


def build_feature_matrix(
    cases: list[MutationLigandPair] | None = None,
) -> FeatureMatrix:
    """Build the pilot feature matrix from golden cases.

    For each case with a structure pair, runs StructuralContext + feature extraction.
    For cases without structures, creates a feature vector with only known properties.
    """
    if cases is None:
        cases = load_verified_cases()

    matrix = FeatureMatrix()
    ctx_builder = StructuralContextBuilder()

    for case in cases:
        try:
            fv = _build_one(case, ctx_builder)
            matrix.samples.append(fv)
            matrix.sample_ids.append(fv.sample_id)

            # Encode label: affinity_decrease=1, neutral=0.5, affinity_increase=0
            direction = case.effect_direction
            if direction == EffectDirection.AFFINITY_DECREASE:
                label = 1.0
            elif direction == EffectDirection.AFFINITY_INCREASE:
                label = 0.0
            else:
                label = 0.5
            matrix.labels.append(label)
            matrix.label_directions.append(direction.value)
            matrix.split_groups.append(fv.split_group)

        except Exception as e:
            matrix.build_errors.append(
                {
                    "sample_id": case.sample_id,
                    "error": str(e),
                }
            )

    matrix.n_samples = len(matrix.samples)
    matrix.n_features = 23  # per FeatureVector.feature_names()
    return matrix


def _build_one(case: MutationLigandPair, ctx_builder: StructuralContextBuilder) -> FeatureVector:
    """Build feature vector for one golden case."""
    # Get literature summary
    lit_summary = {}
    protein_hint = _protein_family_hint(case.protein_accession)
    if protein_hint:
        lit_summary = get_evidence_summary(protein_hint, case.mutation_notation)

    # If structure pair is available, run full StructuralContext
    ctx_diff = {}
    ctx_ms = {}
    ctx_ligand = {}
    n4a = 0
    catalytic_4a = 0

    # Try to run StructuralContext if we have at least a WT structure
    if case.wt_pdb:
        try:
            fmt = "mmcif" if case.wt_pdb.endswith(".cif") else "pdb"
            wt_path = str(_PROJECT_ROOT / "examples" / "data" / case.wt_pdb)
            if not os.path.exists(wt_path):
                raise FileNotFoundError(wt_path)

            from psf_reasoner.context.ligand_fragmenter import decompose_ligand
            from psf_reasoner.context.residue_role_annotator import classify_residue_role
            from psf_reasoner.physical.geometry import atom_distance
            from psf_reasoner.physical.structure import StructureParser

            parser = StructureParser()
            si = StructureInput(path=wt_path, format=fmt, model_index=0)
            wt_struct = parser.parse(si)
            # The structure must contain the case's ligand.  No silent
            # fallback to another molecule: a mismatched ligand (e.g. a DRV
            # case whose WT structure binds MK1) raises, and the outer loop
            # records the case as a build error instead of using it.
            wt_ligand = wt_struct.locate_ligand_by_identifier(case.ligand_id)

            # Find mutation site residue in WT
            for residue in wt_struct.residues:
                if residue.identity.number == (case.pdb_position or case.uniprot_position) and (
                    not case.pdb_chain or residue.identity.chain == case.pdb_chain
                ):
                    # Single-structure features
                    roles = classify_residue_role(residue, wt_ligand, protein_family_hint=protein_hint or "")
                    ctx_ms = {
                        "residue_label": residue.identity.label,
                        "is_catalytic": "catalytic" in [r.value for r in roles],
                        "is_ligand_contact": "ligand_contact" in [r.value for r in roles],
                        "is_pocket_lining": "pocket_lining" in [r.value for r in roles],
                        "roles": [r.value for r in roles],
                    }
                    # Nearest ligand distance
                    res_atoms = [a for a in residue.atoms if a.element not in {"D", "H"}]
                    lig_atoms = [a for a in wt_ligand.atoms if a.element not in {"D", "H"}]
                    if res_atoms and lig_atoms:
                        ctx_ms["nearest_ligand_distance"] = round(
                            min(atom_distance(ra, la) for ra in res_atoms for la in lig_atoms), 3
                        )
                    # 4A neighborhood
                    ctx_ms["neighborhood_4a"] = []
                    for other in wt_struct.residues:
                        if (
                            other.is_hetero
                            or other.is_water
                            or other.identity.label == residue.identity.label
                        ):
                            continue
                        oa = [a for a in other.atoms if a.element not in {"D", "H"}]
                        if oa and res_atoms:
                            md = min(atom_distance(ra, o) for ra in res_atoms for o in oa)
                            if md <= 4.0:
                                ctx_ms["neighborhood_4a"].append(other.identity.label)
                    n4a = len(ctx_ms.get("neighborhood_4a", []))
                    catalytic_4a = 0  # can't easily determine from single structure
                    break

            # Ligand decomposition
            decomp = decompose_ligand(wt_ligand, case.ligand_id)
            ctx_ligand = {
                "heavy_atom_count": decomp.heavy_atom_count,
                "hbond_donors": decomp.hbond_donors,
                "hbond_acceptors": decomp.hbond_acceptors,
                "overall_charge": decomp.overall_charge,
                "fragments": [{"id": f.fragment_id, "description": f.description} for f in decomp.fragments],
            }
        except Exception as e:
            # Structure unavailable, unparseable, or ligand mismatch: surface
            # the reason to the caller instead of silently using empty
            # features.  The outer loop records it as a build error.
            raise ValueError(
                f"{case.sample_id}: structure features unavailable "
                f"({case.wt_pdb}, ligand {case.ligand_id}): {e}"
            ) from e

    fv = extract_features(
        sample_id=case.sample_id,
        split_group=case.split_group,
        ctx_diff=ctx_diff,
        ctx_ms=ctx_ms,
        ctx_ligand=ctx_ligand,
        lit_summary=lit_summary,
        label=1.0 if case.effect_direction == EffectDirection.AFFINITY_DECREASE else 0.0,
        label_type=case.assay_type.value,
    )

    # NOTE: experimental ΔΔG (case.delta_delta_g) must NOT be written into
    # any feature — it is the experimental outcome, and using it as an input
    # feature would leak the label into the training signal.
    fv.f_neighborhood_4a_count = n4a
    fv.f_pocket_catalytic_in_4a = catalytic_4a
    fv.f_is_catalytic = 1 if case.is_catalytic_site else fv.f_is_catalytic
    fv.f_is_ligand_contact = 1 if case.is_ligand_contact else fv.f_is_ligand_contact

    return fv


def _protein_family_hint(accession: str) -> str:
    mapping = {
        "P03367": "HIV-1_PROTEASE",
        "P00374": "DHFR",
        "P00533": "EGFR",
        "P00519": "ABL1",
        "P62593": "BLAC",
    }
    return mapping.get(accession, "")
