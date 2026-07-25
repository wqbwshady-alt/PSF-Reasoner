"""Dataset Expansion V2 — systematic expansion to 100+ family-balanced cases."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from psf_reasoner.datasets.golden_cases import load_golden_cases
from psf_reasoner.datasets.schemas import EffectDirection


@dataclass
class ExpansionStatus:
    total: int = 0
    target: int = 100
    families: dict[str, dict] = field(default_factory=dict)
    family_label_matrix: dict = field(default_factory=dict)
    ligand_label_matrix: dict = field(default_factory=dict)
    structure_coverage: float = 0.0
    contact_coverage: float = 0.0
    can_evaluate_within_family: int = 0
    total_families: int = 0

    def summary(self) -> str:
        lines = [
            f"Expansion Status: {self.total}/{self.target} cases",
            f"Families with ≥2 label directions: {self.can_evaluate_within_family}/{self.total_families}",
            f"Structure coverage: {self.structure_coverage:.0%}",
            f"Contact coverage: {self.contact_coverage:.0%}",
            f"",
            f"Family × Label Matrix:",
        ]
        for fam in sorted(self.family_label_matrix):
            labels = self.family_label_matrix[fam]
            parts = [f"  {fam}:"]
            for d in ["decrease", "neutral", "increase"]:
                count = labels.get(d, 0)
                status = "✅" if count >= 4 else ("⚠" if count >= 1 else "❌")
                parts.append(f"{status}{d}={count}")
            lines.append(" ".join(parts))
        return "\n".join(lines)


def audit_expansion() -> ExpansionStatus:
    """Audit current expansion state and identify gaps."""
    cases = load_golden_cases()
    status = ExpansionStatus(
        total=len(cases),
        target=150,
    )

    # Family × Label matrix
    matrix: dict[str, dict[str, int]] = {}
    ligand_matrix: dict[str, dict[str, int]] = {}
    struct_count = 0
    contact_count = 0

    for c in cases:
        fam = c.protein_name or c.split_group
        direction = c.effect_direction.value
        if "neutral" in direction:
            direction = "neutral"
        if direction not in ("decrease", "neutral", "increase"):
            direction = "decrease" if "decrease" in direction else "increase"

        if fam not in matrix:
            matrix[fam] = {"decrease": 0, "neutral": 0, "increase": 0}
        matrix[fam][direction] = matrix[fam].get(direction, 0) + 1

        lig = c.ligand_id
        if lig not in ligand_matrix:
            ligand_matrix[lig] = {"decrease": 0, "neutral": 0, "increase": 0}
        ligand_matrix[lig][direction] = ligand_matrix[lig].get(direction, 0) + 1

        if c.wt_pdb:
            struct_count += 1
        if c.has_structure_pair:
            contact_count += 1

    # Build per-family targets
    families = {}
    for fam, dirs in matrix.items():
        can_eval = sum(1 for d in dirs.values() if d > 0)
        deficit_decrease = max(0, 4 - dirs.get("decrease", 0))
        deficit_neutral = max(0, 4 - dirs.get("neutral", 0))
        deficit_increase = max(0, 4 - dirs.get("increase", 0))
        families[fam] = {
            "total": sum(dirs.values()),
            "can_evaluate": can_eval >= 2,
            "deficits": {
                "decrease": deficit_decrease,
                "neutral": deficit_neutral,
                "increase": deficit_increase,
            },
        }

    status.families = families
    status.family_label_matrix = matrix
    status.ligand_label_matrix = dict(ligand_matrix)
    status.structure_coverage = struct_count / max(len(cases), 1)
    status.contact_coverage = contact_count / max(len(cases), 1)
    status.can_evaluate_within_family = sum(1 for f in families.values() if f["can_evaluate"])
    status.total_families = len(families)

    return status


def get_expansion_priority() -> list[dict]:
    """Return priority-ordered list of what to collect next."""
    status = audit_expansion()
    priorities = []

    for fam, info in status.families.items():
        for direction, deficit in info["deficits"].items():
            if deficit > 0:
                priorities.append({
                    "family": fam,
                    "direction_needed": direction,
                    "deficit": deficit,
                    "priority": "HIGH" if deficit >= 3 else "MEDIUM" if deficit >= 1 else "LOW",
                })

    # Sort: high deficit first, then by family
    priorities.sort(key=lambda x: (-x["deficit"], x["family"]))
    return priorities


def generate_expansion_plan() -> str:
    """Generate a markdown expansion plan."""
    status = audit_expansion()
    priorities = get_expansion_priority()

    lines = [
        f"# Dataset Expansion V2 Plan",
        f"",
        f"Current: {status.total} cases | Target: {status.target} cases",
        f"Structure coverage: {status.structure_coverage:.0%} | Contact: {status.contact_coverage:.0%}",
        f"",
        f"## Priority Collection Targets",
        f"",
        f"| Family | Direction Needed | Deficit | Priority |",
        f"|--------|-----------------|---------|----------|",
    ]
    for p in priorities[:15]:
        lines.append(f"| {p['family']} | {p['direction_needed']} | {p['deficit']} | {p['priority']} |")

    lines += [
        f"",
        f"## Family × Label Matrix",
        f"",
    ]
    for fam in sorted(status.family_label_matrix):
        labels = status.family_label_matrix[fam]
        parts = [f"**{fam}**: decrease={labels.get('decrease',0)}, neutral={labels.get('neutral',0)}, increase={labels.get('increase',0)}"]
        lines.append("  " + " · ".join(parts))

    lines += [
        f"",
        f"## Quota Targets (per family)",
        f"Each family: decrease≥4, neutral≥4, increase≥4",
        f"",
    ]
    for fam, info in sorted(status.families.items()):
        d = info["deficits"]
        total_deficit = sum(d.values())
        if total_deficit > 0:
            targets = [f"{dir_}: need {n} more" for dir_, n in d.items() if n > 0]
            lines.append(f"- **{fam}**: {', '.join(targets)}")
        else:
            lines.append(f"- **{fam}**: ✅ quota met")

    lines += [
        f"",
        f"## New Families to Add (recommended)",
        f"",
        f"- Trypsin + Benzamidine (serine protease, well-characterized)",
        f"- SARS-CoV-2 Mpro + Nirmatrelvir (cysteine protease, clinical relevance)",
        f"- Influenza Neuraminidase + Oseltamivir (clinical resistance, many structures)",
        f"- Carbonic Anhydrase + sulfonamide inhibitors (simple, many mutants)",
        f"- Ricin A-chain + small molecule inhibitors",
        f"",
        f"Each new family should contribute 12-20 cases with ≥2 label directions.",
    ]

    return "\n".join(lines)
