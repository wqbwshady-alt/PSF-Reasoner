"""WT/mutant coordinate comparisons for explicitly supplied structure pairs."""

from __future__ import annotations

from dataclasses import dataclass

from psf_reasoner.identifiers import make_id
from psf_reasoner.physical.geometry import nearest_heavy_atom_pair
from psf_reasoner.physical.interactions import InteractionCounts, count_typed_interactions, analyze_typed_interactions
from psf_reasoner.physical.metrics import ligand_shell_bounding_box_volume, residue_sasa
from psf_reasoner.physical.structure import (
    ParsedStructure,
    ResidueRecord,
    StructureAnalysisError,
    StructureParser,
)
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    InteractionDetail,
    Measurement,
    PhysicalEvidence,
)
from psf_reasoner.schemas.inputs import AnalysisRequest

CONTACT_CUTOFF_ANGSTROM = 4.0
SHELL_RADIUS_ANGSTROM = 6.0


@dataclass(frozen=True, slots=True)
class ResidueComparison:
    reference: ResidueRecord
    mutant: ResidueRecord


class ComparativeEvidenceProvider:
    """Compute deltas only when an explicit mutant structure is supplied."""

    def __init__(self, parser: StructureParser | None = None) -> None:
        self._parser = parser or StructureParser()

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if request.mutation is None or request.mutant_structure is None:
            return ()
        reference = self._parser.parse(request.structure)
        mutant = self._parser.parse(request.mutant_structure)
        reference_ligand = reference.locate_ligand(request.ligand)
        mutant_ligand = mutant.locate_ligand(request.ligand)
        pairs = _pair_residues(
            reference.locate_mutation_residues(request.mutation),
            mutant.locate_mutant_residues(request.mutation),
        )
        evidence = [
            item
            for pair in pairs
            for item in self._compare_residue(
                request,
                reference,
                mutant,
                reference_ligand,
                mutant_ligand,
                pair,
            )
        ]
        evidence.append(
            self._compare_ligand_shell(request, reference, mutant, reference_ligand, mutant_ligand)
        )
        return tuple(evidence)

    def _compare_residue(
        self,
        request: AnalysisRequest,
        reference_structure: ParsedStructure,
        mutant_structure: ParsedStructure,
        reference_ligand: ResidueRecord,
        mutant_ligand: ResidueRecord,
        pair: ResidueComparison,
    ) -> tuple[PhysicalEvidence, ...]:
        reference_distance = nearest_heavy_atom_pair(pair.reference, reference_ligand)
        mutant_distance = nearest_heavy_atom_pair(pair.mutant, mutant_ligand)
        if reference_distance is None or mutant_distance is None:
            raise StructureAnalysisError(
                f"cannot compare {pair.reference.identity.label}: a residue or ligand has no heavy atoms"
            )
        reference_contact = reference_distance.angstrom <= CONTACT_CUTOFF_ANGSTROM
        mutant_contact = mutant_distance.angstrom <= CONTACT_CUTOFF_ANGSTROM
        reference_sasa = residue_sasa(reference_structure, pair.reference)
        mutant_sasa = residue_sasa(mutant_structure, pair.mutant)
        reference_analysis = analyze_typed_interactions(
            pair.reference,
            reference_ligand,
            _waters(reference_structure),
        )
        mutant_analysis = analyze_typed_interactions(
            pair.mutant,
            mutant_ligand,
            _waters(mutant_structure),
        )
        reference_interactions = reference_analysis.counts
        mutant_interactions = mutant_analysis.counts
        return (
            self._delta_evidence(
                request,
                pair,
                EvidenceType.ATOMIC_DISTANCE,
                "nearest_heavy_atom_distance_delta",
                reference_distance.angstrom,
                mutant_distance.angstrom,
                "angstrom",
                "Nearest heavy-atom distance comparison",
                (
                    f"WT {pair.reference.identity.label} to {reference_ligand.identity.label}: "
                    f"{reference_distance.angstrom:.3f} A; mutant {pair.mutant.identity.label} to "
                    f"{mutant_ligand.identity.label}: {mutant_distance.angstrom:.3f} A."
                ),
                0.97,
                "paired nearest heavy-atom distance",
            ),
            self._delta_evidence(
                request,
                pair,
                EvidenceType.RESIDUE_CONTACT,
                "contact_state_delta",
                float(reference_contact),
                float(mutant_contact),
                "binary_contact_state",
                "Residue-ligand contact state comparison",
                (
                    f"WT contact={reference_contact}; mutant contact={mutant_contact}; "
                    f"cutoff={CONTACT_CUTOFF_ANGSTROM:.1f} A."
                ),
                0.94,
                "paired contact-state comparison",
            ),
            self._delta_evidence(
                request,
                pair,
                EvidenceType.SOLVENT_EXPOSURE,
                "residue_sasa_delta",
                reference_sasa,
                mutant_sasa,
                "angstrom_squared",
                "Residue solvent-accessible surface area comparison",
                (
                    f"WT SASA={reference_sasa:.2f} A^2; mutant SASA={mutant_sasa:.2f} A^2; "
                    "Shrake-Rupley approximation with 96 points per atom."
                ),
                0.78,
                "paired Shrake-Rupley residue SASA",
            ),
            *self._interaction_deltas(
                request,
                pair,
                reference_interactions,
                mutant_interactions,
                reference_analysis,
                mutant_analysis,
            ),
        )

    def _interaction_deltas(
        self,
        request: AnalysisRequest,
        pair: ResidueComparison,
        reference: InteractionCounts,
        mutant: InteractionCounts,
        reference_analysis: object = None,
        mutant_analysis: object = None,
    ) -> tuple[PhysicalEvidence, ...]:
        """Build per-interaction-class delta evidence with atom-level provenance."""

        def _details(analysis, interaction_type: str) -> tuple[InteractionDetail, ...]:
            if analysis is None:
                return ()
            return tuple(
                InteractionDetail(
                    interaction_type=item.interaction_type,
                    protein_atom=item.protein_atom,
                    ligand_atom=item.ligand_atom,
                    distance_angstrom=item.distance_angstrom,
                    geometry=item.geometry,
                    confidence=item.confidence,
                    mediator=item.mediator,
                )
                for item in getattr(analysis, "interactions", ())
                if item.interaction_type == interaction_type
            )
        return (
            self._delta_evidence(
                request,
                pair,
                EvidenceType.HYDROGEN_BOND,
                "typed_hydrogen_bond_count_delta",
                float(reference.hydrogen_bonds),
                float(mutant.hydrogen_bonds),
                "typed_atom_pairs",
                "Typed hydrogen-bond geometry comparison",
                (
                    f"WT typed pairs={reference.hydrogen_bonds}; mutant typed pairs="
                    f"{mutant.hydrogen_bonds}; donor-acceptor cutoff=3.5 A."
                ),
                0.70,
                "paired donor-acceptor heavy-atom classification",
                interaction_details=(
                    *_details(reference_analysis, "hydrogen_bond"),
                    *_details(mutant_analysis, "hydrogen_bond"),
                ),
            ),
            self._delta_evidence(
                request,
                pair,
                EvidenceType.HYDROPHOBIC_CONTACT,
                "typed_hydrophobic_contact_count_delta",
                float(reference.hydrophobic_contacts),
                float(mutant.hydrophobic_contacts),
                "typed_atom_pairs",
                "Typed hydrophobic-contact geometry comparison",
                (
                    f"WT typed pairs={reference.hydrophobic_contacts}; mutant typed pairs="
                    f"{mutant.hydrophobic_contacts}; hydrophobic cutoff=4.0 A."
                ),
                0.65,
                "paired atom-typed hydrophobic classification",
                interaction_details=(
                    *_details(reference_analysis, "hydrophobic_contact"),
                    *_details(mutant_analysis, "hydrophobic_contact"),
                ),
            ),
            self._delta_evidence(
                request,
                pair,
                EvidenceType.SALT_BRIDGE,
                "typed_salt_bridge_count_delta",
                float(reference.salt_bridges),
                float(mutant.salt_bridges),
                "typed_atom_pairs",
                "Typed salt-bridge geometry comparison",
                (
                    f"WT typed pairs={reference.salt_bridges}; mutant typed pairs="
                    f"{mutant.salt_bridges}; charged-atom cutoff=4.0 A."
                ),
                0.70,
                "paired explicit-charge salt-bridge classification",
                interaction_details=(
                    *_details(reference_analysis, "salt_bridge"),
                    *_details(mutant_analysis, "salt_bridge"),
                ),
            ),
            self._delta_evidence(
                request,
                pair,
                EvidenceType.PI_INTERACTION,
                "typed_pi_interaction_count_delta",
                float(reference.pi_interactions),
                float(mutant.pi_interactions),
                "ring_centroid_pairs",
                "Typed pi-interaction geometry comparison",
                (
                    f"WT ring pairs={reference.pi_interactions}; mutant ring pairs="
                    f"{mutant.pi_interactions}; centroid cutoff=5.5 A."
                ),
                0.40,
                "paired aromatic-ring centroid classification",
                interaction_details=(
                    *_details(reference_analysis, "pi_interaction"),
                    *_details(mutant_analysis, "pi_interaction"),
                ),
            ),
            self._delta_evidence(
                request,
                pair,
                EvidenceType.WATER_BRIDGE,
                "water_bridge_count_delta",
                float(reference.water_bridges),
                float(mutant.water_bridges),
                "bridging_waters",
                "Water-bridge geometry comparison",
                (
                    f"WT bridges={reference.water_bridges}; mutant bridges={mutant.water_bridges}; "
                    "water-to-typed-donor-or-acceptor cutoff=3.5 A."
                ),
                0.50,
                "paired explicit-water bridge classification",
                interaction_details=(
                    *_details(reference_analysis, "water_bridge"),
                    *_details(mutant_analysis, "water_bridge"),
                ),
            ),
        )

    def _compare_ligand_shell(
        self,
        request: AnalysisRequest,
        reference: ParsedStructure,
        mutant: ParsedStructure,
        reference_ligand: ResidueRecord,
        mutant_ligand: ResidueRecord,
    ) -> PhysicalEvidence:
        reference_volume, reference_count = ligand_shell_bounding_box_volume(reference, reference_ligand)
        mutant_volume, mutant_count = ligand_shell_bounding_box_volume(mutant, mutant_ligand)
        delta = mutant_volume - reference_volume
        return PhysicalEvidence(
            id=make_id(
                "evidence",
                "paired_ligand_shell_geometry",
                request.mutation.notation if request.mutation else "none",
                request.ligand.identifier,
            ),
            title="Ligand-proximal shell geometry comparison",
            description=(
                f"WT shell volume proxy={reference_volume:.2f} A^3 ({reference_count} protein atoms); "
                f"mutant={mutant_volume:.2f} A^3 ({mutant_count} protein atoms); "
                f"shell radius={SHELL_RADIUS_ANGSTROM:.1f} A."
            ),
            evidence_type=EvidenceType.POCKET_GEOMETRY,
            status=EvidenceStatus.COMPUTED,
            entities=(reference_ligand.identity.label, mutant_ligand.identity.label),
            measurement=Measurement(
                name="ligand_shell_bounding_box_volume_delta",
                value=round(delta, 3),
                reference_value=round(reference_volume, 3),
                unit="angstrom_cubed_proxy",
                direction=_direction(delta),
            ),
            confidence=0.60,
            provenance=_paired_provenance(
                request,
                "paired ligand-proximal protein-shell bounding-box geometry",
            ),
            limitations=(
                "This is a ligand-shell geometry proxy, not an absolute pocket-volume calculation.",
                "Differences can reflect crystallographic state, ligand pose, or other mutations.",
            ),
        )

    def _delta_evidence(
        self,
        request: AnalysisRequest,
        pair: ResidueComparison,
        evidence_type: EvidenceType,
        measurement_name: str,
        reference_value: float,
        mutant_value: float,
        unit: str,
        title: str,
        description: str,
        confidence: float,
        method: str,
        interaction_details: tuple = (),
    ) -> PhysicalEvidence:
        delta = mutant_value - reference_value
        return PhysicalEvidence(
            id=make_id(
                "evidence",
                "paired",
                evidence_type,
                measurement_name,
                pair.reference.identity.label,
                pair.mutant.identity.label,
            ),
            title=title,
            description=description,
            evidence_type=evidence_type,
            status=EvidenceStatus.COMPUTED,
            entities=(pair.reference.identity.label, pair.mutant.identity.label),
            measurement=Measurement(
                name=measurement_name,
                value=round(delta, 3),
                reference_value=round(reference_value, 3),
                unit=unit,
                direction=_direction(delta),
            ),
            confidence=confidence,
            provenance=_paired_provenance(request, method),
            limitations=_interaction_limitations(evidence_type),
            interaction_details=interaction_details,
        )


