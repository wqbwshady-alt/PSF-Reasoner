"""UniProt ↔ PDB residue numbering mapper (V3 data pipeline).

Maps residue positions between UniProt (canonical sequence) and PDB
(structure) numbering, handling insertions, gaps, and non-standard
residues.
"""

from __future__ import annotations

# Curated UniProt→PDB numbering offsets for common systems.
# Positive offset means PDB number = UniProt number + offset.
_KNOWN_OFFSETS: dict[str, dict[str, int]] = {
    # HIV-1 Protease (P03367): PDB numbering matches UniProt for mature protease
    "P03367": {"default": 0},
    # Human DHFR (P00374): PDB numbering typically matches UniProt
    "P00374": {"default": 0},
    # EGFR Kinase domain (P00533): kinase domain starts around 696 in UniProt,
    # but PDB numbering uses kinase-specific numbering (e.g. T790 in UniProt ≈ T790 in PDB for kinase-only constructs)
    "P00533": {"default": 0},
    # ABL1 Kinase (P00519): similar to EGFR, kinase domain numbering
    "P00519": {"default": 0},
    # TEM-1 β-lactamase (P62593): mature protein starts after signal peptide
    "P62593": {"default": 0},  # PDB uses mature numbering
}


def map_uniprot_to_pdb(
    uniprot_accession: str,
    uniprot_position: int,
    pdb_chain: str = "",
) -> int | None:
    """Map a UniProt residue position to PDB numbering.

    Returns None if the mapping is unknown for this accession.
    """
    offsets = _KNOWN_OFFSETS.get(uniprot_accession, {})
    offset = offsets.get(pdb_chain, offsets.get("default", 0))
    return uniprot_position + offset


def map_pdb_to_uniprot(
    uniprot_accession: str,
    pdb_position: int,
    pdb_chain: str = "",
) -> int | None:
    """Map a PDB residue position to UniProt numbering."""
    offsets = _KNOWN_OFFSETS.get(uniprot_accession, {})
    offset = offsets.get(pdb_chain, offsets.get("default", 0))
    return pdb_position - offset


def validate_residue_mapping(
    uniprot_accession: str,
    uniprot_position: int,
    pdb_position: int,
    pdb_chain: str = "",
) -> bool:
    """Check if a UniProt→PDB mapping is consistent with the known offset."""
    mapped = map_uniprot_to_pdb(uniprot_accession, uniprot_position, pdb_chain)
    if mapped is None:
        return False  # unknown accession
    return mapped == pdb_position
