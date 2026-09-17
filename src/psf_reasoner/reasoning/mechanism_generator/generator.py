"""Competing Mechanism Generator (V3 P3).

Builds causal mechanism graphs from structural context and literature
evidence.  Replaces the legacy heuristic baseline with a structured,
multi-hypothesis reasoning approach.

For each mutation, generates ALL plausible causal paths and ranks them
by evidence support, rather than picking one template.

The node builders live in :mod:`~psf_reasoner.reasoning.mechanism_generator.nodes`
and the path/uncertainty extraction in
:mod:`~psf_reasoner.reasoning.mechanism_generator.paths`; the methods below
delegate to them.
"""

from __future__ import annotations

from psf_reasoner.context.structural_context_builder import StructuralContext
from psf_reasoner.knowledge.evidence_ranker import EvidenceGrade
from psf_reasoner.knowledge.literature_evidence import query_evidence
from psf_reasoner.reasoning.causal_graph import (
    CausalEdge,
    CausalMechanismGraph,
    CausalNode,
    EvidenceLink,
    EvidencePolarity,
    MechanismPath,
)
from psf_reasoner.reasoning.mechanism_generator.nodes import (
    build_binding_consequence_nodes,
    build_geometry_nodes,
    build_interaction_nodes,
    build_mutation_property_nodes,
    build_phenotype_nodes,
)
from psf_reasoner.reasoning.mechanism_generator.paths import (
    dfs_paths,
    extract_paths,
    extract_uncertainties,
)


