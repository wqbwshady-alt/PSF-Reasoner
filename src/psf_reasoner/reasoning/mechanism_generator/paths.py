"""Path extraction and uncertainty reporting for the mechanism generator (V3 P3).

Holds the causal-path DFS, the competing-path ranking, and the
uncertainty extraction extracted 1:1 from ``MechanismGenerator``.
``generator.py`` is the only importer of this module.
"""

from __future__ import annotations

from psf_reasoner.knowledge.evidence_ranker import EvidenceGrade
from psf_reasoner.reasoning.causal_graph import (
    CausalLevel,
    CausalMechanismGraph,
    CausalNode,
    EvidencePolarity,
    MechanismPath,
)


def extract_paths(graph: CausalMechanismGraph) -> list[MechanismPath]:
    """Extract all complete causal paths from the graph."""
    paths: list[MechanismPath] = []

    # Find all complete paths from mutation_property → phenotype
    prop_nodes = [n for n in graph.nodes if n.level == CausalLevel.MUTATION_PROPERTY]
    pheno_nodes = [n for n in graph.nodes if n.level == CausalLevel.PHENOTYPE]

    if not prop_nodes or not pheno_nodes:
        return paths

    # Simple DFS through the graph
    for pn in prop_nodes:
        dfs_paths(graph, pn.node_id, pheno_nodes, [], [], paths)

    # Rank by evidence support
    for i, path in enumerate(paths):
        path.rank = i + 1
    paths.sort(key=lambda p: (-p.supporting_evidence_count, p.conflicting_evidence_count))
    for i, path in enumerate(paths):
        path.rank = i + 1

    return paths


def dfs_paths(
    graph: CausalMechanismGraph,
    current_id: str,
    pheno_nodes: list[CausalNode],
    visited_nodes: list[str],
    visited_edges: list[str],
    paths: list[MechanismPath],
    depth: int = 0,
) -> None:
    """Depth-first traversal to extract causal paths."""
    if depth > 6:
        return  # prevent cycles

    visited_nodes = [*visited_nodes, current_id]

    current_node = next((n for n in graph.nodes if n.node_id == current_id), None)
    if current_node and any(pn.node_id == current_id for pn in pheno_nodes):
        # Reached phenotype — record path
        node_ids = tuple(visited_nodes)
        edge_ids = tuple(visited_edges)
        support = sum(
            1
            for nid in node_ids
            for n in graph.nodes
            if n.node_id == nid
            for e in n.evidence
            if e.polarity == EvidencePolarity.SUPPORTING
        )
        conflict = sum(
            1
            for nid in node_ids
            for n in graph.nodes
            if n.node_id == nid
            for e in n.evidence
            if e.polarity == EvidencePolarity.CONFLICTING
        )

        # Build label from path nodes
        labels = []
        for nid in node_ids:
            n = next((n for n in graph.nodes if n.node_id == nid), None)
            if n:
                labels.append(n.mechanism_label)
        label = " → ".join(labels)

        paths.append(
            MechanismPath(
                path_id=f"path_{len(paths) + 1:03d}",
                label=label,
                nodes=node_ids,
                edges=edge_ids,
                supporting_evidence_count=support,
                conflicting_evidence_count=conflict,
                missing_evidence=[],
                causal_assumptions=[
                    a for nid in node_ids for n in graph.nodes if n.node_id == nid for a in n.assumptions
                ],
            )
        )
        return

    # Follow edges
    for edge in graph.edges:
        if edge.from_node == current_id:
            dfs_paths(
                graph,
                edge.to_node,
                pheno_nodes,
                visited_nodes,
                [*visited_edges, edge.edge_id],
                paths,
                depth + 1,
            )


def extract_uncertainties(diffs: dict, lit_evidence: list) -> list[str]:
    """Identify key uncertainties that limit mechanism discrimination."""
    uncertainties: list[str] = []

    # Missing literature evidence
    if not lit_evidence:
        uncertainties.append(
            "No curated literature evidence available for this protein/mutation/ligand combination"
        )

    has_direct = any(e.compute_grade() <= EvidenceGrade.GRADE_2_STRONG for e in lit_evidence)
    if not has_direct:
        uncertainties.append("No direct or strong literature evidence — relying on structural inference only")

    # Missing dynamic data
    uncertainties.append("No MD or ensemble data — contact occupancies and H-bond lifetimes are unknown")

    # Missing energy calculation
    uncertainties.append("No ΔΔG calculation — binding affinity change is qualitative not quantitative")

    return uncertainties
