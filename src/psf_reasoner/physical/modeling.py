"""Boundary for future mutation-model construction and local relaxation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import gettempdir
from typing import Protocol

from psf_reasoner.identifiers import make_id
from psf_reasoner.physical.preparation import EXPECTED_HEAVY_ATOMS
from psf_reasoner.physical.structure import (
    THREE_TO_ONE,
    AtomRecord,
    ParsedStructure,
    ResidueIdentity,
    ResidueRecord,
    StructureParser,
)
from psf_reasoner.schemas.common import Provenance, ProvenanceKind
from psf_reasoner.schemas.evidence import EvidenceStatus, EvidenceType, Measurement, PhysicalEvidence
from psf_reasoner.schemas.inputs import LigandSpec, MutationSpec, StructureInput

ONE_TO_THREE = {value: key for key, value in THREE_TO_ONE.items()}


class MutationModelingUnavailableError(RuntimeError):
    pass


class FoldXMutationModeler:
    """Mutation modeler using the FoldX ``BuildModel`` command.

    FoldX is a computational tool for predicting the effect of mutations on
    protein stability and interactions.  This adapter requires FoldX to be
    installed and available on ``PATH``.

    When FoldX is not available or the mutation is a truncation case
    (target residue is a subset of source), falls back to the local
    side-chain truncation modeler.
    """

    def __init__(
        self,
        parser: StructureParser | None = None,
        output_dir: str | None = None,
        foldx_binary: str = "foldx",
    ) -> None:
        import shutil

        self._parser = parser or StructureParser()
        self._output_dir = Path(output_dir or gettempdir()) / "psf_reasoner_models"
        self._foldx_available = shutil.which(foldx_binary) is not None
        self._foldx_binary = foldx_binary
        self._local = LocalSideChainMutationModeler(parser, output_dir)

    def build(
        self,
        reference_structure: StructureInput,
        mutation: MutationSpec,
        ligand: LigandSpec,
    ) -> MutationModelingResult:
        # Try FoldX first for gain-of-size mutations
        if self._foldx_available:
            try:
                return self._build_with_foldx(reference_structure, mutation, ligand)
            except MutationModelingUnavailableError:
                pass

        # Fall back to local modeler (handles truncation cases)
        return self._local.build(reference_structure, mutation, ligand)

    def _build_with_foldx(
        self,
        reference_structure: StructureInput,
        mutation: MutationSpec,
        ligand: LigandSpec,
    ) -> MutationModelingResult:
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path as P

        parsed = self._parser.parse(reference_structure)
        mutation_code = f"{mutation.wild_type}{mutation.residue_number}{mutation.mutant};"

        work_dir = P(tempfile.mkdtemp(prefix="foldx_"))
        try:
            # Copy input PDB to work directory (FoldX requires PDB in CWD)
            input_pdb = work_dir / f"{P(reference_structure.path).stem}.pdb"
            shutil.copy2(reference_structure.path, input_pdb)

            # Write FoldX config
            (work_dir / "config.cfg").write_text(
                f"command=BuildModel\npdb={input_pdb.stem}\nmutant-file=individual_list.txt\n"
            )
            (work_dir / "individual_list.txt").write_text(mutation_code + "\n")

            result = subprocess.run(
                [self._foldx_binary, "-f", "config.cfg"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(work_dir),
            )

            if result.returncode != 0:
                raise MutationModelingUnavailableError(
                    f"FoldX BuildModel failed: {result.stderr[:200]}"
                )

            # Find output PDB
            output_pdbs = list(work_dir.glob(f"{input_pdb.stem}_1.pdb"))
            if not output_pdbs:
                raise MutationModelingUnavailableError(
                    "FoldX did not produce output PDB"
                )

            output_path = self._output_dir / f"{input_pdb.stem}_{mutation.notation}_foldx.pdb"
            self._output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output_pdbs[0], output_path)

            structure_input = StructureInput(
                path=str(output_path),
                format=reference_structure.format,
                model_index=0,
            )

            fingerprint = sha256(
                f"{reference_structure.path}|foldx|{mutation.notation}".encode()
            ).hexdigest()[:16]

            return MutationModelingResult(
                structure=structure_input,
                evidence=PhysicalEvidence(
                    id=make_id("evidence", "mutation_model_foldx", mutation.notation, fingerprint),
                    title="FoldX-generated mutant model",
                    description=(
                        f"Generated a mutant model for {mutation.notation} using FoldX "
                        f"BuildModel. FoldX performs side-chain rotamer optimization "
                        f"and local backbone relaxation."
                    ),
                    evidence_type=EvidenceType.MUTATION_MODEL,
                    status=EvidenceStatus.COMPUTED,
                    entities=(f"{mutation.chain or ''}:{mutation.residue_number}",),
                    measurement=Measurement(
                        name="modelled_mutation_site_count",
                        value=1.0,
                        unit="sites",
                    ),
                    confidence=0.65,
                    provenance=(
                        Provenance(
                            kind=ProvenanceKind.COMPUTATION,
                            source=f"FoldX (via {self._foldx_binary})",
                            method="FoldX BuildModel with side-chain rotamer optimization",
                            parameters={
                                "mutation": mutation.notation,
                                "output": str(output_path),
                            },
                        ),
                    ),
                    limitations=(
                        "FoldX BuildModel performs local optimization only — "
                        "no global backbone relaxation or MD.",
                        "Accuracy depends on the FoldX energy function version.",
                        "Generated model is a computational prediction, not an "
                        "experimental structure.",
                    ),
                ),
            )
        finally:
            import shutil as _shutil

            _shutil.rmtree(work_dir, ignore_errors=True)


@dataclass(frozen=True, slots=True)
class MutationModelingResult:
    structure: StructureInput
    evidence: PhysicalEvidence


class MutationModeler(Protocol):
    def build(
        self,
        reference_structure: StructureInput,
        mutation: MutationSpec,
        ligand: LigandSpec,
    ) -> MutationModelingResult: ...


class UnconfiguredMutationModeler:
    """Explicitly prevents fabricated mutant structures in the local baseline."""

    def build(
        self,
        reference_structure: StructureInput,
        mutation: MutationSpec,
        ligand: LigandSpec,
    ) -> MutationModelingResult:
        raise MutationModelingUnavailableError(
            "no mutation-modeling engine is configured; provide mutant_structure or install an adapter"
        )


class LocalSideChainMutationModeler:
    """Deterministic local modeler for conservative side-chain truncation cases."""

    def __init__(self, parser: StructureParser | None = None, output_dir: str | None = None) -> None:
        self._parser = parser or StructureParser()
        self._output_dir = Path(output_dir or gettempdir()) / "psf_reasoner_models"

    def build(
        self,
        reference_structure: StructureInput,
        mutation: MutationSpec,
        ligand: LigandSpec,
    ) -> MutationModelingResult:
        del ligand
        parsed = self._parser.parse(reference_structure)
        target_name = ONE_TO_THREE.get(mutation.mutant)
        if target_name is None:
            raise MutationModelingUnavailableError(f"unsupported target residue code: {mutation.mutant}")
        expected_target = EXPECTED_HEAVY_ATOMS[target_name]
        residues: list[ResidueRecord] = []
        mutated_labels: list[str] = []
        for residue in parsed.residues:
            if _matches_mutation_site(residue, mutation):
                if residue.one_letter_code != mutation.wild_type:
                    raise MutationModelingUnavailableError(
                        f"{residue.identity.label} is {residue.one_letter_code}, "
                        f"expected {mutation.wild_type}"
                    )
                residues.append(_mutate_residue_by_truncation(residue, target_name, expected_target))
                mutated_labels.append(residue.identity.label)
            else:
                residues.append(residue)
        if not mutated_labels:
            raise MutationModelingUnavailableError(f"no residue matched {mutation.notation}")
        modelled = ParsedStructure(
            source_path=parsed.source_path,
            source_format=parsed.source_format,
            model_index=parsed.model_index,
            residues=tuple(residues),
            alternate_atom_count=0,
        )
        self._output_dir.mkdir(parents=True, exist_ok=True)
        fingerprint = sha256(
            f"{reference_structure.path}|{reference_structure.model_index}|{mutation.notation}|{mutation.chain}".encode()
        ).hexdigest()[:16]
        output_path = (
            self._output_dir / f"{Path(reference_structure.path).stem}_{mutation.notation}_{fingerprint}.pdb"
        )
        _write_pdb(modelled, output_path)
        structure_input = StructureInput(
            path=str(output_path), format=reference_structure.format, model_index=0
        )
        return MutationModelingResult(
            structure=structure_input,
            evidence=PhysicalEvidence(
                id=make_id("evidence", "mutation_model", mutation.notation, fingerprint),
                title="Automatic local mutant model generated",
                description=(
                    f"Generated a deterministic local mutant model for {mutation.notation}; "
                    "side-chain atoms not compatible with the target residue were removed "
                    "and shared atoms retained."
                ),
                evidence_type=EvidenceType.MUTATION_MODEL,
                status=EvidenceStatus.COMPUTED,
                entities=tuple(mutated_labels),
                measurement=Measurement(
                    name="modelled_mutation_site_count", value=float(len(mutated_labels)), unit="sites"
                ),
                confidence=0.52,
                provenance=(
                    Provenance(
                        kind=ProvenanceKind.COMPUTATION,
                        source="PSF local side-chain mutation modeler v1",
                        method="deterministic side-chain truncation and identity validation",
                        parameters={"mutation": mutation.notation, "output": str(output_path)},
                    ),
                ),
                limitations=(
                    "This local model is suitable for evidence plumbing and side-chain "
                    "truncation cases only.",
                    "It is not a rotamer search, molecular-dynamics relaxation, or "
                    "crystallographic mutant structure.",
                ),
            ),
        )


def _matches_mutation_site(residue: ResidueRecord, mutation: MutationSpec) -> bool:
    return (
        residue.identity.number == mutation.residue_number
        and residue.identity.insertion_code == mutation.insertion_code
        and (mutation.chain is None or residue.identity.chain == mutation.chain)
    )


def _mutate_residue_by_truncation(
    residue: ResidueRecord,
    target_name: str,
    expected_target: frozenset[str],
) -> ResidueRecord:
    identity = ResidueIdentity(
        chain=residue.identity.chain,
        name=target_name,
        number=residue.identity.number,
        insertion_code=residue.identity.insertion_code,
    )
    observed_names = {atom.name for atom in residue.atoms}
    atoms: list[AtomRecord] = []
    for atom in residue.atoms:
        name = atom.name
        if name not in expected_target:
            if target_name == "ALA" and name == "CG1" and "CB" not in observed_names:
                name = "CB"
            else:
                continue
        atoms.append(
            AtomRecord(
                residue=identity,
                name=name,
                element=atom.element,
                x=atom.x,
                y=atom.y,
                z=atom.z,
                occupancy=atom.occupancy,
                altloc=None,
                formal_charge=atom.formal_charge,
            )
        )
    if not atoms:
        raise MutationModelingUnavailableError(f"cannot construct target residue {target_name}")
    return ResidueRecord(
        identity=identity,
        one_letter_code=THREE_TO_ONE.get(target_name),
        is_hetero=False,
        atoms=tuple(atoms),
    )


def _write_pdb(structure: ParsedStructure, path: Path) -> None:
    serial = 1
    lines: list[str] = ["HEADER    PSF-REASONER LOCAL MUTANT MODEL"]
    for residue in structure.residues:
        record = "HETATM" if residue.is_hetero else "ATOM  "
        for atom in residue.atoms:
            insertion = residue.identity.insertion_code or " "
            lines.append(
                f"{record}{serial:5d} {atom.name:<4s}{residue.identity.name:>4s} {residue.identity.chain:1s}"
                f"{residue.identity.number:4d}{insertion:1s}   {atom.x:8.3f}{atom.y:8.3f}{atom.z:8.3f}"
                f"{atom.occupancy:6.2f}{20.00:6.2f}          {atom.element:>2s}"
            )
            serial += 1
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