def _pair_residues(
    reference: tuple[ResidueRecord, ...],
    mutant: tuple[ResidueRecord, ...],
) -> tuple[ResidueComparison, ...]:
    mutant_by_site = {_site_key(residue): residue for residue in mutant}
    pairs = tuple(
        ResidueComparison(reference=reference_residue, mutant=mutant_by_site[_site_key(reference_residue)])
        for reference_residue in reference
        if _site_key(reference_residue) in mutant_by_site
    )
    if not pairs:
        raise StructureAnalysisError(
            "no mutation sites could be paired between reference and mutant structures"
        )
    if len(pairs) != len(reference) or len(pairs) != len(mutant):
        raise StructureAnalysisError("reference and mutant structures contain different mutation-site chains")
    return pairs


def _site_key(residue: ResidueRecord) -> tuple[str, int, str | None]:
    identity = residue.identity
    return (identity.chain, identity.number, identity.insertion_code)


def _waters(structure: ParsedStructure) -> tuple[ResidueRecord, ...]:
    return tuple(residue for residue in structure.residues if residue.is_water)


def _direction(value: float, tolerance: float = 0.001) -> Direction:
    if value > tolerance:
        return Direction.INCREASE
    if value < -tolerance:
        return Direction.DECREASE
    return Direction.UNCHANGED


