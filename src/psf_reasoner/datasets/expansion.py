"""Dataset inventory audit (replaces the quota-based expansion plan).

Earlier versions of this module framed dataset growth as quota targets
("decrease>=4, neutral>=4, increase>=4 per family").  That framing produced
the fabricated bulk-fill rows documented in docs/EVIDENCE-REVIEW.md and is
deliberately removed.

What remains is an inventory: how many verified / pending / rejected cases
exist per family, so curation effort can be directed at re-verifying
rejected families instead of generating more rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from psf_reasoner.datasets.golden_cases import load_golden_cases


@dataclass
class InventoryStatus:
    total: int = 0
    verified: int = 0
    pending: int = 0
    rejected: int = 0
    families: dict[str, dict] = field(default_factory=dict)
    has_structure_pair: int = 0

    def summary(self) -> str:
        lines = [
            f"Inventory: {self.total} cases "
            f"({self.verified} verified, {self.pending} pending, {self.rejected} rejected)",
            f"Structure pairs: {self.has_structure_pair}",
            "",
            "Per family (verified/pending/rejected):",
        ]
        for fam in sorted(self.families):
            v = self.families[fam]
            lines.append(f"  {fam}: {v['accepted']}/{v['pending']}/{v['rejected']}")
        return "\n".join(lines)


def audit_expansion() -> InventoryStatus:
    """Audit the case inventory by review status."""
    cases = load_golden_cases()
    status = InventoryStatus(total=len(cases))
    for c in cases:
        fam = c.protein_name or c.split_group or "unknown"
        entry = status.families.setdefault(fam, {"accepted": 0, "pending": 0, "rejected": 0})
        if c.review_status.value == "accepted":
            status.verified += 1
            entry["accepted"] += 1
        elif c.review_status.value == "pending":
            status.pending += 1
            entry["pending"] += 1
        else:
            status.rejected += 1
            entry["rejected"] += 1
        if c.wt_pdb and c.mutant_pdb:
            status.has_structure_pair += 1
    return status


def get_expansion_priority() -> list[dict]:
    """Return curation priorities: families with zero verified cases first.

    The priority is RE-VERIFICATION of excluded families (find the real
    literature), never the generation of new rows to fill a matrix.
    """
    status = audit_expansion()
    priorities = []
    for fam, info in status.families.items():
        priorities.append(
            {
                "family": fam,
                "verified": info["accepted"],
                "pending": info["pending"],
                "rejected": info["rejected"],
                "priority": "HIGH" if info["accepted"] == 0 else "LOW",
            }
        )
    priorities.sort(key=lambda x: -x["rejected"])
    return priorities


def generate_expansion_plan() -> str:
    """Generate a curation plan that re-verifies, never fabricates."""
    status = audit_expansion()
    priorities = get_expansion_priority()
    lines = [
        "# Dataset Curation Plan (evidence-first)",
        "",
        f"Current: {status.total} cases | verified {status.verified} | "
        f"pending {status.pending} | rejected {status.rejected}",
        "",
        "## Priority: re-verify rejected families against real literature",
        "",
        "| Family | Verified | Pending | Rejected | Priority |",
        "|--------|----------|---------|----------|----------|",
    ]
    for p in priorities[:15]:
        lines.append(
            f"| {p['family']} | {p['verified']} | {p['pending']} | {p['rejected']} | {p['priority']} |"
        )
    lines += [
        "",
        "## Rules",
        "",
        "- Every numeric value must be traceable to a table/figure in the cited paper.",
        "- Every structure must actually contain the assay ligand.",
        "- No quota targets.  A family with one verified case is better than a",
        "  family with twenty fabricated ones.",
        "",
        "See docs/EVIDENCE-REVIEW.md for the full audit and the human-review",
        "checklist (paywalled full-text items).",
    ]
    return "\n".join(lines)
