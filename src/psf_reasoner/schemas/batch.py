"""Batch execution contracts."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from psf_reasoner.schemas.common import Direction, ScientificModel
from psf_reasoner.schemas.inputs import (
    AnalysisRequest,
    LigandSpec,
    MutationSpec,
    PhenotypeSpec,
    StructureInput,
)


class BatchCase(ScientificModel):
    """A single case within a batch manifest."""

    case_id: str = Field(min_length=1)
    structure: StructureInput
    mutant_structure: StructureInput | None = None
    ligand: LigandSpec
    mutation: MutationSpec | None = None
    phenotype: PhenotypeSpec | None = None
    study_context: str | None = None

    def to_request(self) -> AnalysisRequest:
        return AnalysisRequest(
            structure=self.structure,
            mutant_structure=self.mutant_structure,
            ligand=self.ligand,
            mutation=self.mutation,
            phenotype=self.phenotype,
            study_context=self.study_context,
        )


class BatchManifest(ScientificModel):
    """A collection of analysis cases to run as a batch."""

    batch_id: str = Field(min_length=1)
    description: str = ""
    cases: tuple[BatchCase, ...] = ()


class BatchJobResult(ScientificModel):
    """Result of a single job within a batch."""

    case_id: str
    report_id: str | None = None
    status: str = "pending"  # "success" | "error" | "pending"
    error: str | None = None
    elapsed_seconds: float | None = None


class BatchResult(ScientificModel):
    """Aggregate result of a batch run."""

    batch_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    jobs: tuple[BatchJobResult, ...] = ()
    total: int = 0
    succeeded: int = 0
    failed: int = 0

    @property
    def success_rate(self) -> float:
        return self.succeeded / self.total if self.total > 0 else 0.0
