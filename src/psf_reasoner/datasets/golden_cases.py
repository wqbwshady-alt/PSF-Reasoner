"""Curated mutation–ligand cases (V3 data pipeline) — evidence-audited.

Previous revisions of this module claimed "118 verified golden cases".
An independent literature audit (docs/EVIDENCE-REVIEW.md, 2026-09-10)
found that 103/118 entries cited PMIDs unrelated to their claims and that
50 entries were quota-filling bulk rows with fabricated fold values.

This revision contains ONLY:

- ``review_status=ACCEPTED`` — cases whose PMID, direction, and (where
  present) numeric value were verified against the cited literature.
- ``review_status=PENDING`` — cases with a legitimate source whose exact
  numeric value still needs full-text verification.
- ``review_status=REJECTED`` — everything else, kept here with an explicit
  ``rejection_reason`` so the audit trail is preserved and no downstream
  consumer can silently reuse contaminated data.

Training/evaluation code must use ``load_verified_cases()`` (ACCEPTED only).
``load_golden_cases()`` returns the full inventory for auditing.
"""

from __future__ import annotations

from psf_reasoner.datasets.schemas import (
    AssayType,
    DataQuality,
    EffectDirection,
    MutationLigandPair,
    ReviewStatus,
)

_HIV = "HIV-1 Protease"
_HIV_ACC = "P03367"
_DHFR = "Human Dihydrofolate Reductase"
_DHFR_ACC = "P00374"
_EGFR = "EGFR Kinase"
_EGFR_ACC = "P00533"
_ABL = "ABL1 Kinase"
_ABL_ACC = "P00519"
_BLAC = "TEM-1 Beta-lactamase"
_BLAC_ACC = "P62593"
_TRYP = "Bovine Trypsin"
_TRYP_ACC = "P00760"
_MPRO = "SARS-CoV-2 Mpro"
_MPRO_ACC = "P0DTD1"
_NEUR = "Influenza Neuraminidase"
_NEUR_ACC = "P03468"


def _case(
    sample_id: str,
    accession: str,
    protein_name: str,
    organism: str,
    notation: str,
    position: int,
    ligand_id: str,
    ligand_name: str,
    *,
    assay_type: AssayType,
    wt_value: float | None = None,
    mutant_value: float | None = None,
    value_unit: str = "",
    effect_direction: EffectDirection = EffectDirection.UNKNOWN,
    wt_pdb: str = "",
    mutant_pdb: str = "",
    background_mutations: list[str] | None = None,
    pmid: str = "",
    doi: str = "",
    review_status: ReviewStatus = ReviewStatus.PENDING,
    review_notes: str = "",
    rejection_reason: str = "",
    data_quality: DataQuality = DataQuality.UNVERIFIED,
    experimental_method: str = "",
    chain: str = "A",
    delta_delta_g: float | None = None,
) -> MutationLigandPair:
    wt, _, mut = notation.partition("X")
    if not mut:  # "V82A" notation
        wt, mut = notation[0], notation[-1]
    return MutationLigandPair(
        sample_id=sample_id,
        protein_accession=accession,
        protein_name=protein_name,
        organism=organism,
        mutation_notation=notation,
        wt_residue=wt,
        mutant_residue=mut,
        uniprot_position=position,
        pdb_position=position,
        pdb_chain=chain,
        ligand_id=ligand_id,
        ligand_name=ligand_name,
        ligand_role="inhibitor",
        assay_type=assay_type,
        wt_value=wt_value,
        mutant_value=mutant_value,
        value_unit=value_unit,
        delta_delta_g=delta_delta_g,
        effect_direction=effect_direction,
        wt_pdb=wt_pdb,
        mutant_pdb=mutant_pdb,
        background_mutations=background_mutations or [],
        has_structure_pair=bool(wt_pdb and mutant_pdb),
        experimental_method=experimental_method,
        pmid=pmid,
        doi=doi,
        data_source="manual_curation",
        data_quality=data_quality,
        review_status=review_status,
        review_notes=review_notes,
        rejection_reason=rejection_reason,
        split_group=accession,
    )