def _paired_provenance(request: AnalysisRequest, method: str) -> tuple[Provenance, ...]:
    assert request.mutant_structure is not None
    return (
        Provenance(
            kind=ProvenanceKind.STRUCTURE,
            source=request.structure.path,
            method=f"reference: gemmi parse + {method}",
            parameters={"model_index": request.structure.model_index},
        ),
        Provenance(
            kind=ProvenanceKind.STRUCTURE,
            source=request.mutant_structure.path,
            method=f"mutant: gemmi parse + {method}",
            parameters={"model_index": request.mutant_structure.model_index},
        ),
    )


def _interaction_limitations(evidence_type: EvidenceType) -> tuple[str, ...]:
    common = ("This comparison requires matched structures and does not establish causality by itself.",)
    if evidence_type is EvidenceType.HYDROGEN_BOND:
        return (
            *common,
            "Hydrogen positions, protonation, and angular geometry are not modelled.",
        )
    if evidence_type is EvidenceType.HYDROPHOBIC_CONTACT:
        return (*common, "Carbon proximity is a hydrophobic-contact proxy, not an energy calculation.")
    if evidence_type is EvidenceType.WATER_BRIDGE:
        return (*common, "Only resolved waters in the supplied models are considered.")
    if evidence_type in {EvidenceType.PI_INTERACTION, EvidenceType.SALT_BRIDGE}:
        return (
            *common,
            "Ligand bond order and aromaticity are unavailable unless provided by a "
            "ligand chemistry adapter.",
        )
    return common
