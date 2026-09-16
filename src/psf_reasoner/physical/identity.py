"""Protein identity extraction from structure files.

Reads the depositor-provided title / entity names from a PDB or mmCIF file
and maps them onto the protein-family hints understood by the knowledge
layer.  Identity is derived from the structure itself — never guessed from
the ligand abbreviation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import gemmi

# Keyword → knowledge-layer family key.  Keys must match the registration
# keys in knowledge/literature_evidence.py.
_FAMILY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("HIV-1_PROTEASE", ("hiv", "retroviral protease", "human immunodeficiency")),
    ("DHFR", ("dihydrofolate reductase", "dhfr")),
    ("EGFR", ("epidermal growth factor receptor", "egfr", "erbb1")),
    ("ABL1", ("tyrosine-protein kinase abl", "abl1", "bcr-abl", "c-abl")),
    ("BLAC", ("beta-lactamase", "tem-1", "tem1")),
    ("TRYP", ("trypsin",)),
    ("MPRO", ("3c-like protease", "3cl protease", "main protease", "sars-cov-2")),
    ("NEUR", ("neuraminidase", "sialidase")),
)


@dataclass(frozen=True, slots=True)
class ProteinIdentity:
    """Best-effort identity extracted from a structure file header."""

    title: str = ""
    entity_names: tuple[str, ...] = field(default_factory=tuple)
    family_hint: str = ""  # knowledge-layer family key, "" when unknown
    source: str = ""  # where the information came from, for provenance

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "entity_names": list(self.entity_names),
            "family_hint": self.family_hint or None,
            "source": self.source,
        }


def extract_protein_identity(structure_path: str | Path) -> ProteinIdentity:
    """Extract protein identity from a PDB/mmCIF file header.

    Returns a ``ProteinIdentity`` with an empty ``family_hint`` when the
    structure cannot be read or no known family keyword matches.  It never
    fabricates an identity.
    """
    try:
        structure = gemmi.read_structure(str(structure_path))
    except Exception:
        return ProteinIdentity(source="unreadable structure")

    info = structure.info
    try:
        title = (info["_struct.title"] or "").strip()
    except (KeyError, TypeError):
        title = ""
    entity_names: list[str] = []
    seen: set[str] = set()
    for entity in structure.entities:
        name = entity.name.strip()
        if name and name not in seen:
            seen.add(name)
            entity_names.append(name)

    text = " ".join([title, *entity_names]).lower()
    family_hint = ""
    for family_key, keywords in _FAMILY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            family_hint = family_key
            break

    return ProteinIdentity(
        title=title,
        entity_names=tuple(entity_names),
        family_hint=family_hint,
        source="structure header (_struct.title / entity names)",
    )
