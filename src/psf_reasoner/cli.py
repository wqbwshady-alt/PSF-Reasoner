"""Typer command-line adapter."""

import json
from pathlib import Path
from typing import Annotated

import typer

from psf_reasoner.application.ports import StructureInputError
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.schemas.inputs import (
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    PhenotypeSpec,
    StructureInput,
)

app = typer.Typer(
    name="psf",
    help="Bidirectional physical-structural-functional reasoning.",
    no_args_is_help=True,
)
_runner = create_default_runner()

StructureOption = Annotated[
    Path,
    typer.Option("--structure", exists=True, dir_okay=False, readable=True),
]
MutantStructureOption = Annotated[
    Path | None,
    typer.Option("--mutant-structure", exists=True, dir_okay=False, readable=True),
]
LigandOption = Annotated[str, typer.Option("--ligand", help="Ligand identifier.")]


@app.command()
def forward(
    structure: StructureOption,
    ligand: LigandOption,
    mutation: Annotated[str, typer.Option("--mutation", help="Mutation such as V82A.")],
    chain: Annotated[str | None, typer.Option("--chain")] = None,
    mutant_structure: MutantStructureOption = None,
) -> None:
    """Infer structural mechanisms and functions from a mutation."""
    request = _request(
        structure,
        ligand,
        mutation=mutation,
        chain=chain,
        mutant_structure=mutant_structure,
    )
    _write_report(request)


@app.command()
def reverse(
    structure: StructureOption,
    ligand: LigandOption,
    phenotype: Annotated[str, typer.Option("--phenotype")],
) -> None:
    """Infer candidate mechanisms and required evidence from a phenotype."""
    request = _request(structure, ligand, phenotype=phenotype)
    _write_report(request)


@app.command()
def analyze(
    structure: StructureOption,
    ligand: LigandOption,
    mutation: Annotated[str, typer.Option("--mutation")],
    phenotype: Annotated[str, typer.Option("--phenotype")],
    chain: Annotated[str | None, typer.Option("--chain")] = None,
    mutant_structure: MutantStructureOption = None,
) -> None:
    """Run both directions and check their consistency."""
    request = _request(
        structure,
        ligand,
        mutation=mutation,
        phenotype=phenotype,
        chain=chain,
        mutant_structure=mutant_structure,
    )
    _write_report(request)


def _request(
    structure: Path,
    ligand: str,
    *,
    mutation: str | None = None,
    phenotype: str | None = None,
    chain: str | None = None,
    mutant_structure: Path | None = None,
) -> AnalysisRequest:
    return AnalysisRequest(
        structure=StructureInput(path=str(structure)),
        mutant_structure=StructureInput(path=str(mutant_structure)) if mutant_structure else None,
        ligand=LigandSpec(identifier=ligand),
        mutation=MutationSpec(notation=mutation, chain=chain) if mutation else None,
        phenotype=PhenotypeSpec(name=phenotype) if phenotype else None,
    )


def _write_report(request: AnalysisRequest) -> None:
    try:
        report = _runner.run(request)
    except StructureInputError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
