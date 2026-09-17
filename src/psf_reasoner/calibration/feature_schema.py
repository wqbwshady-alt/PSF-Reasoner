"""Feature extraction from Structural Context for calibrated models (V3 P4).

Converts the rich StructuralContext (dict/nested objects) into a flat
numerical feature vector suitable for logistic regression, random forest,
or other calibrated models.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureVector:
    """Flat numerical feature vector extracted from StructuralContext.

    All features are deterministic (no LLM, no randomness) and computed
    from structure coordinates and curated knowledge.
    """

    sample_id: str = ""
    split_group: str = ""

    # -- Mutation property features (6) -----------------------------------
    f_volume_delta: float = 0.0  # side-chain volume change in Å³
    f_polarity_added: int = 0  # 0 or 1
    f_polarity_removed: int = 0  # 0 or 1
    f_charge_delta: int = 0  # net charge change
    f_aromatic_added: int = 0  # 0 or 1
    f_hbond_donor_gained: int = 0  # 0 or 1
    f_hbond_acceptor_gained: int = 0  # 0 or 1

    # -- Geometric features (5) -------------------------------------------
    f_contact_count_delta: int = 0  # residue-ligand contact count change
    f_atoms_lost: int = 0  # number of heavy atoms lost
    f_atoms_gained: int = 0  # number of heavy atoms gained
    f_nearest_ligand_distance: float = 0.0  # Å
    f_neighborhood_4a_count: int = 0  # residues within 4Å of mutation

    # -- Pocket features (4) ----------------------------------------------
    f_is_catalytic: int = 0  # 0 or 1
    f_is_ligand_contact: int = 0  # 0 or 1
    f_is_pocket_lining: int = 0  # 0 or 1
    f_pocket_catalytic_in_4a: int = 0  # number of catalytic residues in 4Å

    # -- Ligand features (3) ----------------------------------------------
    f_ligand_heavy_atoms: int = 0
    f_ligand_hbond_donors: int = 0
    f_ligand_hbond_acceptors: int = 0
    f_ligand_charge: int = 0

    # -- Knowledge features (3) --------------------------------------------
    f_direct_evidence_count: int = 0  # GRADE_1_DIRECT literature entries
    f_strong_evidence_count: int = 0  # GRADE_1 + GRADE_2 entries
    f_any_literature: int = 0  # 0 or 1

    # -- Label -------------------------------------------------------------
    label: float = 0.0
    label_type: str = ""

    def to_array(self) -> list[float]:
        """Return features as a flat list for model training."""
        return [
            self.f_volume_delta,
            self.f_polarity_added,
            self.f_polarity_removed,
            float(self.f_charge_delta),
            self.f_aromatic_added,
            self.f_hbond_donor_gained,
            self.f_hbond_acceptor_gained,
            float(self.f_contact_count_delta),
            float(self.f_atoms_lost),
            float(self.f_atoms_gained),
            self.f_nearest_ligand_distance,
            float(self.f_neighborhood_4a_count),
            self.f_is_catalytic,
            self.f_is_ligand_contact,
            self.f_is_pocket_lining,
            float(self.f_pocket_catalytic_in_4a),
            float(self.f_ligand_heavy_atoms),
            float(self.f_ligand_hbond_donors),
            float(self.f_ligand_hbond_acceptors),
            float(self.f_ligand_charge),
            float(self.f_direct_evidence_count),
            float(self.f_strong_evidence_count),
            float(self.f_any_literature),
        ]

    @staticmethod
    def feature_names() -> list[str]:
        """Return feature names in the same order as to_array()."""
        return [
            "volume_delta",
            "polarity_added",
            "polarity_removed",
            "charge_delta",
            "aromatic_added",
            "hbond_donor_gained",
            "hbond_acceptor_gained",
            "contact_count_delta",
            "atoms_lost",
            "atoms_gained",
            "nearest_ligand_distance",
            "neighborhood_4a_count",
            "is_catalytic",
            "is_ligand_contact",
            "is_pocket_lining",
            "pocket_catalytic_in_4a",
            "ligand_heavy_atoms",
            "ligand_hbond_donors",
            "ligand_hbond_acceptors",
            "ligand_charge",
            "direct_evidence_count",
            "strong_evidence_count",
            "any_literature",
        ]


def extract_features(
    sample_id: str,
    split_group: str,
    ctx_diff: dict,
    ctx_ms: dict | None,
    ctx_ligand: dict | None,
    lit_summary: dict | None,
    label: float = 0.0,
    label_type: str = "",
) -> FeatureVector:
    """Extract a flat FeatureVector from V3 StructuralContext components."""

    diffs = ctx_diff or {}
    ms = ctx_ms or {}
    lig = ctx_ligand or {}
    lit = lit_summary or {}

    return FeatureVector(
        sample_id=sample_id,
        split_group=split_group,
        # Mutation properties
        f_volume_delta=float(diffs.get("volume_delta", 0)),
        f_polarity_added=1 if diffs.get("polarity_change") == "polar_added" else 0,
        f_polarity_removed=1 if diffs.get("polarity_change") == "polar_removed" else 0,
        f_charge_delta=_parse_charge_delta(diffs.get("charge_change", "0")),
        f_aromatic_added=1 if diffs.get("aromaticity_change") == "aromatic_added" else 0,
        f_hbond_donor_gained=1 if diffs.get("hbond_donor_change") == "gained" else 0,
        f_hbond_acceptor_gained=1 if diffs.get("hbond_acceptor_change") == "gained" else 0,
        # Geometry
        f_contact_count_delta=int(diffs.get("contact_count_delta", 0)),
        f_atoms_lost=len(diffs.get("lost_atoms", [])),
        f_atoms_gained=len(diffs.get("gained_atoms", [])),
        f_nearest_ligand_distance=float(ms.get("nearest_ligand_distance", 0) or 0),
        f_neighborhood_4a_count=0,  # filled by caller
        # Pocket roles
        f_is_catalytic=1 if ms.get("is_catalytic") else 0,
        f_is_ligand_contact=1 if ms.get("is_ligand_contact") else 0,
        f_is_pocket_lining=1 if ms.get("is_pocket_lining") else 0,
        f_pocket_catalytic_in_4a=0,  # filled by caller
        # Ligand
        f_ligand_heavy_atoms=int(lig.get("heavy_atom_count", 0)),
        f_ligand_hbond_donors=int(lig.get("hbond_donors", 0)),
        f_ligand_hbond_acceptors=int(lig.get("hbond_acceptors", 0)),
        f_ligand_charge=int(lig.get("overall_charge", 0)),
        # Knowledge
        f_direct_evidence_count=sum(
            1
            for entries in lit.get("by_grade", {}).values()
            for e in entries
            if e.get("applicability") == "exact_match"
        ),
        f_strong_evidence_count=lit.get("total_entries", 0),
        f_any_literature=1 if lit.get("total_entries", 0) > 0 else 0,
        # Label
        label=label,
        label_type=label_type,
    )


def _parse_charge_delta(charge_str: str) -> int:
    try:
        return int(charge_str.replace("+", ""))
    except (ValueError, AttributeError):
        return 0
