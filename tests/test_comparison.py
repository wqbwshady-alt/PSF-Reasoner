from pathlib import Path

import pytest

from psf_reasoner.bootstrap import create_default_service
from psf_reasoner.physical.comparison import ComparativeEvidenceProvider
from psf_reasoner.physical.energy import LocalEnergyEvidenceProvider
from psf_reasoner.physical.modeling import (
    LocalSideChainMutationModeler,
    MutationModelingUnavailableError,
    UnconfiguredMutationModeler,
)
from psf_reasoner.physical.pocket import PocketNetworkEvidenceProvider
from psf_reasoner.schemas.common import Direction
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType
from psf_reasoner.schemas.inputs import AnalysisRequest, LigandSpec, MutationSpec, StructureInput


@pytest.fixture
def paired_request(structure_file: Path, mutant_structure_file: Path) -> AnalysisRequest:
    return AnalysisRequest(
        structure=StructureInput(path=str(structure_file)),
        mutant_structure=StructureInput(path=str(mutant_structure_file)),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )


def test_paired_structures_emit_distance_contact_sasa_and_interaction_deltas(
    paired_request: AnalysisRequest,
) -> None:
    evidence = ComparativeEvidenceProvider().collect(paired_request)
    by_type = {item.evidence_type: item for item in evidence}

    assert set(by_type) == {
        EvidenceType.ATOMIC_DISTANCE,
        EvidenceType.RESIDUE_CONTACT,
        EvidenceType.SOLVENT_EXPOSURE,
        EvidenceType.HYDROGEN_BOND,
        EvidenceType.HYDROPHOBIC_CONTACT,
        EvidenceType.SALT_BRIDGE,
        EvidenceType.PI_INTERACTION,
        EvidenceType.WATER_BRIDGE,
        EvidenceType.POCKET_GEOMETRY,
    }
    assert all(item.status is EvidenceStatus.COMPUTED for item in evidence)
    assert by_type[EvidenceType.ATOMIC_DISTANCE].measurement is not None
    assert by_type[EvidenceType.ATOMIC_DISTANCE].measurement.value == 2.0
    assert by_type[EvidenceType.ATOMIC_DISTANCE].measurement.reference_value == 2.5
    assert by_type[EvidenceType.ATOMIC_DISTANCE].measurement.direction is Direction.INCREASE
    assert by_type[EvidenceType.RESIDUE_CONTACT].measurement is not None
    assert by_type[EvidenceType.RESIDUE_CONTACT].measurement.value == -1.0
    assert by_type[EvidenceType.WATER_BRIDGE].measurement is not None
    assert by_type[EvidenceType.WATER_BRIDGE].measurement.value == -1.0
    assert "proxy" in by_type[EvidenceType.POCKET_GEOMETRY].limitations[0]


def test_default_service_includes_comparative_evidence(paired_request: AnalysisRequest) -> None:
    report = create_default_service().analyze(paired_request)

    assert any(
        item.evidence_type is EvidenceType.SOLVENT_EXPOSURE and item.status is EvidenceStatus.COMPUTED
        for item in report.physical_evidence
    )
    assert report.request.mutant_structure is not None


def test_pocket_network_and_energy_providers_emit_computed_deltas(
    paired_request: AnalysisRequest,
) -> None:
    evidence = (
        *PocketNetworkEvidenceProvider().collect(paired_request),
        *LocalEnergyEvidenceProvider().collect(paired_request),
    )

    assert any(item.evidence_type is EvidenceType.RESIDUE_NETWORK for item in evidence)
    assert any(item.evidence_type is EvidenceType.ENERGY_COMPONENT for item in evidence)
    assert all(item.status is EvidenceStatus.COMPUTED for item in evidence)


def test_1sdt_1sdv_real_structure_pair_compares_v82a() -> None:
    request = AnalysisRequest(
        structure=StructureInput(path="examples/data/1sdt.cif"),
        mutant_structure=StructureInput(path="examples/data/1sdv.cif"),
        ligand=LigandSpec(identifier="MK1"),
        mutation=MutationSpec(notation="V82A", chain="A"),
    )

    evidence = ComparativeEvidenceProvider().collect(request)
    by_type = {item.evidence_type: item for item in evidence}

    assert by_type[EvidenceType.ATOMIC_DISTANCE].measurement is not None
    assert by_type[EvidenceType.ATOMIC_DISTANCE].measurement.value == 0.315
    assert by_type[EvidenceType.RESIDUE_CONTACT].measurement is not None
    assert by_type[EvidenceType.RESIDUE_CONTACT].measurement.value == -1.0


def test_unconfigured_mutation_modeler_never_fabricates_a_structure(
    paired_request: AnalysisRequest,
) -> None:
    assert paired_request.mutation is not None
    with pytest.raises(MutationModelingUnavailableError, match="no mutation-modeling engine"):
        UnconfiguredMutationModeler().build(
            paired_request.structure,
            paired_request.mutation,
            paired_request.ligand,
        )


def test_local_side_chain_modeler_builds_v82a_model(
    paired_request: AnalysisRequest,
) -> None:
    assert paired_request.mutation is not None
    result = LocalSideChainMutationModeler().build(
        paired_request.structure,
        paired_request.mutation,
        paired_request.ligand,
    )

    assert Path(result.structure.path).is_file()
    assert result.evidence.evidence_type is EvidenceType.MUTATION_MODEL
    assert result.evidence.status is EvidenceStatus.COMPUTED
