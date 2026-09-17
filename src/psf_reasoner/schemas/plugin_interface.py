"""Unified plugin interface for external tools (V3 P5a).

Defines the standard schema for integrating external computational tools
(FoldX, Rosetta, MM/GBSA, MD engines, etc.) without coupling the core
reasoning engine to specific implementations.

All external tool outputs are normalized through this interface before
entering the Evidence Graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PluginToolType(StrEnum):
    """Categories of external tools."""

    ENERGY_CALCULATION = "energy_calculation"
    MD_ENGINE = "md_engine"
    DOCKING = "docking"
    POCKET_ANALYSIS = "pocket_analysis"
    STRUCTURE_PREDICTION = "structure_prediction"
    EXPERIMENTAL_DATA = "experimental_data"
    OTHER = "other"


@dataclass
class PluginProvenance:
    """Complete provenance record for an external tool execution."""

    tool_name: str
    tool_version: str
    method: str
    input_structure: str  # path or identifier
    parameters: dict = field(default_factory=dict)
    execution_time: str = ""  # ISO format timestamp
    compute_environment: str = ""  # "local", "HPC", "cloud"
    output_files: list[str] = field(default_factory=list)


@dataclass
class PluginResult:
    """Standardised output from an external tool plugin.

    Every external tool result must be normalized to this schema before
    the reasoning engine can consume it.  This ensures that FoldX, Rosetta,
    MM/GBSA, and user-provided data all follow the same contract.
    """

    # Identity
    result_id: str
    tool_type: PluginToolType
    provenance: PluginProvenance

    # What was computed
    result_kind: str  # "ddG_binding", "contact_occupancy", etc.
    result_value: float
    result_unit: str
    result_direction: str  # "increased", "decreased", "unchanged"
    uncertainty: float | None = None
    reference_value: float | None = None

    # Quality
    confidence: str = "moderate"  # qualitative: "high", "moderate", "low"
    quality_flags: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    # Link to structure
    mutation: str = ""
    chain: str = ""
    ligand: str = ""

    def to_evidence_dict(self) -> dict:
        """Convert to a dict suitable for Evidence Graph integration."""
        return {
            "result_id": self.result_id,
            "tool": self.provenance.tool_name,
            "kind": self.result_kind,
            "value": self.result_value,
            "unit": self.result_unit,
            "direction": self.result_direction,
            "uncertainty": self.uncertainty,
            "confidence": self.confidence,
            "assumptions": self.assumptions,
            "limitations": self.limitations,
        }


# ---------------------------------------------------------------------------
# Plugin registry — extend with real implementations as they become available
# ---------------------------------------------------------------------------

_PLUGIN_REGISTRY: dict[str, dict] = {}


def register_plugin(name: str, tool_type: PluginToolType, description: str) -> None:
    """Register an external tool plugin in the system registry."""
    _PLUGIN_REGISTRY[name] = {
        "name": name,
        "tool_type": tool_type.value,
        "description": description,
    }


def list_registered_plugins() -> list[dict]:
    """Return all registered external tool plugins."""
    return list(_PLUGIN_REGISTRY.values())


# Pre-register known tool categories as placeholders
register_plugin("foldx", PluginToolType.ENERGY_CALCULATION, "FoldX empirical force field for ΔΔG prediction")
register_plugin("rosetta", PluginToolType.ENERGY_CALCULATION, "Rosetta macromolecular modeling suite")
register_plugin("mmgbsa", PluginToolType.ENERGY_CALCULATION, "MM/GBSA continuum solvent binding energy")
register_plugin("fpocket", PluginToolType.POCKET_ANALYSIS, "fpocket pocket detection and characterization")
register_plugin("gromacs", PluginToolType.MD_ENGINE, "GROMACS molecular dynamics engine")
register_plugin("amber", PluginToolType.MD_ENGINE, "AMBER molecular dynamics suite")
register_plugin(
    "user_experiment",
    PluginToolType.EXPERIMENTAL_DATA,
    "User-provided experimental measurements (Ki, Kd, IC50, etc.)",
)
