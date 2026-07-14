"""Analysis input contracts."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import Field, model_validator

from psf_reasoner.schemas.common import Direction, ScientificModel

MUTATION_PATTERN = re.compile(r"^(?P<wild>[A-Z])(?P<number>[1-9][0-9]*)(?P<icode>[A-Z]?)(?P<mutant>[A-Z])$")


class StructureFormat(StrEnum):
    AUTO = "auto"
    PDB = "pdb"
    MMCIF = "mmcif"


class StructureInput(ScientificModel):
    path: str | None = Field(default=None, min_length=1)
    upload_id: str | None = Field(default=None, min_length=1, max_length=128)
    format: StructureFormat = StructureFormat.AUTO
    model_index: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def require_path_or_upload_id(self) -> StructureInput:
        if self.path is None and self.upload_id is None:
            raise ValueError("at least one of 'path' or 'upload_id' is required")
        return self


class LigandSpec(ScientificModel):
    identifier: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_.+-]+$")
    chain: str | None = Field(default=None, min_length=1, max_length=4)
    residue_number: int | None = None


class MutationSpec(ScientificModel):
    notation: str = Field(pattern=r"^[A-Z][1-9][0-9]*[A-Z]?[A-Z]$")
    chain: str | None = Field(default=None, min_length=1, max_length=4)
    wild_type: str = ""
    residue_number: int = 0
    insertion_code: str | None = None
    mutant: str = ""

    @model_validator(mode="before")
    @classmethod
    def parse_notation(cls, data: object) -> object:
        if not isinstance(data, dict) or "notation" not in data:
            return data
        match = MUTATION_PATTERN.fullmatch(str(data["notation"]).upper())
        if match is None:
            return data
        parsed = dict(data)
        parsed["notation"] = str(data["notation"]).upper()
        parsed["wild_type"] = match.group("wild")
        parsed["residue_number"] = int(match.group("number"))
        parsed["insertion_code"] = match.group("icode") or None
        parsed["mutant"] = match.group("mutant")
        return parsed


class PhenotypeSpec(ScientificModel):
    name: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    direction: Direction = Direction.INCREASE
    description: str | None = None


class AnalysisMode(StrEnum):
    FORWARD = "forward"
    REVERSE = "reverse"
    BIDIRECTIONAL = "bidirectional"


class AnalysisRequest(ScientificModel):
    structure: StructureInput
    mutant_structure: StructureInput | None = None
    ligand: LigandSpec
    mutation: MutationSpec | None = None
    phenotype: PhenotypeSpec | None = None
    study_context: str | None = None

    @model_validator(mode="after")
    def require_reasoning_anchor(self) -> AnalysisRequest:
        if self.mutation is None and self.phenotype is None:
            raise ValueError("at least one of mutation or phenotype is required")
        return self

    @property
    def mode(self) -> AnalysisMode:
        if self.mutation is not None and self.phenotype is not None:
            return AnalysisMode.BIDIRECTIONAL
        if self.mutation is not None:
            return AnalysisMode.FORWARD
        return AnalysisMode.REVERSE
