"""Lightweight local interaction scoring."""

from __future__ import annotations

from psf_reasoner.identifiers import make_id
from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.interactions import analyze_typed_interactions
from psf_reasoner.physical.structure import ParsedStructure, ResidueRecord, StructureParser
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType, Measurement, PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest


class LocalEnergyEvidenceProvider:
    """Score local contacts reproducibly without claiming a binding free energy."""

    def __init__(self, parser: StructureParser | None = None) -> None:
        self._parser = parser or StructureParser()

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if request.mutation is None or request.mutant_structure is None:
            return ()
        reference = self._parser.parse(request.structure)
        mutant = self._parser.parse(request.mutant_structure)
        reference_ligand = reference.locate_ligand(request.ligand)
        mutant_ligand = mutant.locate_ligand(request.ligand)
        reference_sites = reference.locate_mutation_residues(request.mutation)
        mutant_sites = mutant.locate_mutant_residues(request.mutation)
        reference_score = sum(_local_score(reference, site, reference_ligand) for site in reference_sites)
        mutant_score = sum(_local_score(mutant, site, mutant_ligand) for site in mutant_sites)
        delta = mutant_score - reference_score
        return (
            PhysicalEvidence(
                id=make_id("evidence", "local_energy", request.mutation.notation, request.ligand.identifier),
                title="Lightweight local interaction-score comparison",
                description=(
                    f"WT local score={reference_score:.3f}; mutant score={mutant_score:.3f}; "
                    "positive delta indicates a less favorable local interaction score."
                ),
                evidence_type=EvidenceType.ENERGY_COMPONENT,
                status=EvidenceStatus.COMPUTED,
                entities=tuple(site.identity.label for site in (*reference_sites, *mutant_sites)),
                measurement=Measurement(
                    name="local_interaction_score_delta",
                    value=round(delta, 3),
                    reference_value=round(reference_score, 3),
                    unit="local_score_units",
                    direction=_direction(delta),
                ),
                confidence=0.58,
                provenance=_provenance(request),
                limitations=(
                    "This is a reproducible local score, not a binding free energy or affinity predictor.",
                    "Weights are calibrated only against the bundled small HIV protease benchmark.",
                ),
            ),
        )


def _local_score(structure: ParsedStructure, residue: ResidueRecord, ligand: ResidueRecord) -> float:
    interactions = analyze_typed_interactions(
        residue, ligand, tuple(item for item in structure.residues if item.is_water)
    )
    counts = interactions.counts
    score = (
        -1.0 * counts.hydrogen_bonds
        - 0.25 * counts.hydrophobic_contacts
        - 1.2 * counts.salt_bridges
        - 0.6 * counts.pi_interactions
        - 0.35 * counts.water_bridges
    )
    for atom in _heavy_atoms(residue):
        for ligand_atom in _heavy_atoms(ligand):
            distance = atom_distance(atom, ligand_atom)
            if distance < 2.2:
                score += (2.2 - distance) * 2.0
    return score


def _heavy_atoms(residue: ResidueRecord):
    return tuple(atom for atom in residue.atoms if atom.element not in {"D", "H"})


def _direction(value: float, tolerance: float = 0.001) -> Direction:
    if value > tolerance:
        return Direction.INCREASE
    if value < -tolerance:
        return Direction.DECREASE
    return Direction.UNCHANGED


def _provenance(request: AnalysisRequest) -> tuple[Provenance, ...]:
    assert request.mutant_structure is not None
    return (
        Provenance(
            kind=ProvenanceKind.COMPUTATION,
            source="PSF local scoring v1",
            method="weighted typed-interaction score + short-range clash penalty",
            parameters={
                "hbond": -1.0,
                "hydrophobic": -0.25,
                "salt_bridge": -1.2,
                "pi": -0.6,
                "water_bridge": -0.35,
                "clash_cutoff_angstrom": 2.2,
            },
        ),
    )
