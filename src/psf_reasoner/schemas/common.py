"""Shared value objects used across scientific layers."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
ParameterValue = str | int | float | bool | None


class ScientificModel(BaseModel):
    """Strict immutable base for report data."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ProvenanceKind(StrEnum):
    INPUT = "input"
    BUILTIN_PRIOR = "builtin_prior"
    STRUCTURE = "structure"
    COMPUTATION = "computation"
    EXPERIMENT = "experiment"
    LITERATURE = "literature"


class Provenance(ScientificModel):
    kind: ProvenanceKind
    source: str = Field(min_length=1)
    method: str | None = None
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)
    notes: str | None = None


class Claim(ScientificModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*-[a-f0-9]{12}$")
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    confidence: Confidence
    provenance: tuple[Provenance, ...] = ()
    supports: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class Direction(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    CHANGE = "change"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"