class MechanismGenerator:
    """Generate competing causal mechanism graphs from structural context.

    Usage::

        gen = MechanismGenerator()
        graph = gen.generate(ctx, protein_family="HIV-1_PROTEASE")
        # graph.to_dict() → structured output for LLM and frontend
    """

    def generate(
        self,
        ctx: StructuralContext,
        protein_family: str = "",
    ) -> CausalMechanismGraph:
        """Generate a complete causal mechanism graph from structural context."""
        mutation = ctx.mutation_notation
        ligand = ctx.ligand_identifier
        diffs = ctx.structural_differences or {}

        graph = CausalMechanismGraph(
            mutation=mutation,
            protein=protein_family or ctx.protein_name,
            ligand=ligand,
        )

        # ---- Retrieve literature evidence ----------------------------------
        lit_evidence = query_evidence(protein_family, mutation, ligand)

        # ---- Step 1: Build mutation property node(s) -----------------------
        prop_nodes = self._build_mutation_property_nodes(diffs, mutation, ctx)
        graph.nodes.extend(prop_nodes)

        # ---- Step 2: Build geometry nodes ----------------------------------
        geom_nodes = self._build_geometry_nodes(ctx, prop_nodes)
        graph.nodes.extend(geom_nodes)
        if prop_nodes and geom_nodes:
            for pn in prop_nodes:
                for gn in geom_nodes:
                    graph.edges.append(
                        CausalEdge(
                            edge_id=f"edge_{pn.node_id}_to_{gn.node_id}",
                            from_node=pn.node_id,
                            to_node=gn.node_id,
                            description=f"{pn.mechanism_label} → {gn.mechanism_label}",
                            confidence="strong" if gn.evidence else "moderate",
                        )
                    )

        # ---- Step 3: Build interaction nodes --------------------------------
        int_nodes = self._build_interaction_nodes(diffs, ctx, geom_nodes)
        graph.nodes.extend(int_nodes)
        for gn in geom_nodes:
            for inode in int_nodes:
                if inode.evidence:
                    graph.edges.append(
                        CausalEdge(
                            edge_id=f"edge_{gn.node_id}_to_{inode.node_id}",
                            from_node=gn.node_id,
                            to_node=inode.node_id,
                            description=f"{gn.mechanism_label} → {inode.mechanism_label}",
                            confidence="strong",
                        )
                    )

        # ---- Step 4: Build binding consequence nodes ------------------------
        bind_nodes = self._build_binding_consequence_nodes(diffs, int_nodes, lit_evidence)
        graph.nodes.extend(bind_nodes)
        for inode in int_nodes:
            for bn in bind_nodes:
                graph.edges.append(
                    CausalEdge(
                        edge_id=f"edge_{inode.node_id}_to_{bn.node_id}",
                        from_node=inode.node_id,
                        to_node=bn.node_id,
                        description=f"{inode.mechanism_label} → {bn.mechanism_label}",
                        confidence="moderate",
                        evidence=[
                            EvidenceLink(
                                evidence_id=e.evidence_id,
                                polarity=EvidencePolarity.SUPPORTING,
                                source="literature",
                                description=e.structured_claim,
                                grade=e.compute_grade(),
                            )
                            for e in lit_evidence
                            if e.compute_grade() <= EvidenceGrade.GRADE_3_MODERATE
                        ],
                    )
                )

        # ---- Step 5: Build phenotype node ----------------------------------
        pheno_nodes = self._build_phenotype_nodes(bind_nodes)
        graph.nodes.extend(pheno_nodes)
        for bn in bind_nodes:
            for pn in pheno_nodes:
                graph.edges.append(
                    CausalEdge(
                        edge_id=f"edge_{bn.node_id}_to_{pn.node_id}",
                        from_node=bn.node_id,
                        to_node=pn.node_id,
                        description=f"{bn.mechanism_label} → {pn.mechanism_label}",
                        confidence="moderate",
                    )
                )

        # ---- Step 6: Extract competing paths --------------------------------
        graph.paths = self._extract_paths(graph)

        # ---- Step 7: Summarize ---------------------------------------------
        if graph.paths:
            graph.dominant_mechanism = graph.paths[0].label
            graph.alternative_mechanisms = [p.label for p in graph.paths[1:4]]
        graph.key_uncertainties = self._extract_uncertainties(diffs, lit_evidence)

        return graph

    # ------------------------------------------------------------------
    # Node builders
    # ------------------------------------------------------------------

    def _build_mutation_property_nodes(
        self, diffs: dict, mutation: str, ctx: StructuralContext
    ) -> list[CausalNode]:
        """Create nodes for each chemical property change at the mutation site."""
        return build_mutation_property_nodes(diffs, mutation, ctx)

    def _build_geometry_nodes(self, ctx: StructuralContext, prop_nodes: list[CausalNode]) -> list[CausalNode]:
        """Create nodes for local geometry changes."""
        return build_geometry_nodes(ctx, prop_nodes)

    def _build_interaction_nodes(
        self, diffs: dict, ctx: StructuralContext, geom_nodes: list[CausalNode]
    ) -> list[CausalNode]:
        """Create nodes for specific interaction type changes."""
        return build_interaction_nodes(diffs, ctx, geom_nodes)

    def _build_binding_consequence_nodes(
        self,
        diffs: dict,
        int_nodes: list[CausalNode],
        lit_evidence: list,
    ) -> list[CausalNode]:
        """Create nodes for binding affinity consequences."""
        return build_binding_consequence_nodes(diffs, int_nodes, lit_evidence)

    def _build_phenotype_nodes(self, bind_nodes: list[CausalNode]) -> list[CausalNode]:
        """Create nodes for phenotype-level consequences."""
        return build_phenotype_nodes(bind_nodes)

    # ------------------------------------------------------------------
    # Path extraction
    # ------------------------------------------------------------------

    def _extract_paths(self, graph: CausalMechanismGraph) -> list[MechanismPath]:
        """Extract all complete causal paths from the graph."""
        return extract_paths(graph)

    def _dfs_paths(
        self,
        graph: CausalMechanismGraph,
        current_id: str,
        pheno_nodes: list[CausalNode],
        visited_nodes: list[str],
        visited_edges: list[str],
        paths: list[MechanismPath],
        depth: int = 0,
    ) -> None:
        """Depth-first traversal to extract causal paths."""
        dfs_paths(graph, current_id, pheno_nodes, visited_nodes, visited_edges, paths, depth)

    # ------------------------------------------------------------------
    # Uncertainty extraction
    # ------------------------------------------------------------------

    def _extract_uncertainties(self, diffs: dict, lit_evidence: list) -> list[str]:
        """Identify key uncertainties that limit mechanism discrimination."""
        return extract_uncertainties(diffs, lit_evidence)
