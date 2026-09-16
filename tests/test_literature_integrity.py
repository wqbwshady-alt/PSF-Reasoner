"""Regression tests for literature-evidence integrity.

The 2026-09-10 audit found two classes of bugs in the knowledge layer:

1. ``query_evidence("")`` matched ``"" in "HIV-1_PROTEASE"`` through the
   partial-match fallback, so ANY analysis with unknown protein identity
   received HIV-1 protease literature.
2. Several curated entries cited PMIDs/DOIs unrelated to their claims.

These tests lock in the corrected behaviour.
"""

from __future__ import annotations

from psf_reasoner.knowledge.literature_evidence import (
    get_evidence_summary,
    query_evidence,
)

KNOWN_BAD_PMIDS = {
    "2548654",
    "12730686",
    "15632378",
    "8345919",
    "11258910",
    "11527979",
    "19692680",
    "24722272",
}


def test_empty_family_returns_no_evidence() -> None:
    assert query_evidence("") == []
    assert query_evidence("   ") == []


def test_unknown_family_returns_no_evidence() -> None:
    assert query_evidence("UNKNOWN_PROTEIN") == []
    assert query_evidence("XYZ") == []


def test_hiv_family_returns_only_hiv_evidence() -> None:
    entries = query_evidence("HIV-1_PROTEASE")
    assert entries, "HIV-1 protease should have curated evidence"
    for entry in entries:
        assert entry.pmid not in KNOWN_BAD_PMIDS
        assert entry.pmid in {"15066177", "18597780"}


def test_no_curated_entry_cites_known_bad_pmid() -> None:
    for family in ("HIV-1_PROTEASE", "DHFR", "EGFR"):
        for entry in query_evidence(family, max_grade=5):
            assert entry.pmid not in KNOWN_BAD_PMIDS, f"{entry.evidence_id} cites known-bad PMID {entry.pmid}"


def test_summary_for_empty_family_is_empty() -> None:
    summary = get_evidence_summary("")
    assert summary["total_entries"] == 0
    assert summary["has_direct_evidence"] is False


def test_v82a_literature_has_correct_value() -> None:
    entry = next(
        e for e in query_evidence("HIV-1_PROTEASE", max_grade=5) if e.evidence_id == "HIV_V82A_MK1_001"
    )
    assert entry.pmid == "15066177"
    assert entry.measured_value == 3.3


def test_mechanism_generator_without_family_attaches_no_literature() -> None:
    # A causal graph generated without a protein family must not carry
    # literature evidence from any protein.
    from psf_reasoner.context.structural_context_builder import StructuralContext
    from psf_reasoner.reasoning.mechanism_generator import MechanismGenerator

    ctx = StructuralContext(
        mutation_notation="V82A",
        ligand_identifier="MK1",
        structural_differences={
            "sidechain_volume_change": "decreased",
            "contact_count_delta": -2,
        },
    )
    graph = MechanismGenerator().generate(ctx, protein_family="")

    for node in graph.nodes:
        for link in node.evidence:
            assert link.source != "literature", (
                f"node {node.node_id} carries literature evidence without a protein family"
            )
    for edge in graph.edges:
        for link in edge.evidence:
            assert link.source != "literature", (
                f"edge {edge.edge_id} carries literature evidence without a protein family"
            )
