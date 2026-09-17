"""Competing Causal Mechanism Graph (V3 P3).

Data structures for representing causal reasoning chains as a directed
acyclic graph where nodes are causal states and edges are evidence-backed
transitions.  Supports multiple competing hypotheses with explicit
supporting, conflicting, and missing evidence per edge.

Standard causal hierarchy:
  Mutation property change
    → Local geometry change
    → Interaction change
    → Pocket / conformational change
    → Binding or catalytic consequence
    → Phenotype
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from psf_reasoner.knowledge.evidence_ranker import EvidenceGrade


class CausalLevel(StrEnum):
    """Standard causal hierarchy levels in the mechanism graph."""

    MUTATION_PROPERTY = "mutation_property"
    LOCAL_GEOMETRY = "local_geometry"
    INTERACTION = "interaction"
    POCKET_CONFORMATION = "pocket_conformation"
    BINDING_CONSEQUENCE = "binding_consequence"
    PHENOTYPE = "phenotype"


class EvidencePolarity(StrEnum):
    SUPPORTING = "supporting"
    CONFLICTING = "conflicting"
    NEUTRAL = "neutral"


@dataclass
class EvidenceLink:
    """One piece of evidence attached to a causal edge or node."""

    evidence_id: str
    polarity: EvidencePolarity
    source: str = ""  # "physical_computation" | "literature" | "structural_context"
    description: str = ""
    grade: EvidenceGrade = EvidenceGrade.GRADE_4_WEAK


@dataclass
class CausalNode:
    """One node in the causal mechanism graph."""

    node_id: str
    level: CausalLevel
    description: str
    mechanism_label: str = ""  # e.g. "steric_repacking", "hbond_gain", "aromatic_stack"
    evidence: list[EvidenceLink] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass
class CausalEdge:
    """A directed edge connecting two causal nodes."""

    edge_id: str
    from_node: str
    to_node: str
    description: str
    evidence: list[EvidenceLink] = field(default_factory=list)
    confidence: str = "moderate"  # qualitative


@dataclass
class MechanismPath:
    """One complete causal path through the graph (a competing mechanism).

    A path goes from mutation_property → phenotype, with each transition
    backed by evidence.
    """

    path_id: str
    label: str  # human-readable, e.g. "Steric repacking → reduced affinity"
    nodes: tuple[str, ...]  # ordered node IDs
    edges: tuple[str, ...]  # ordered edge IDs
    supporting_evidence_count: int = 0
    conflicting_evidence_count: int = 0
    missing_evidence: list[str] = field(default_factory=list)
    causal_assumptions: list[str] = field(default_factory=list)
    rank: int = 0


@dataclass
class CausalMechanismGraph:
    """Complete causal mechanism graph for one mutation analysis.

    Contains all nodes, edges, and competing paths.  The reasoning
    engine produces this graph, and the LLM reasoner uses it to
    generate narrative explanations.
    """

    mutation: str = ""
    protein: str = ""
    ligand: str = ""
    nodes: list[CausalNode] = field(default_factory=list)
    edges: list[CausalEdge] = field(default_factory=list)
    paths: list[MechanismPath] = field(default_factory=list)

    # Summary
    dominant_mechanism: str = ""
    alternative_mechanisms: list[str] = field(default_factory=list)
    key_uncertainties: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a dict suitable for JSON and LLM consumption."""
        return {
            "mutation": self.mutation,
            "protein": self.protein,
            "ligand": self.ligand,
            "nodes": [
                {
                    "id": n.node_id,
                    "level": n.level.value,
                    "description": n.description,
                    "mechanism_label": n.mechanism_label,
                    "evidence_count": len(n.evidence),
                    "supporting": sum(1 for e in n.evidence if e.polarity == EvidencePolarity.SUPPORTING),
                    "conflicting": sum(1 for e in n.evidence if e.polarity == EvidencePolarity.CONFLICTING),
                    "assumptions": n.assumptions,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.edge_id,
                    "from": e.from_node,
                    "to": e.to_node,
                    "description": e.description,
                    "confidence": e.confidence,
                    "evidence_count": len(e.evidence),
                }
                for e in self.edges
            ],
            "paths": [
                {
                    "id": p.path_id,
                    "label": p.label,
                    "rank": p.rank,
                    "supporting": p.supporting_evidence_count,
                    "conflicting": p.conflicting_evidence_count,
                    "missing": p.missing_evidence,
                    "assumptions": p.causal_assumptions,
                }
                for p in sorted(self.paths, key=lambda p: p.rank)
            ],
            "dominant_mechanism": self.dominant_mechanism,
            "alternative_mechanisms": self.alternative_mechanisms,
            "key_uncertainties": self.key_uncertainties,
        }
