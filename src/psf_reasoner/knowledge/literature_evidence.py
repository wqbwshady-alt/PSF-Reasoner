"""Curated literature evidence database (V3 P2) — evidence-audited.

Each entry maps to a specific protein + mutation + ligand combination with
structured claims, experimental values, and provenance.

Audit history: earlier revisions contained 9 entries, several of which
cited PMIDs unrelated to their claims or DOIs that do not exist
(docs/EVIDENCE-REVIEW.md, 2026-09-10).  Only entries whose PMID and, where
present, numeric value were verified against the cited literature remain
in this module.
"""

from __future__ import annotations

from psf_reasoner.knowledge.entity_normalizer import EvidenceApplicability
from psf_reasoner.knowledge.evidence_ranker import LiteratureEvidence, MeasurementType

# ---------------------------------------------------------------------------
# Curated evidence entries
# ---------------------------------------------------------------------------

_CURATED_EVIDENCE: dict[str, list[LiteratureEvidence]] = {}


def _register(protein: str, entries: list[LiteratureEvidence]) -> None:
    _CURATED_EVIDENCE[protein] = entries


# ---- HIV-1 Protease ----------------------------------------------------------

_register(
    "HIV-1_PROTEASE",
    [
        LiteratureEvidence(
            evidence_id="HIV_V82A_MK1_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="15066177",
            doi="10.1111/j.1432-1033.2004.04060.x",
            measurement_type=MeasurementType.REPORTED_KI_KD,
            measured_value=3.3,
            measured_unit="fold_increase_Ki",
            measured_direction="increased",
            original_conclusion=(
                "The inhibition (Ki) of PR(V82A) was 3.3-fold that of wild type against indinavir (MK1)."
            ),
            structured_claim=(
                "V82A reduces indinavir binding affinity (~3.3-fold Ki increase) "
                "through altered S2 pocket packing."
            ),
            experimental_system="in vitro purified enzyme",
            notes="fold verified from the abstract; absolute Ki values need the paywalled full text.",
        ),
        LiteratureEvidence(
            evidence_id="HIV_L90M_MK1_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="15066177",
            doi="10.1111/j.1432-1033.2004.04060.x",
            measurement_type=MeasurementType.REPORTED_KI_KD,
            measured_value=0.16,
            measured_unit="fold_Ki",
            measured_direction="decreased",
            original_conclusion=(
                "The inhibition (Ki) of PR(L90M) was 0.16-fold that of wild type "
                "against indinavir (MK1), i.e. increased susceptibility."
            ),
            structured_claim=(
                "L90M increases susceptibility to indinavir (~0.16-fold Ki), "
                "contrasting with V82A."
            ),
            experimental_system="in vitro purified enzyme",
            notes="fold verified from the abstract.",
        ),
        LiteratureEvidence(
            evidence_id="HIV_G48V_SQV_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="18597780",
            doi="10.1016/j.jmb.2008.05.062",
            measurement_type=MeasurementType.REPORTED_KI_KD,
            measured_value=86.0,
            measured_unit="fold_Ki",
            measured_direction="increased",
            original_conclusion=(
                "G48V raises the Ki for saquinavir from 0.42 nM to 36 nM "
                "(Table 1), an 86-fold loss of binding."
            ),
            structured_claim=(
                "G48V perturbs the flap region and strongly reduces "
                "saquinavir binding (86-fold Ki increase)."
            ),
            experimental_system="in vitro purified enzyme",
            notes="Table 1 values verified against PMC2754059.",
        ),
    ],
)

# ---- DHFR -------------------------------------------------------------------

_register(
    "DHFR",
    [
        LiteratureEvidence(
            evidence_id="DHFR_L22F_MTX_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="8643082",
            measurement_type=MeasurementType.REPORTED_KI_KD,
            measured_value=88.0,
            measured_unit="fold_Ki",
            measured_direction="increased",
            original_conclusion=("Leu22->Phe in human DHFR raises the methotrexate Ki 88-fold."),
            structured_claim=(
                "L22F reduces methotrexate binding (88-fold Ki increase) "
                "through pteridine-pocket perturbation."
            ),
            experimental_system="in vitro purified enzyme",
            notes="88-fold from the abstract; full-text table pending.",
        ),
        LiteratureEvidence(
            evidence_id="DHFR_F31R_MTX_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="19478082",
            measurement_type=MeasurementType.CURATED_DDG,
            measured_value=2.1,
            measured_unit="kcal_per_mol",
            measured_direction="increased",
            original_conclusion=(
                "Phe31->Arg in human DHFR destabilizes methotrexate binding by 2.1 kcal/mol (35-fold)."
            ),
            structured_claim="F31R removes a key methotrexate anchoring contact (2.1 kcal/mol binding loss).",
            experimental_system="in vitro purified enzyme",
            notes="delta-delta-G read from PMC2740434 Table 2.",
        ),
    ],
)

