"""Entity normalization for proteins, mutations, and ligands (V3 P2).

Ensures that literature knowledge is mapped to the correct protein
accession, isoform, residue numbering, and ligand identity before
being used as evidence.  Prevents common errors like:
- Same residue number, different species
- Same protein, different isoform
- Different ligands treated as equivalent
- Different experimental systems conflated
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceApplicability(StrEnum):
    """How directly a piece of literature evidence applies to the query."""

    EXACT_MATCH = "exact_match"  # same protein, same site, same substitution, same ligand
    SAME_SITE_SAME_PROTEIN = "same_site_same_protein"  # same site, different substitution
    SAME_SITE_HOMOLOG = "same_site_homolog"  # homologous site in related protein
    NEARBY_SITE = "nearby_site"  # nearby residue in same protein
    SAME_PROTEIN_MECHANISM = "same_protein_mechanism"  # same protein, general mechanism
    FAMILY_ANALOGY = "family_analogy"  # same protein family, analogous mechanism
    GENERAL_BIOCHEMICAL = "general_biochemical"  # general biochemical principle


@dataclass
class ProteinEntity:
    """Normalized protein identity."""

    name: str
    uniprot_accession: str | None = None
    organism: str = ""
    gene_name: str = ""
    ec_number: str | None = None
    family: str = ""  # e.g. "aspartyl_protease", "kinase", "DHFR"


@dataclass
class MutationEntity:
    """Normalized mutation identity with numbering mapping."""

    notation: str  # standardised e.g. "V82A"
    wild_type: str
    residue_number: int
    mutant: str
    chain: str = ""
    pdb_numbering: int | None = None  # PDB residue number (may differ from UniProt)
    uniprot_numbering: int | None = None
    insertion_code: str | None = None


@dataclass
class LigandEntity:
    """Normalized ligand identity."""

    pdb_code: str  # 3-letter PDB ligand code
    name: str = ""
    smiles: str | None = None
    drugbank_id: str | None = None
    chembl_id: str | None = None
    role: str = ""  # inhibitor, substrate, cofactor, etc.


# ---------------------------------------------------------------------------
# Curated entity database (extensible)
# ---------------------------------------------------------------------------

_KNOWN_PROTEINS: dict[str, ProteinEntity] = {
    "HIV-1_PROTEASE": ProteinEntity(
        name="HIV-1 Protease",
        uniprot_accession="P03367",
        organism="Human immunodeficiency virus type 1",
        gene_name="pol",
        ec_number="3.4.23.16",
        family="aspartyl_protease",
    ),
    "DHFR": ProteinEntity(
        name="Dihydrofolate Reductase",
        uniprot_accession="P00374",
        organism="Homo sapiens",
        gene_name="DHFR",
        ec_number="1.5.1.3",
        family="DHFR",
    ),
    "EGFR": ProteinEntity(
        name="Epidermal Growth Factor Receptor",
        uniprot_accession="P00533",
        organism="Homo sapiens",
        gene_name="EGFR",
        ec_number="2.7.10.1",
        family="kinase",
    ),
    "ABL1": ProteinEntity(
        name="Tyrosine-protein kinase ABL1",
        uniprot_accession="P00519",
        organism="Homo sapiens",
        gene_name="ABL1",
        ec_number="2.7.10.2",
        family="kinase",
    ),
    "TEM1_BLAC": ProteinEntity(
        name="TEM-1 Beta-lactamase",
        uniprot_accession="P62593",
        organism="Escherichia coli",
        gene_name="bla",
        ec_number="3.5.2.6",
        family="beta_lactamase",
    ),
}

_KNOWN_LIGANDS: dict[str, LigandEntity] = {
    "MK1": LigandEntity(
        pdb_code="MK1",
        name="MK1 (hydroxyethylene isostere inhibitor)",
        role="inhibitor",
    ),
    "MTX": LigandEntity(
        pdb_code="MTX",
        name="Methotrexate",
        drugbank_id="DB00563",
        chembl_id="CHEMBL34259",
        role="inhibitor",
    ),
    "STI": LigandEntity(
        pdb_code="STI",
        name="Imatinib (Gleevec)",
        drugbank_id="DB00619",
        chembl_id="CHEMBL941",
        role="inhibitor",
    ),
    "FOL": LigandEntity(
        pdb_code="FOL",
        name="Folic Acid",
        drugbank_id="DB00158",
        role="substrate",
    ),
}


def lookup_protein(name_hint: str) -> ProteinEntity | None:
    """Resolve a protein family hint to a normalized ProteinEntity."""
    for key, entity in _KNOWN_PROTEINS.items():
        if name_hint.upper() == key or name_hint.upper() in key or key in name_hint.upper():
            return entity
    return None


def lookup_ligand(pdb_code: str) -> LigandEntity | None:
    """Resolve a PDB ligand code to a normalized LigandEntity."""
    return _KNOWN_LIGANDS.get(pdb_code.upper().strip())


def classify_evidence_applicability(
    query_protein: ProteinEntity | None,
    query_mutation: MutationEntity | None,
    query_ligand: LigandEntity | None,
    evidence_protein: ProteinEntity | None,
    evidence_mutation: MutationEntity | None,
    evidence_ligand: LigandEntity | None,
) -> EvidenceApplicability:
    """Classify how applicable a piece of literature evidence is to a query."""

    # Same protein?
    same_protein = (
        query_protein is not None
        and evidence_protein is not None
        and query_protein.uniprot_accession == evidence_protein.uniprot_accession
    )

    # Same site?
    same_site = (
        query_mutation is not None
        and evidence_mutation is not None
        and query_mutation.residue_number == evidence_mutation.residue_number
    )

    # Same substitution?
    same_substitution = (
        same_site
        and query_mutation.wild_type == evidence_mutation.wild_type
        and query_mutation.mutant == evidence_mutation.mutant
    )

    # Same ligand?
    same_ligand = (
        query_ligand is not None
        and evidence_ligand is not None
        and query_ligand.pdb_code == evidence_ligand.pdb_code
    )

    # Same family?
    same_family = (
        query_protein is not None
        and evidence_protein is not None
        and query_protein.family == evidence_protein.family
    )

    if same_protein and same_site and same_substitution and same_ligand:
        return EvidenceApplicability.EXACT_MATCH
    if same_protein and same_site:
        return EvidenceApplicability.SAME_SITE_SAME_PROTEIN
    if same_family and same_site:
        return EvidenceApplicability.SAME_SITE_HOMOLOG
    if (
        same_protein
        and query_mutation
        and evidence_mutation
        # Check if sites are nearby (within 5 residues)
        and abs(query_mutation.residue_number - evidence_mutation.residue_number) <= 5
    ):
        return EvidenceApplicability.NEARBY_SITE
    if same_protein:
        return EvidenceApplicability.SAME_PROTEIN_MECHANISM
    if same_family:
        return EvidenceApplicability.FAMILY_ANALOGY
    return EvidenceApplicability.GENERAL_BIOCHEMICAL