def load_golden_cases() -> list[MutationLigandPair]:
    """Return the full case inventory: verified + pending + rejected.

    Use ``load_verified_cases()`` for training/evaluation data.
    """
    return [*_verified(), *_pending(), *_rejected()]


def load_verified_cases() -> list[MutationLigandPair]:
    """Return only cases whose source, direction, and values were verified."""
    return [c for c in load_golden_cases() if c.review_status == ReviewStatus.ACCEPTED]


# ===========================================================================
# Verified cases (ACCEPTED) — every PMID/DOI/direction verified on 2026-09-10
# ===========================================================================


def _verified() -> list[MutationLigandPair]:
    cases = [
        # HIV-1 protease V82A + indinavir (MK1): 3.3-fold Ki increase.
        # Mahalingam et al. 2004, Eur J Biochem 271:1516-24, abstract:
        # "The inhibition (Ki) of PR(V82A) ... was 3.3-fold".
        # Structure pair 1SDT/1SDV verified: 99-aa chains differ ONLY at
        # position 82 (V->A), both bound to MK1.  1SDT carries background
        # mutations Q7K/L33I/L63I/C67A/C95A relative to UniProt P03367.
        _case(
            "HIV_V82A_MK1",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "V82A",
            82,
            "MK1",
            "MK1 (L-735,524, indinavir)",
            assay_type=AssayType.KI,
            wt_value=1.0,
            mutant_value=3.3,
            value_unit="fold_Ki",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            wt_pdb="1sdt.cif",
            mutant_pdb="1sdv.cif",
            background_mutations=["Q7K", "L33I", "L63I", "C67A", "C95A"],
            pmid="15066177",
            doi="10.1111/j.1432-1033.2004.04060.x",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="fold verified from abstract; absolute Ki values (540->1810 pM) "
            "not yet verified (paywalled full text).",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # HIV-1 protease L90M + indinavir (MK1): 0.16-fold Ki (hypersusceptibility).
        # Same paper, same abstract.  Mutant structure 1SDU (L90M + MK1, 1.25 A).
        _case(
            "HIV_L90M_MK1",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "L90M",
            90,
            "MK1",
            "MK1 (L-735,524, indinavir)",
            assay_type=AssayType.KI,
            wt_value=1.0,
            mutant_value=0.16,
            value_unit="fold_Ki",
            effect_direction=EffectDirection.AFFINITY_INCREASE,
            wt_pdb="1sdt.cif",
            mutant_pdb="1sdu.cif",
            background_mutations=["Q7K", "L33I", "L63I", "C67A", "C95A"],
            pmid="15066177",
            doi="10.1111/j.1432-1033.2004.04060.x",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="fold verified from abstract; absolute Ki values not yet verified.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # HIV-1 protease G48V + saquinavir: 86-fold Ki increase.
        # Liu et al. 2008, J Mol Biol 381:102-15, Table 1 (0.42 -> 36 nM).
        _case(
            "HIV_G48V_SQV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "G48V",
            48,
            "SQV",
            "Saquinavir",
            assay_type=AssayType.KI,
            wt_value=0.42,
            mutant_value=36.0,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="18597780",
            doi="10.1016/j.jmb.2008.05.062",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="Table 1 values verified against PMC2754059.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # HIV-1 protease I50V + darunavir: 31-fold Ki increase.
        # Liu et al. 2008 Table 1 (0.58 -> 18 nM).
        _case(
            "HIV_I50V_DRV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "I50V",
            50,
            "DRV",
            "Darunavir",
            assay_type=AssayType.KI,
            wt_value=0.58,
            mutant_value=18.0,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="18597780",
            doi="10.1016/j.jmb.2008.05.062",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="Table 1 values verified against PMC2754059.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # HIV-1 protease I54V + saquinavir: 15-fold Ki increase.
        # Liu et al. 2008 Table 1 (0.42 -> 6 nM).
        _case(
            "HIV_I54V_SQV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "I54V",
            54,
            "SQV",
            "Saquinavir",
            assay_type=AssayType.KI,
            wt_value=0.42,
            mutant_value=6.0,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="18597780",
            doi="10.1016/j.jmb.2008.05.062",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="Table 1 values verified against PMC2754059.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # HIV-1 protease I54M + saquinavir: 5-fold Ki increase.
        # Liu et al. 2008 Table 1 (0.42 -> 2.2 nM).
        _case(
            "HIV_I54M_SQV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "I54M",
            54,
            "SQV",
            "Saquinavir",
            assay_type=AssayType.KI,
            wt_value=0.42,
            mutant_value=2.2,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="18597780",
            doi="10.1016/j.jmb.2008.05.062",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="Table 1 values verified against PMC2754059.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # HIV-1 protease D30N + nelfinavir: 2-6-fold Ki increase (NFV greatest).
        # Clemente et al. 2003, Biochemistry 42:15029-35, abstract.
        _case(
            "HIV_D30N_NFV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "D30N",
            30,
            "NFV",
            "Nelfinavir",
            assay_type=AssayType.KI,
            wt_value=1.0,
            mutant_value=6.0,
            value_unit="fold_Ki",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="14690411",
            doi="10.1021/bi035701y",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="abstract reports a 2-6 fold range across inhibitors with "
            "nelfinavir greatest; 6.0 recorded as the nelfinavir upper bound.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # Human DHFR L22F + methotrexate: 88-fold MTX Ki increase.
        # Ercikan-Abali et al. 1996, Mol Pharmacol 49:430-7.
        _case(
            "DHFR_L22F_MTX",
            _DHFR_ACC,
            _DHFR,
            "Homo sapiens",
            "L22F",
            22,
            "MTX",
            "Methotrexate",
            assay_type=AssayType.KI,
            wt_value=1.0,
            mutant_value=88.0,
            value_unit="fold_Ki",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            wt_pdb="1u72.pdb",
            pmid="8643082",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="88-fold from the abstract (Ki); full-text table pending.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
        # Human DHFR F31R + methotrexate: delta-delta-G 2.1 kcal/mol (35-fold).
        # Volpato et al. 2009, J Biol Chem 284:20079-89, PMC2740434 Table 2.
        _case(
            "DHFR_F31R_MTX",
            _DHFR_ACC,
            _DHFR,
            "Homo sapiens",
            "F31R",
            31,
            "MTX",
            "Methotrexate",
            assay_type=AssayType.DELTA_G,
            wt_value=0.0,
            mutant_value=2.1,
            value_unit="kcal/mol",
            delta_delta_g=2.1,
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            wt_pdb="1u72.pdb",
            pmid="19478082",
            review_status=ReviewStatus.ACCEPTED,
            review_notes="delta-delta-G 2.1 kcal/mol read from PMC2740434 Table 2.",
            data_quality=DataQuality.CURATED,
            experimental_method="in vitro purified enzyme",
        ),
    ]
    return cases


# ===========================================================================
# Pending cases — legitimate source identified, exact value needs full text
# ===========================================================================


def _pending() -> list[MutationLigandPair]:
    cases = [
        # Mahalingam et al. 1999, Eur J Biochem 263:238-45 — abstract covers
        # catalytic activity only; SQV Ki fold values need the full-text Table II.
        _case(
            "HIV_L90M_SQV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "L90M",
            90,
            "SQV",
            "Saquinavir",
            assay_type=AssayType.KI,
            wt_value=0.033,
            mutant_value=0.68,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="10429209",
            doi="10.1046/j.1432-1327.1999.00514.x",
            review_status=ReviewStatus.PENDING,
            review_notes="Table II values not yet verified against full text.",
            data_quality=DataQuality.UNVERIFIED,
        ),
        _case(
            "HIV_G48V_SQV_MAHALINGAM1999",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "G48V",
            48,
            "SQV",
            "Saquinavir",
            assay_type=AssayType.KI,
            wt_value=0.033,
            mutant_value=5.4,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="10429209",
            doi="10.1046/j.1432-1327.1999.00514.x",
            review_status=ReviewStatus.PENDING,
            review_notes="Table II values not yet verified against full text.",
            data_quality=DataQuality.UNVERIFIED,
        ),
        _case(
            "HIV_G48V_L90M_SQV",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "G48V+L90M",
            48,
            "SQV",
            "Saquinavir",
            assay_type=AssayType.KI,
            wt_value=0.033,
            mutant_value=33.0,
            value_unit="nM",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="10429209",
            doi="10.1046/j.1432-1327.1999.00514.x",
            review_status=ReviewStatus.PENDING,
            review_notes="double-mutant Ki; Table II values not yet verified.",
            data_quality=DataQuality.UNVERIFIED,
        ),
        # Structure pair 1U72/1DLS verified (L22Y + MTX); the exact numeric
        # effect on MTX binding still needs a full-text table.
        _case(
            "DHFR_L22Y_MTX",
            _DHFR_ACC,
            _DHFR,
            "Homo sapiens",
            "L22Y",
            22,
            "MTX",
            "Methotrexate",
            assay_type=AssayType.KI,
            wt_value=None,
            mutant_value=None,
            value_unit="",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            wt_pdb="1u72.pdb",
            mutant_pdb="1dls.pdb",
            pmid="7890613",
            review_status=ReviewStatus.PENDING,
            review_notes="structure pair verified (1U72 WT / 1DLS L22Y, both + MTX); "
            "numeric binding value pending full-text verification.",
            data_quality=DataQuality.UNVERIFIED,
        ),
        # EGFR C797S + gefitinib: source corrected to Thress et al. 2015
        # (Nat Med 21:560-2); the 80-fold figure itself still needs the
        # full text.
        _case(
            "EGFR_C797S_IRE",
            _EGFR_ACC,
            _EGFR,
            "Homo sapiens",
            "C797S",
            797,
            "IRE",
            "Gefitinib",
            assay_type=AssayType.KI,
            wt_value=None,
            mutant_value=None,
            value_unit="",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            pmid="25939061",
            review_status=ReviewStatus.PENDING,
            review_notes="source corrected to PMID 25939061 (Thress 2015); "
            "numeric fold pending full-text verification.",
            data_quality=DataQuality.UNVERIFIED,
        ),
    ]
    return cases


# ===========================================================================
# Rejected cases — kept for the audit trail, must never enter training
# ===========================================================================


def _rejected() -> list[MutationLigandPair]:
    rejected: list[MutationLigandPair] = []

    def add(
        sample_id: str,
        notation: str,
        position: int,
        ligand: str,
        lname: str,
        accession: str,
        protein: str,
        organism: str,
        reason: str,
        wt_pdb: str = "",
    ) -> None:
        rejected.append(
            _case(
                sample_id,
                accession,
                protein,
                organism,
                notation,
                position,
                ligand,
                lname,
                assay_type=AssayType.KI,
                wt_value=None,
                mutant_value=None,
                value_unit="",
                wt_pdb=wt_pdb,
                review_status=ReviewStatus.REJECTED,
                rejection_reason=reason,
            )
        )

    # --- HIV-1 protease: cited PMIDs unrelated to the claims --------------
    _hiv_wrong = [
        (
            "HIV_V82A_DRV",
            "V82A",
            82,
            "DRV",
            "Darunavir",
            "PMID 12730686 is cyclophilin A; structure ligand (MK1) != assay ligand",
        ),
        (
            "HIV_I84V_DRV",
            "I84V",
            84,
            "DRV",
            "Darunavir",
            "PMID 15632378 is CYP2D6/tamoxifen; single-I84V Ki source not found",
        ),
        ("HIV_I50V_APV", "I50V", 50, "APV", "Amprenavir", "PMID 10681379 unrelated (cocaine metabolites)"),
        ("HIV_D30N_NFV_OLD", "D30N", 30, "NFV", "Nelfinavir", "PMID 9149701 unrelated (prostacyclin)"),
        ("HIV_G48V_SQV_OLD", "G48V", 48, "SQV", "Saquinavir", "PMID 7540751 unrelated (nursing humanities)"),
        ("HIV_L90M_SQV_OLD", "L90M", 90, "SQV", "Saquinavir", "PMID 7540751 unrelated (nursing humanities)"),
        ("HIV_I54V_IDV", "I54V", 54, "IDV", "Indinavir", "PMID 8810284 unrelated (chick collagen)"),
        ("HIV_I54M_IDV", "I54M", 54, "IDV", "Indinavir", "PMID 8810284 unrelated (chick collagen)"),
        ("HIV_V32I_IDV", "V32I", 32, "IDV", "Indinavir", "PMID 8810284 unrelated (chick collagen)"),
        ("HIV_M46I_IDV", "M46I", 46, "IDV", "Indinavir", "PMID 8810284 unrelated (chick collagen)"),
        (
            "HIV_N88S_IDV",
            "N88S",
            88,
            "IDV",
            "Indinavir",
            "PMID 11502742 unrelated (occludin); N88S hypersensitivity is documented for "
            "amprenavir, not indinavir",
        ),
        ("HIV_K20I_IDV", "K20I", 20, "IDV", "Indinavir", "PMID 11502742 unrelated (occludin)"),
        ("HIV_L63P_IDV", "L63P", 63, "IDV", "Indinavir", "PMID 11095614 unrelated (corneal MMP)"),
        ("HIV_I93L_IDV", "I93L", 93, "IDV", "Indinavir", "PMID 11095614 unrelated (corneal MMP)"),
    ]
    for sid, notation, pos, lig, lname, reason in _hiv_wrong:
        add(
            sid,
            notation,
            pos,
            lig,
            lname,
            _HIV_ACC,
            _HIV,
            "HIV-1",
            reason,
            wt_pdb="1sdt.cif" if sid != "HIV_D30N_NFV_OLD" else "",
        )

    # --- HIV-1 protease bulk fill (fabricated 1.1-1.3x folds) -------------
    for notation, pos in [
        ("V11I", 11),
        ("T12S", 12),
        ("I15V", 15),
        ("E35D", 35),
        ("S37N", 37),
        ("R41K", 41),
        ("K55R", 55),
        ("Q61E", 61),
        ("I72V", 72),
        ("T74S", 74),
    ]:
        add(
            f"HIV_{notation}_MK1",
            notation,
            pos,
            "MK1",
            "MK1 inhibitor",
            _HIV_ACC,
            _HIV,
            "HIV-1",
            "bulk quota-fill row; PMID 11095614 unrelated; fold value fabricated",
            wt_pdb="1sdt.cif",
        )

    # --- DHFR: wrong PMIDs and fabricated values --------------------------
    _dhfr_wrong = [
        ("DHFR_S118A_MTX", "S118A", 118, "PMID 11527979 unrelated (Wilson ATPase chimeras)"),
        ("DHFR_G116A_MTX", "G116A", 116, "PMID 11527979 unrelated"),
        (
            "DHFR_Q35E_MTX",
            "Q35E",
            35,
            "PMID 11258910 unrelated; Volpato 2009 reports Q35E = affinity "
            "DECREASE (1.5x), opposite of recorded",
        ),
        ("DHFR_E30A_MTX", "E30A", 30, "PMID 11527979 unrelated"),
        ("DHFR_F31S_MTX", "F31S", 31, "PMID 11258910 unrelated; F31S value not found in literature"),
    ]
    for sid, notation, pos, reason in _dhfr_wrong:
        add(
            sid,
            notation,
            pos,
            "MTX",
            "Methotrexate",
            _DHFR_ACC,
            _DHFR,
            "Homo sapiens",
            reason,
            wt_pdb="1u72.pdb",
        )
    for notation, pos in [
        ("I7V", 7),
        ("V8A", 8),
        ("L13I", 13),
        ("R28K", 28),
        ("K55R", 55),
        ("T56S", 56),
        ("V115I", 115),
        ("D21N", 21),
    ]:
        add(
            f"DHFR_{notation}_MTX",
            notation,
            pos,
            "MTX",
            "Methotrexate",
            _DHFR_ACC,
            _DHFR,
            "Homo sapiens",
            "bulk quota-fill row; PMID 11527979 unrelated; fold value fabricated",
            wt_pdb="1u72.pdb",
        )

    # --- TEM-1 beta-lactamase: 1btl.pdb has no ligand; PMIDs unrelated ----
    for sid, notation, pos in [
        ("BLAC_S70A_PEN", "S70A", 70),
        ("BLAC_S130A_PEN", "S130A", 130),
        ("BLAC_E166A_PEN", "E166A", 166),
        ("BLAC_K73A_PEN", "K73A", 73),
        ("BLAC_E104A_PEN", "E104A", 104),
    ]:
        add(
            sid,
            notation,
            pos,
            "PEN",
            "Penicillin G",
            _BLAC_ACC,
            _BLAC,
            "Escherichia coli",
            "PMID 2205042 unrelated (pig parasites); structure 1btl.pdb contains no ligand; "
            "catalytic-residue alanine mutants do not increase substrate affinity",
            wt_pdb="1btl.pdb",
        )
    for sid, notation, pos, reason in [
        ("BLAC_G238S_PEN", "G238S", 238, "PMID 16189104 studies AmpC, not TEM-1"),
        ("BLAC_R244S_PEN", "R244S", 244, "PMID 16189104 studies AmpC, not TEM-1"),
        ("BLAC_A237G_PEN", "A237G", 237, "PMID 16189104 studies AmpC, not TEM-1"),
    ]:
        add(
            sid,
            notation,
            pos,
            "PEN",
            "Penicillin G",
            _BLAC_ACC,
            _BLAC,
            "Escherichia coli",
            reason,
            wt_pdb="1btl.pdb",
        )
    for notation, pos in [
        ("T114A", 114),
        ("D115N", 115),
        ("N132A", 132),
        ("T181A", 181),
        ("D179N", 179),
        ("R161A", 161),
        ("D214N", 214),
        ("T265A", 265),
    ]:
        add(
            f"BLAC_{notation}_PEN",
            notation,
            pos,
            "PEN",
            "Penicillin G",
            _BLAC_ACC,
            _BLAC,
            "Escherichia coli",
            "bulk quota-fill row; PMID 16189104 unrelated; structure has no ligand",
            wt_pdb="1btl.pdb",
        )

    # --- Trypsin: single wrong PMID covers all 16 -------------------------
    _tryp_mutations = [
        ("D189S", 189),
        ("G193A", 193),
        ("S195A", 195),
        ("G216A", 216),
        ("G226A", 226),
        ("K60A", 60),
        ("H57A", 57),
        ("D102N", 102),
        ("Y39F", 39),
        ("F41Y", 41),
        ("C42A", 42),
        ("H57N", 57),
        ("Y94F", 94),
        ("L99I", 99),
        ("N143A", 143),
        ("V213I", 213),
    ]
    for notation, pos in _tryp_mutations:
        add(
            f"TRYP_{notation}_BEN",
            notation,
            pos,
            "BEN",
            "Benzamidine",
            _TRYP_ACC,
            _TRYP,
            "Bos taurus",
            "PMID 3131872 unrelated (German oxygen-therapy review); fold values fabricated",
            wt_pdb="3ptb.pdb",
        )

    # --- SARS-CoV-2 Mpro: ligand N3 != nirmatrelvir, PMID is PLpro paper --
    _mpro_mutations = [
        ("H41A", 41),
        ("C145A", 145),
        ("E166A", 166),
        ("Q189A", 189),
        ("T25A", 25),
        ("N142A", 142),
        ("G143A", 143),
        ("S144A", 144),
        ("M49A", 49),
        ("L50A", 50),
        ("F140A", 140),
        ("N142L", 142),
        ("E166Q", 166),
        ("D187N", 187),
        ("R188K", 188),
        ("T190A", 190),
    ]
    for notation, pos in _mpro_mutations:
        add(
            f"MPRO_{notation}_NIR",
            notation,
            pos,
            "NIR",
            "Nirmatrelvir",
            _MPRO_ACC,
            _MPRO,
            "SARS-CoV-2",
            "PMID 32726803 is a PLpro (not Mpro) paper; 6lu7.pdb ligand is N3, "
            "not nirmatrelvir; 'NIR' is a wrong CCD code; fold values fabricated",
            wt_pdb="6lu7.pdb",
        )

    # --- Influenza neuraminidase: mixed subtypes/accessions, wrong CCD ----
    _neur_mutations = [
        ("H275Y", 275),
        ("E119V", 119),
        ("R292K", 292),
        ("N294S", 294),
        ("I223R", 223),
        ("V116A", 116),
        ("D151N", 151),
        ("R152K", 152),
        ("Y155F", 155),
        ("W178A", 178),
        ("S179A", 179),
        ("E227D", 227),
        ("R371K", 371),
    ]
    for notation, pos in _neur_mutations:
        add(
            f"NEUR_{notation}_OSL",
            notation,
            pos,
            "OSL",
            "Oseltamivir",
            _NEUR_ACC,
            _NEUR,
            "Influenza A virus",
            "PMID 16954204 unrelated (Derlin-1/CFTR); 2hu4.pdb is an engineered "
            "H5N1 N1 (H233Y/H252Y, accession Q6DPL2, not P03468) and does NOT "
            "contain H275Y; 'OSL' is a wrong CCD code; fold values fabricated",
            wt_pdb="2hu4.pdb",
        )

    # --- EGFR / ABL1: real-but-unsupporting PMIDs, values without source --
    _egfr_mutations = [
        ("T790M", 790, "IRE", "Gefitinib", "Lynch 2004 reports sensitizing mutations; T790M not in it"),
        ("T790M", 790, "ERL", "Erlotinib", "Lynch 2004 reports sensitizing mutations; T790M not in it"),
        ("L858R", 858, "IRE", "Gefitinib", "Lynch 2004 has no fold table; value without source"),
        ("G719S", 719, "IRE", "Gefitinib", "Lynch 2004 has no fold table; value without source"),
        ("V765M", 765, "IRE", "Gefitinib", "no literature source for V765M fold"),
    ]
    for notation, pos, lig, lname, reason in _egfr_mutations:
        add(f"EGFR_{notation}_{lig}", notation, pos, lig, lname, _EGFR_ACC, _EGFR, "Homo sapiens", reason)

    _abl_mutations = [
        ("T315I", 315, 100.0),
        ("E255K", 255, 30.0),
        ("F317L", 317, 15.0),
        ("Y253H", 253, 20.0),
        ("M351T", 351, 3.0),
        ("E255V", 255, 25.0),
        ("H396P", 396, 4.0),
        ("L248V", 248, 1.5),
        ("G250E", 250, 2.0),
        ("Q252H", 252, 8.0),
    ]
    for notation, pos, _fold in _abl_mutations:
        add(
            f"ABL1_{notation}_STI",
            notation,
            pos,
            "STI",
            "Imatinib",
            _ABL_ACC,
            _ABL,
            "Homo sapiens",
            "PMID 11964322 is a patient mutation survey with no fold values; recorded folds have no source",
        )

    return rejected


def get_dataset_summary() -> dict:
    """Return a summary of the case inventory by review status."""
    cases = load_golden_cases()
    proteins: dict[str, int] = {}
    directions: dict[str, int] = {}
    statuses: dict[str, int] = {}
    has_structure = 0
    for c in cases:
        proteins[c.protein_name] = proteins.get(c.protein_name, 0) + 1
        directions[c.effect_direction.value] = directions.get(c.effect_direction.value, 0) + 1
        statuses[c.review_status.value] = statuses.get(c.review_status.value, 0) + 1
        if c.wt_pdb and c.mutant_pdb:
            has_structure += 1

    return {
        "total": len(cases),
        "review_statuses": statuses,
        "verified": statuses.get("accepted", 0),
        "proteins": proteins,
        "effect_directions": directions,
        "has_structure_pair": has_structure,
        "data_quality": {
            "curated": sum(1 for c in cases if c.data_quality.value == "curated"),
            "reported": sum(1 for c in cases if c.data_quality.value == "reported"),
            "unverified": sum(1 for c in cases if c.data_quality.value == "unverified"),
        },
    }
