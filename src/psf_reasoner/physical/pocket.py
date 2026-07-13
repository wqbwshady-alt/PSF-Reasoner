"""Ligand-pocket definition and residue-network evidence."""

from __future__ import annotations

from psf_reasoner.identifiers import make_id
from psf_reasoner.physical.geometry import atom_distance
from psf_reasoner.physical.structure import (
    ParsedStructure,
    ResidueRecord,
    StructureAnalysisError,
    StructureParser,
)
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType, Measurement, PhysicalEvidence
from psf_reasoner.schemas.inputs import AnalysisRequest

POCKET_RADIUS_ANGSTROM = 6.0
RESIDUE_EDGE_CUTOFF_ANGSTROM = 4.5


class PocketNetworkEvidenceProvider:
    """Compute an operational ligand pocket and its residue-contact network."""

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
        if not reference_sites or not mutant_sites:
            raise StructureAnalysisError("mutation site could not be located in paired structures")

        reference_pocket = _pocket_residues(reference, reference_ligand)
        mutant_pocket = _pocket_residues(mutant, mutant_ligand)
        reference_edges = _contact_edges(reference_pocket)
        mutant_edges = _contact_edges(mutant_pocket)
        ref_site_degrees = sum(_site_degree(site, reference_edges) for site in reference_sites)
        mut_site_degrees = sum(_site_degree(site, mutant_edges) for site in mutant_sites)
        pocket_delta = len(mutant_pocket) - len(reference_pocket)
        edge_delta = len(mutant_edges) - len(reference_edges)
        degree_delta = mut_site_degrees - ref_site_degrees
        return (
            PhysicalEvidence(
                id=make_id(
                    "evidence",
                    "pocket_definition",
                    request.mutation.notation,
                    request.ligand.identifier,
                ),
                title="Operational ligand-pocket residue-count comparison",
                description=(
                    f"WT pocket residues={len(reference_pocket)}; mutant pocket residues="
                    f"{len(mutant_pocket)}; residues are included when any heavy atom is within "
                    f"{POCKET_RADIUS_ANGSTROM:.1f} A of ligand."
                ),
                evidence_type=EvidenceType.POCKET_GEOMETRY,
                status=EvidenceStatus.COMPUTED,
                entities=(reference_ligand.identity.label, mutant_ligand.identity.label),
                measurement=Measurement(
                    name="pocket_residue_count_delta",
                    value=float(pocket_delta),
                    reference_value=float(len(reference_pocket)),
                    unit="residues",
                    direction=_direction(float(pocket_delta)),
                ),
                confidence=0.72,
                provenance=_provenance(request, "ligand-centered pocket definition"),
                limitations=(
                    "This is an operational pocket proxy, not an absolute cavity-volume calculation.",
                    "Pocket membership depends on ligand pose, crystal state, and the configured radius.",
                ),
            ),
            PhysicalEvidence(
                id=make_id(
                    "evidence",
                    "residue_network",
                    request.mutation.notation,
                    request.ligand.identifier,
                ),
                title="Ligand-pocket residue-network comparison",
                description=(
                    f"WT pocket network edges={len(reference_edges)}; mutant edges={len(mutant_edges)}; "
                    f"mutation-site degree delta={degree_delta}."
                ),
                evidence_type=EvidenceType.RESIDUE_NETWORK,
                status=EvidenceStatus.COMPUTED,
                entities=tuple(site.identity.label for site in (*reference_sites, *mutant_sites)),
                measurement=Measurement(
                    name="mutation_site_network_degree_delta",
                    value=float(degree_delta),
                    reference_value=float(ref_site_degrees),
                    unit="residue_contact_edges",
                    direction=_direction(float(degree_delta)),
                ),
                confidence=0.74,
                provenance=_provenance(request, "ligand-pocket residue contact graph"),
                limitations=(
                    f"Edges use a fixed {RESIDUE_EDGE_CUTOFF_ANGSTROM:.1f} A heavy-atom cutoff.",
                    f"Total pocket edge delta was {edge_delta}; the reported value focuses "
                    "on the mutation site.",
                ),
            ),
        )


def _pocket_residues(structure: ParsedStructure, ligand: ResidueRecord) -> tuple[ResidueRecord, ...]:
    ligand_atoms = _heavy_atoms(ligand)
    return tuple(
        residue
        for residue in structure.residues
        if not residue.is_hetero
        and not residue.is_water
        and any(
            atom_distance(atom, ligand_atom) <= POCKET_RADIUS_ANGSTROM
            for atom in _heavy_atoms(residue)
            for ligand_atom in ligand_atoms
        )
    )


def _contact_edges(residues: tuple[ResidueRecord, ...]) -> frozenset[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for index, first in enumerate(residues):
        for second in residues[index + 1 :]:
            if any(
                atom_distance(first_atom, second_atom) <= RESIDUE_EDGE_CUTOFF_ANGSTROM
                for first_atom in _heavy_atoms(first)
                for second_atom in _heavy_atoms(second)
            ):
                edges.add(tuple(sorted((first.identity.label, second.identity.label))))
    return frozenset(edges)


def _site_degree(site: ResidueRecord, edges: frozenset[tuple[str, str]]) -> int:
    return sum(site.identity.label in edge for edge in edges)


def _heavy_atoms(residue: ResidueRecord):
    return tuple(atom for atom in residue.atoms if atom.element not in {"D", "H"})


def _direction(value: float, tolerance: float = 0.001) -> Direction:
    if value > tolerance:
        return Direction.INCREASE
    if value < -tolerance:
        return Direction.DECREASE
    return Direction.UNCHANGED


def _provenance(request: AnalysisRequest, method: str) -> tuple[Provenance, ...]:
    assert request.mutant_structure is not None
    return (
        Provenance(
            kind=ProvenanceKind.STRUCTURE, source=request.structure.path, method=f"reference: {method}"
        ),
        Provenance(
            kind=ProvenanceKind.STRUCTURE, source=request.mutant_structure.path, method=f"mutant: {method}"
        ),
    )
