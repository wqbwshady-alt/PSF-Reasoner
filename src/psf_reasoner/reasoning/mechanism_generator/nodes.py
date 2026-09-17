"""Node builders for the competing mechanism generator (V3 P3).

The node-construction logic of ``MechanismGenerator`` lives here as
module-level functions.  Each function corresponds 1:1 to the private
method it was extracted from and expects the same inputs (minus ``self``)
and returns the same list of nodes.

``generator.py`` is the only importer of this module — nothing here
imports back into ``generator`` (no circular imports).
"""

from __future__ import annotations

from psf_reasoner.context.structural_context_builder import StructuralContext
from psf_reasoner.knowledge.evidence_ranker import EvidenceGrade
from psf_reasoner.reasoning.causal_graph import (
    CausalLevel,
    CausalNode,
    EvidenceLink,
    EvidencePolarity,
)


def build_mutation_property_nodes(diffs: dict, mutation: str, ctx: StructuralContext) -> list[CausalNode]:
    """Create nodes for each chemical property change at the mutation site."""
    nodes: list[CausalNode] = []
    idx = 0

    wt = diffs.get("wild_type", "?")
    mut = diffs.get("mutant", "?")

    # Volume change
    vol = diffs.get("sidechain_volume_change", "")
    if vol and vol != "unchanged":
        idx += 1
        direction = "increased" if vol == "increased" else "decreased"
        nodes.append(
            CausalNode(
                node_id=f"prop_vol_{idx}",
                level=CausalLevel.MUTATION_PROPERTY,
                description=(
                    f"Side-chain volume {direction}: {wt} ({_volume(wt)} Å³) → {mut} ({_volume(mut)} Å³)"
                ),
                mechanism_label="Volume change",
                evidence=[
                    EvidenceLink(
                        evidence_id=f"struct_vol_{idx}",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"Volume delta: {diffs.get('volume_delta', '?')} Å³",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
                assumptions=["Volume change matters only if it alters contacts within the binding pocket"],
            )
        )

    # Polarity
    pol = diffs.get("polarity_change", "")
    if pol and pol != "unchanged":
        idx += 1
        nodes.append(
            CausalNode(
                node_id=f"prop_pol_{idx}",
                level=CausalLevel.MUTATION_PROPERTY,
                description=f"Polarity {pol}: {wt} → {mut}",
                mechanism_label="Polarity change",
                evidence=[
                    EvidenceLink(
                        evidence_id=f"struct_pol_{idx}",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"Polarity: {pol}",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
                assumptions=["Polarity change affects solvation and H-bond energetics locally"],
            )
        )

    # Aromaticity
    arom = diffs.get("aromaticity_change", "")
    if arom and arom != "unchanged":
        idx += 1
        nodes.append(
            CausalNode(
                node_id=f"prop_arom_{idx}",
                level=CausalLevel.MUTATION_PROPERTY,
                description=f"Aromaticity {arom}: {wt} → {mut}",
                mechanism_label="Aromaticity change",
                evidence=[
                    EvidenceLink(
                        evidence_id=f"struct_arom_{idx}",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"Aromaticity: {arom}",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
                assumptions=["Aromatic ring can form π-stacking or CH-π interactions"],
            )
        )

    # H-bond donor
    hbd = diffs.get("hbond_donor_change", "")
    if hbd and hbd != "unchanged":
        idx += 1
        nodes.append(
            CausalNode(
                node_id=f"prop_hbd_{idx}",
                level=CausalLevel.MUTATION_PROPERTY,
                description=f"H-bond donor {hbd}: {wt} → {mut}",
                mechanism_label="H-bond donor gained",
                evidence=[
                    EvidenceLink(
                        evidence_id=f"struct_hbd_{idx}",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"H-bond donor: {hbd}",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
                assumptions=["New H-bond donors can form favorable interactions if geometrically feasible"],
            )
        )

    # H-bond acceptor
    hba = diffs.get("hbond_acceptor_change", "")
    if hba and hba != "unchanged":
        idx += 1
        nodes.append(
            CausalNode(
                node_id=f"prop_hba_{idx}",
                level=CausalLevel.MUTATION_PROPERTY,
                description=f"H-bond acceptor {hba}: {wt} → {mut}",
                mechanism_label="H-bond acceptor gained",
                evidence=[
                    EvidenceLink(
                        evidence_id=f"struct_hba_{idx}",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"H-bond acceptor: {hba}",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
                assumptions=[
                    "New H-bond acceptors can form favorable interactions if geometrically feasible"
                ],
            )
        )

    if not nodes:
        nodes.append(
            CausalNode(
                node_id="prop_unknown",
                level=CausalLevel.MUTATION_PROPERTY,
                description=f"No significant chemical property change detected for {mutation}",
                mechanism_label="No significant change",
            )
        )

    return nodes


def build_geometry_nodes(ctx: StructuralContext, prop_nodes: list[CausalNode]) -> list[CausalNode]:
    """Create nodes for local geometry changes."""
    diffs = ctx.structural_differences or {}
    nodes: list[CausalNode] = []

    # Lost atoms
    lost = diffs.get("lost_atoms", [])
    gained = diffs.get("gained_atoms", [])
    if lost or gained:
        nodes.append(
            CausalNode(
                node_id="geom_atom_change",
                level=CausalLevel.LOCAL_GEOMETRY,
                description=f"Atom-level change: lost={lost}, gained={gained}",
                mechanism_label="Atom composition change",
                evidence=[
                    EvidenceLink(
                        evidence_id="struct_atoms",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"{len(lost)} atoms lost, {len(gained)} gained",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
            )
        )

    # Contact changes
    contact_delta = diffs.get("contact_count_delta", 0)
    if contact_delta != 0:
        direction = "lost" if contact_delta < 0 else "gained"
        nodes.append(
            CausalNode(
                node_id="geom_contact_change",
                level=CausalLevel.LOCAL_GEOMETRY,
                description=f"Residue-ligand contacts {direction}: {abs(contact_delta)} contacts",
                mechanism_label="Contact change",
                evidence=[
                    EvidenceLink(
                        evidence_id="struct_contacts",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"Contact count delta: {contact_delta}",
                        grade=EvidenceGrade.GRADE_1_DIRECT,
                    )
                ],
            )
        )

    # Neighborhood info
    n4 = len(ctx.neighborhood_4a)
    if n4 > 0:
        catalytic = [n["label"] for n in ctx.neighborhood_4a if n.get("is_catalytic")]
        nodes.append(
            CausalNode(
                node_id="geom_neighborhood",
                level=CausalLevel.LOCAL_GEOMETRY,
                description=f"Mutation site has {n4} residues within 4Å"
                + (f", including catalytic: {catalytic}" if catalytic else ""),
                mechanism_label="Neighborhood context",
            )
        )

    return nodes


def build_interaction_nodes(
    diffs: dict, ctx: StructuralContext, geom_nodes: list[CausalNode]
) -> list[CausalNode]:
    """Create nodes for specific interaction type changes."""
    nodes: list[CausalNode] = []
    ms = ctx.mutation_site or {}

    # Steric repacking (if volume changes and contacts change)
    vol = diffs.get("sidechain_volume_change", "")
    contact_delta = diffs.get("contact_count_delta", 0)
    if vol == "increased" and contact_delta != 0:
        nodes.append(
            CausalNode(
                node_id="int_steric_clash",
                level=CausalLevel.INTERACTION,
                description=(
                    "Increased side-chain volume may cause steric clash or repacking near the ligand"
                ),
                mechanism_label="Steric repacking",
                evidence=[
                    EvidenceLink(
                        evidence_id="int_steric_1",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"Volume increased + {abs(contact_delta)} contacts changed",
                        grade=EvidenceGrade.GRADE_2_STRONG,
                    )
                ],
                assumptions=["Volume increase in a confined pocket causes steric clash"],
            )
        )
    elif vol == "decreased" and contact_delta != 0:
        nodes.append(
            CausalNode(
                node_id="int_packing_loss",
                level=CausalLevel.INTERACTION,
                description="Decreased side-chain volume leads to loss of packing contacts",
                mechanism_label="Packing loss",
                evidence=[
                    EvidenceLink(
                        evidence_id="int_pack_1",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"Volume decreased + {abs(contact_delta)} contacts lost",
                        grade=EvidenceGrade.GRADE_2_STRONG,
                    )
                ],
            )
        )

    # New H-bond
    hbd = diffs.get("hbond_donor_change", "")
    hba = diffs.get("hbond_acceptor_change", "")
    if hbd == "gained" or hba == "gained":
        nodes.append(
            CausalNode(
                node_id="int_new_hbond",
                level=CausalLevel.INTERACTION,
                description=(
                    "New H-bond donor/acceptor capability may enable novel interactions with ligand or water"
                ),
                mechanism_label="New H-bond potential",
                evidence=[
                    EvidenceLink(
                        evidence_id="int_hb_1",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description=f"H-bond donor {hbd}, acceptor {hba}",
                        grade=EvidenceGrade.GRADE_3_MODERATE,
                    )
                ],
                assumptions=[
                    "New H-bond capability only matters if geometry allows actual bond formation",
                    "Requires < 3.5 Å donor-acceptor distance and > 100° angle",
                ],
            )
        )

    # New aromatic interaction
    arom = diffs.get("aromaticity_change", "")
    if arom == "aromatic_added":
        nodes.append(
            CausalNode(
                node_id="int_new_aromatic",
                level=CausalLevel.INTERACTION,
                description="New aromatic ring may enable π-stacking or CH-π interactions",
                mechanism_label="New aromatic potential",
                evidence=[
                    EvidenceLink(
                        evidence_id="int_arom_1",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description="Aromaticity added",
                        grade=EvidenceGrade.GRADE_3_MODERATE,
                    )
                ],
                assumptions=["π interactions require appropriate geometry and ring orientation"],
            )
        )

    # If no specific interaction change
    if not nodes:
        nearest = ms.get("nearest_ligand_distance")
        nodes.append(
            CausalNode(
                node_id="int_no_change",
                level=CausalLevel.INTERACTION,
                description=(
                    f"No specific interaction type change detected. Nearest ligand distance: {nearest}Å"
                ),
                mechanism_label="No interaction change",
            )
        )

    return nodes


def build_binding_consequence_nodes(
    diffs: dict,
    int_nodes: list[CausalNode],
    lit_evidence: list,
) -> list[CausalNode]:
    """Create nodes for binding affinity consequences."""
    nodes: list[CausalNode] = []

    # Check if there's mechanistic reason to expect affinity change
    has_steric = any("steric" in n.mechanism_label for n in int_nodes)
    has_packing_loss = any("Packing loss" in n.mechanism_label for n in int_nodes)
    has_new_hbond = any("new_hbond" in n.mechanism_label for n in int_nodes)

    # Literature-backed evidence
    lit_support = [
        EvidenceLink(
            evidence_id=e.evidence_id,
            polarity=EvidencePolarity.SUPPORTING,
            source="literature",
            description=e.structured_claim,
            grade=e.compute_grade(),
        )
        for e in lit_evidence
        if e.compute_grade() <= EvidenceGrade.GRADE_3_MODERATE
    ]

    if has_steric:
        nodes.append(
            CausalNode(
                node_id="bind_steric_affinity_loss",
                level=CausalLevel.BINDING_CONSEQUENCE,
                description="Steric clash may reduce ligand binding affinity",
                mechanism_label="Steric affinity reduction",
                evidence=[
                    EvidenceLink(
                        evidence_id="bind_steric_1",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description="Increased volume in binding pocket → potential steric hindrance",
                        grade=EvidenceGrade.GRADE_2_STRONG,
                    ),
                    *lit_support,
                ],
                assumptions=["Steric clash in the binding pocket reduces binding free energy"],
            )
        )

    if has_packing_loss:
        nodes.append(
            CausalNode(
                node_id="bind_packing_affinity_loss",
                level=CausalLevel.BINDING_CONSEQUENCE,
                description="Loss of packing contacts may reduce binding affinity",
                mechanism_label="Packing affinity reduction",
                evidence=[
                    EvidenceLink(
                        evidence_id="bind_pack_1",
                        polarity=EvidencePolarity.SUPPORTING,
                        source="structural_context",
                        description="Lost contacts → fewer favorable vdW interactions",
                        grade=EvidenceGrade.GRADE_2_STRONG,
                    ),
                    *lit_support,
                ],
            )
        )

    if has_new_hbond:
        nodes.append(
            CausalNode(
                node_id="bind_hbond_compensation",
                level=CausalLevel.BINDING_CONSEQUENCE,
                description="New H-bond capability may partially compensate for steric/packing losses",
                mechanism_label="H-bond compensation",
                evidence=[
                    EvidenceLink(
                        evidence_id="bind_hb_1",
                        polarity=EvidencePolarity.NEUTRAL,
                        source="structural_context",
                        description="New H-bond capability — effect depends on geometry",
                        grade=EvidenceGrade.GRADE_3_MODERATE,
                    )
                ],
                assumptions=["New H-bonds require specific geometry to form"],
            )
        )

    if not nodes:
        nodes.append(
            CausalNode(
                node_id="bind_unknown",
                level=CausalLevel.BINDING_CONSEQUENCE,
                description="Insufficient evidence to predict binding affinity change",
                mechanism_label="Binding effect unknown",
                evidence=[
                    EvidenceLink(
                        evidence_id="bind_unk_1",
                        polarity=EvidencePolarity.NEUTRAL,
                        source="structural_context",
                        description="No strong structural signal for binding change",
                        grade=EvidenceGrade.GRADE_4_WEAK,
                    )
                ],
            )
        )

    return nodes


def build_phenotype_nodes(bind_nodes: list[CausalNode]) -> list[CausalNode]:
    """Create nodes for phenotype-level consequences."""
    # For now, phenotype = resistance if binding is reduced
    has_binding_loss = any(
        "affinity" in n.mechanism_label and "reduction" in n.mechanism_label for n in bind_nodes
    )
    if has_binding_loss:
        return [
            CausalNode(
                node_id="pheno_resistance",
                level=CausalLevel.PHENOTYPE,
                description=(
                    "Reduced inhibitor binding may confer drug resistance, "
                    "provided catalytic activity is retained"
                ),
                mechanism_label="Potential resistance",
                assumptions=[
                    "Resistance requires catalytic activity retention (not assessed here)",
                    "In vivo resistance depends on expression, fitness, drug exposure",
                ],
            )
        ]
    return [
        CausalNode(
            node_id="pheno_unknown",
            level=CausalLevel.PHENOTYPE,
            description="Phenotype cannot be predicted from available evidence",
            mechanism_label="Phenotype unknown",
        )
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _volume(residue_name: str) -> int:
    """Approximate side-chain volume in Å³."""
    volumes = {
        "ALA": 89,
        "ARG": 173,
        "ASN": 114,
        "ASP": 111,
        "CYS": 109,
        "GLN": 144,
        "GLU": 138,
        "GLY": 60,
        "HIS": 153,
        "ILE": 167,
        "LEU": 167,
        "LYS": 169,
        "MET": 163,
        "PHE": 190,
        "PRO": 113,
        "SER": 89,
        "THR": 116,
        "TRP": 228,
        "TYR": 194,
        "VAL": 140,
    }
    return volumes.get(residue_name.upper(), 150)
