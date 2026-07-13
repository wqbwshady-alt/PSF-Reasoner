"""Coordinate-derived protein-ligand evidence provider."""

from psf_reasoner.identifiers import make_id
from psf_reasoner.physical.geometry import AtomPairDistance, nearest_heavy_atom_pair
from psf_reasoner.physical.structure import StructureParser
from psf_reasoner.schemas.common import Direction, Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import (
    EvidenceStatus,
    EvidenceType,
    Measurement,
    PhysicalEvidence,
)
from psf_reasoner.schemas.inputs import AnalysisRequest

DEFAULT_CONTACT_CUTOFF_ANGSTROM = 4.0


class CoordinateEvidenceProvider:
    """Compute distances and contacts from the supplied structure's coordinates."""

    def __init__(
        self,
        parser: StructureParser | None = None,
        contact_cutoff_angstrom: float = DEFAULT_CONTACT_CUTOFF_ANGSTROM,
    ) -> None:
        if contact_cutoff_angstrom <= 0:
            raise ValueError("contact_cutoff_angstrom must be positive")
        self._parser = parser or StructureParser()
        self._contact_cutoff_angstrom = contact_cutoff_angstrom

    def collect(self, request: AnalysisRequest) -> tuple[PhysicalEvidence, ...]:
        if request.mutation is None:
            return ()
        structure = self._parser.parse(request.structure)
        ligand = structure.locate_ligand(request.ligand)
        mutation_residues = structure.locate_mutation_residues(request.mutation)
        evidence: list[PhysicalEvidence] = []
        for residue in mutation_residues:
            pair = nearest_heavy_atom_pair(residue, ligand)
            if pair is None:
                continue
            distance_evidence = self._distance_evidence(
                request,
                structure.source_path,
                residue.identity.label,
                ligand.identity.label,
                pair,
            )
            evidence.append(distance_evidence)
            if pair.angstrom <= self._contact_cutoff_angstrom:
                evidence.append(
                    PhysicalEvidence(
                        id=make_id(
                            "evidence",
                            "residue_contact",
                            request.mutation.notation,
                            residue.identity.label,
                            ligand.identity.label,
                            self._contact_cutoff_angstrom,
                        ),
                        title=(
                            f"Coordinate-derived contact: {residue.identity.label} to {ligand.identity.label}"
                        ),
                        description=(
                            f"The nearest heavy-atom pair ({pair.first.label}, {pair.second.label}) is "
                            f"within the {self._contact_cutoff_angstrom:.1f} A contact cutoff."
                        ),
                        evidence_type=EvidenceType.RESIDUE_CONTACT,
                        status=EvidenceStatus.COMPUTED,
                        entities=(residue.identity.label, ligand.identity.label),
                        measurement=Measurement(
                            name="minimum_heavy_atom_distance",
                            value=round(pair.angstrom, 3),
                            unit="angstrom",
                            direction=Direction.UNKNOWN,
                        ),
                        confidence=0.95,
                        provenance=self._provenance(
                            structure.source_path,
                            request,
                            "nearest heavy-atom contact with fixed cutoff",
                        ),
                        supports=(distance_evidence.id,),
                        limitations=(
                            "A geometric contact does not by itself specify interaction "
                            "chemistry or strength.",
                        ),
                    )
                )
        return tuple(evidence)

    def _distance_evidence(
        self,
        request: AnalysisRequest,
        source_path: str,
        residue_label: str,
        ligand_label: str,
        pair: AtomPairDistance,
    ) -> PhysicalEvidence:
        return PhysicalEvidence(
            id=make_id(
                "evidence",
                "atomic_distance",
                request.mutation.notation if request.mutation else "none",
                residue_label,
                ligand_label,
            ),
            title=f"Nearest heavy-atom distance: {residue_label} to {ligand_label}",
            description=(
                f"The nearest heavy-atom pair is {pair.first.label} to {pair.second.label} "
                f"at {pair.angstrom:.3f} A in the supplied structure."
            ),
            evidence_type=EvidenceType.ATOMIC_DISTANCE,
            status=EvidenceStatus.COMPUTED,
            entities=(residue_label, ligand_label, pair.first.label, pair.second.label),
            measurement=Measurement(
                name="minimum_heavy_atom_distance",
                value=round(pair.angstrom, 3),
                unit="angstrom",
                direction=Direction.UNKNOWN,
            ),
            confidence=0.98,
            provenance=self._provenance(source_path, request, "minimum Euclidean heavy-atom distance"),
            limitations=(
                "Coordinates represent the supplied model only; alternate conformations "
                "are reduced by occupancy.",
            ),
        )

    def _provenance(
        self,
        source_path: str,
        request: AnalysisRequest,
        method: str,
    ) -> tuple[Provenance, ...]:
        return (
            Provenance(
                kind=ProvenanceKind.STRUCTURE,
                source=source_path,
                method=f"gemmi parse + {method}",
                parameters={
                    "model_index": request.structure.model_index,
                    "contact_cutoff_angstrom": self._contact_cutoff_angstrom,
                },
            ),
        )