# ---- EGFR Kinase ------------------------------------------------------------

_register(
    "EGFR",
    [
        LiteratureEvidence(
            evidence_id="EGFR_T790M_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="15737014",
            measurement_type=MeasurementType.QUALITATIVE_OBSERVATION,
            original_conclusion=(
                "A second EGFR kinase-domain mutation, T790M, underlies acquired "
                "resistance to gefitinib and erlotinib in NSCLC."
            ),
            structured_claim=(
                "T790M gatekeeper mutation confers acquired resistance "
                "to first-generation EGFR inhibitors."
            ),
            experimental_system="clinical samples + cell-based assays",
            notes="PMID 15728811 (Kobayashi 2005) and 15737014 (Pao 2005) both "
            "report T790M acquired resistance; the attribution between the "
            "two PMIDs still needs human confirmation.",
        ),
        LiteratureEvidence(
            evidence_id="EGFR_T790M_OSIMERTINIB_001",
            applicability=EvidenceApplicability.EXACT_MATCH,
            pmid="25923549",
            doi="10.1056/NEJMoa1411817",
            measurement_type=MeasurementType.QUALITATIVE_OBSERVATION,
            original_conclusion=(
                "Osimertinib (AZD9291) is effective in NSCLC with the EGFR T790M resistance mutation."
            ),
            structured_claim=(
                "Third-generation irreversible inhibitors (osimertinib) "
                "overcome T790M-mediated resistance."
            ),
            experimental_system="clinical trial + cell-based assays",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Query interface
# ---------------------------------------------------------------------------


def query_evidence(
    protein_family: str,
    mutation_notation: str = "",
    ligand_identifier: str = "",
    max_grade: int = 3,
) -> list[LiteratureEvidence]:
    """Retrieve curated evidence for a protein system.

    Filters by *protein_family* key and optionally by mutation/ligand.
    Returns only evidence with grade <= *max_grade* (1-5).

    An empty or unknown *protein_family* returns an empty list — it must
    never fall back to another protein's evidence.
    """
    key = protein_family.upper().strip()
    if not key:
        return []
    entries = _CURATED_EVIDENCE.get(key, [])
    if not entries:
        # Try partial match — only when the key is non-trivial, so junk or
        # empty keys cannot attach unrelated protein evidence.
        for k in _CURATED_EVIDENCE:
            if (key in k or k in key) and len(key) >= 3:
                entries = _CURATED_EVIDENCE[k]
                break

    results: list[LiteratureEvidence] = []
    for entry in entries:
        grade = entry.compute_grade()
        if int(grade) > max_grade:
            continue
        results.append(entry)

    return results


def get_evidence_summary(
    protein_family: str,
    mutation_notation: str = "",
) -> dict:
    """Return a structured summary of available evidence for a protein system.

    Suitable for inclusion in the Structural Context or for display
    in the frontend evidence panel.
    """
    entries = query_evidence(protein_family, mutation_notation, max_grade=5)
    by_grade: dict[str, list[dict]] = {}
    for entry in entries:
        grade_name = entry.compute_grade().name
        if grade_name not in by_grade:
            by_grade[grade_name] = []
        by_grade[grade_name].append(
            {
                "evidence_id": entry.evidence_id,
                "applicability": entry.applicability.value,
                "claim": entry.structured_claim,
                "pmid": entry.pmid,
                "measurement_type": entry.measurement_type.name,
                "measured_value": entry.measured_value,
                "measured_unit": entry.measured_unit,
            }
        )

    return {
        "protein_family": protein_family,
        "total_entries": len(entries),
        "by_grade": by_grade,
        "has_direct_evidence": any(e.applicability == EvidenceApplicability.EXACT_MATCH for e in entries),
        "has_quantitative_evidence": any(e.measured_value is not None for e in entries),
    }
