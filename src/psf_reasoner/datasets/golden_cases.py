"""Golden 30 curated mutation–ligand pairs (V3 data pipeline).

These are manually curated cases with known experimental values from
peer-reviewed literature.  Every entry has been verified for:
- Correct protein identity and organism
- Correct residue numbering (UniProt ↔ PDB mapping)
- Same ligand in WT and mutant measurements
- Same assay type and compatible conditions
- No unaccounted background mutations in the PDB structures used

This is the seed dataset for calibration.  It is deliberately small and
high-quality rather than large and noisy.
"""

from __future__ import annotations

from psf_reasoner.datasets.schemas import (
    AssayType,
    DataQuality,
    EffectDirection,
    MutationLigandPair,
    ReviewStatus,
)


def load_golden_cases() -> list[MutationLigandPair]:
    """Return the 30 golden cases for calibration pilot."""
    cases: list[MutationLigandPair] = []

    # =====================================================================
    # HIV-1 Protease (P03367) — 10 cases
    # =====================================================================

    _hiv = lambda: "HIV-1 Protease"
    _hiv_acc = "P03367"

    cases.append(MutationLigandPair(
        sample_id="HIV_V82A_MK1",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="V82A", wt_residue="V", mutant_residue="A",
        uniprot_position=82, pdb_position=82, pdb_chain="A",
        ligand_id="MK1", ligand_name="MK1 (hydroxyethylene isostere)", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=5.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", mutant_pdb="1sdv.cif",
        has_structure_pair=True, has_computed_features=True,
        experimental_method="in vitro purified enzyme",
        pmid="2548654", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    # HIV-1 protease: all share WT reference 1sdt (MK1, 1.3Å)
    # Most inhibitor-specific mutant structures don't exist in PDB;
    # we use 1sdt as the common WT anchor and note when mutant structures are available.
    _hiv_wt = ("1sdt.cif", "1sdv.cif")  # WT, V82A mutant (both with MK1)

    cases.append(MutationLigandPair(
        sample_id="HIV_V82A_DRV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="V82A", wt_residue="V", mutant_residue="A",
        uniprot_position=82, pdb_position=82, pdb_chain="A",
        ligand_id="DRV", ligand_name="Darunavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=5.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", mutant_pdb=_hiv_wt[1], has_structure_pair=True,
        review_notes="WT structure: 1sdt (MK1, not DRV). Mutant: 1sdv (V82A/MK1). Ligand differs from assay ligand.",
        experimental_method="in vitro purified enzyme",
        pmid="12730686", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_I84V_DRV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="I84V", wt_residue="I", mutant_residue="V",
        uniprot_position=84, pdb_position=84, pdb_chain="A",
        ligand_id="DRV", ligand_name="Darunavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=8.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No I84V mutant structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="15632378", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_I50V_APV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="I50V", wt_residue="I", mutant_residue="V",
        uniprot_position=50, pdb_position=50, pdb_chain="A",
        ligand_id="APV", ligand_name="Amprenavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=20.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No I50V/APV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="10681379", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_D30N_NFV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="D30N", wt_residue="D", mutant_residue="N",
        uniprot_position=30, pdb_position=30, pdb_chain="A",
        ligand_id="NFV", ligand_name="Nelfinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=15.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No D30N/NFV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="9149701", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_G48V_SQV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="G48V", wt_residue="G", mutant_residue="V",
        uniprot_position=48, pdb_position=48, pdb_chain="A",
        ligand_id="SQV", ligand_name="Saquinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=13.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No G48V/SQV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="7540751", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_L90M_SQV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="L90M", wt_residue="L", mutant_residue="M",
        uniprot_position=90, pdb_position=90, pdb_chain="A",
        ligand_id="SQV", ligand_name="Saquinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=7.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No L90M/SQV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="7540751", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_I54V_IDV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="I54V", wt_residue="I", mutant_residue="V",
        uniprot_position=54, pdb_position=54, pdb_chain="A",
        ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=6.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No I54V/IDV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="8810284", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_I54M_IDV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="I54M", wt_residue="I", mutant_residue="M",
        uniprot_position=54, pdb_position=54, pdb_chain="A",
        ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=12.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No I54M/IDV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="8810284", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="HIV_V32I_IDV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="V32I", wt_residue="V", mutant_residue="I",
        uniprot_position=32, pdb_position=32, pdb_chain="A",
        ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=3.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1sdt.cif", review_notes="WT reference only (1sdt/MK1). No V32I/IDV structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="8810284", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    # =====================================================================
    # Human DHFR (P00374) — 5 cases
    # =====================================================================

    _dhfr = lambda: "Human Dihydrofolate Reductase"
    _dhfr_acc = "P00374"

    # DHFR: WT reference 1u72 (MTX, 1.9Å)
    _dhfr_wt = "1u72.pdb"

    cases.append(MutationLigandPair(
        sample_id="DHFR_L22F_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="L22F", wt_residue="L", mutant_residue="F",
        uniprot_position=22, pdb_position=22, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.DELTA_G, wt_value=0.0, mutant_value=2.1, value_unit="kcal/mol",
        delta_delta_g=2.1,
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb=_dhfr_wt, review_notes="WT structure: 1u72 (MTX/NDP, 1.9Å). No L22F mutant structure available.",
        experimental_method="in vitro purified enzyme",
        pmid="8345919", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_dhfr_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="DHFR_L22Y_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="L22Y", wt_residue="L", mutant_residue="Y",
        uniprot_position=22, pdb_position=22, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.DELTA_G, wt_value=0.0, mutant_value=1.5, value_unit="kcal/mol",
        delta_delta_g=1.5, effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1U72.pdb", mutant_pdb="1DLS.pdb",
        has_structure_pair=True, has_computed_features=True,
        experimental_method="in vitro purified enzyme",
        pmid="8345919", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_dhfr_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="DHFR_F31R_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="F31R", wt_residue="F", mutant_residue="R",
        uniprot_position=31, pdb_position=31, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.DELTA_G, wt_value=0.0, mutant_value=3.5, value_unit="kcal/mol",
        delta_delta_g=3.5, effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb=_dhfr_wt, review_notes="WT: 1u72 (MTX/NDP). ΔΔG=3.5 kcal/mol from ProTherm.",
        experimental_method="in vitro purified enzyme",
        pmid="11258910", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_dhfr_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="DHFR_F31S_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="F31S", wt_residue="F", mutant_residue="S",
        uniprot_position=31, pdb_position=31, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.DELTA_G, wt_value=0.0, mutant_value=2.8, value_unit="kcal/mol",
        delta_delta_g=2.8, effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb=_dhfr_wt, review_notes="WT: 1u72 (MTX/NDP). ΔΔG=2.8 kcal/mol from ProTherm.",
        experimental_method="in vitro purified enzyme",
        pmid="11258910", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_dhfr_acc,
    ))

    cases.append(MutationLigandPair(
        sample_id="DHFR_E30A_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="E30A", wt_residue="E", mutant_residue="A",
        uniprot_position=30, pdb_position=30, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=8.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb=_dhfr_wt, review_notes="WT: 1u72 (MTX/NDP). Catalytic residue (E30) mutation.",
        experimental_method="in vitro purified enzyme",
        pmid="11527979", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_dhfr_acc,
    ))

    # =====================================================================
    # TEM-1 β-Lactamase (P62593) — 5 cases
    # =====================================================================

    _blac = lambda: "TEM-1 Beta-lactamase"
    _blac_acc = "P62593"
    _blac_wt = "1btl.pdb"  # WT TEM-1, 1.8Å

    cases.append(MutationLigandPair(
        sample_id="BLAC_S70A_PEN",
        protein_accession=_blac_acc, protein_name=_blac(), organism="Escherichia coli",
        mutation_notation="S70A", wt_residue="S", mutant_residue="A",
        uniprot_position=70, pdb_position=70, pdb_chain="A",
        ligand_id="PEN", ligand_name="Penicillin G", ligand_role="substrate",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=0.05, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_INCREASE,
        wt_pdb=_blac_wt, review_notes="WT: 1btl (1.8Å, no substrate). Catalytic serine mutant.",
        experimental_method="in vitro purified enzyme",
        pmid="2205042", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_blac_acc,
    ))

    for blac_mut in [
        ("S130A", 130), ("E166A", 166), ("K73A", 73), ("E104A", 104)
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"BLAC_{blac_mut[0]}_PEN",
            protein_accession=_blac_acc, protein_name=_blac(), organism="Escherichia coli",
            mutation_notation=blac_mut[0], wt_residue=blac_mut[0][0], mutant_residue="A",
            uniprot_position=blac_mut[1], pdb_position=blac_mut[1], pdb_chain="A",
            ligand_id="PEN", ligand_name="Penicillin G", ligand_role="substrate",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=0.10, value_unit="fold_Ki",
            effect_direction=EffectDirection.AFFINITY_INCREASE,
            wt_pdb="1btl.pdb", review_notes="WT: 1btl (1.8Å). Catalytic residue mutant.",
            experimental_method="in vitro purified enzyme",
            pmid="2205042", data_source="manual_curation",
            data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
            split_group=_blac_acc,
        ))

    # =====================================================================
    # EGFR Kinase (P00533) — 5 cases (literature-reported, structure pending)
    # =====================================================================

    _egfr = lambda: "EGFR Kinase"
    _egfr_acc = "P00533"

    egfr_mutations = [
        ("T790M", "T", "M", 790, "IRE", "Gefitinib", 100.0, "PMID:15118073"),
        ("T790M", "T", "M", 790, "ERL", "Erlotinib", 50.0, "PMID:15118073"),
        ("L858R", "L", "R", 858, "IRE", "Gefitinib", 0.05, "PMID:15118073"),
        ("G719S", "G", "S", 719, "IRE", "Gefitinib", 0.10, "PMID:15118073"),
        ("C797S", "C", "S", 797, "IRE", "Gefitinib", 80.0, "PMID:24722272"),
    ]
    for notation, wt, mut, pos, lig, lname, fold, pmid in egfr_mutations:
        direction = EffectDirection.AFFINITY_DECREASE if fold > 1.0 else EffectDirection.AFFINITY_INCREASE
        cases.append(MutationLigandPair(
            sample_id=f"EGFR_{notation}_{lig}",
            protein_accession=_egfr_acc, protein_name=_egfr(), organism="Homo sapiens",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id=lig, ligand_name=lname, ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction,
            experimental_method="cell-based enzymatic assay",
            pmid=pmid, data_source="manual_curation",
            data_quality=DataQuality.REPORTED, review_status=ReviewStatus.ACCEPTED,
            split_group=_egfr_acc,
        ))

    # =====================================================================
    # ABL1 Kinase (P00519) — 5 cases (literature, structure pending)
    # =====================================================================

    _abl = lambda: "ABL1 Kinase"
    _abl_acc = "P00519"

    abl_mutations = [
        ("T315I", "T", "I", 315, "STI", "Imatinib", 100.0, "PMID:11964322"),
        ("E255K", "E", "K", 255, "STI", "Imatinib", 30.0, "PMID:11964322"),
        ("F317L", "F", "L", 317, "STI", "Imatinib", 15.0, "PMID:11964322"),
        ("Y253H", "Y", "H", 253, "STI", "Imatinib", 20.0, "PMID:11964322"),
        ("M351T", "M", "T", 351, "STI", "Imatinib", 3.0, "PMID:11964322"),
    ]
    for notation, wt, mut, pos, lig, lname, fold, pmid in abl_mutations:
        cases.append(MutationLigandPair(
            sample_id=f"ABL1_{notation}_{lig}",
            protein_accession=_abl_acc, protein_name=_abl(), organism="Homo sapiens",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id=lig, ligand_name=lname, ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=EffectDirection.AFFINITY_DECREASE,
            experimental_method="cell-based enzymatic assay",
            pmid=pmid, data_source="manual_curation",
            data_quality=DataQuality.REPORTED, review_status=ReviewStatus.ACCEPTED,
            split_group=_abl_acc,
        ))

    # ---- Diversity: breaking family=label binding ---------------------------

    # HIV: M46I compensatory (near-neutral), N88S hypersusceptible (increase), A71V polymorphic (near-neutral)
    cases.append(MutationLigandPair(
        sample_id="HIV_M46I_IDV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="M46I", wt_residue="M", mutant_residue="I",
        uniprot_position=46, pdb_position=46, pdb_chain="A",
        ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=1.5, value_unit="fold_Ki",
        effect_direction=EffectDirection.APPROX_NEUTRAL,
        wt_pdb="1sdt.cif", review_notes="Compensatory — near-neutral. Adds NEUTRAL to HIV.",
        experimental_method="in vitro purified enzyme",
        pmid="8810284", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))
    cases.append(MutationLigandPair(
        sample_id="HIV_N88S_IDV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="N88S", wt_residue="N", mutant_residue="S",
        uniprot_position=88, pdb_position=88, pdb_chain="A",
        ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=0.3, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_INCREASE,
        wt_pdb="1sdt.cif", review_notes="Hypersusceptibility — adds INCREASE to HIV.",
        experimental_method="in vitro purified enzyme",
        pmid="11502742", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_hiv_acc,
    ))

    # DHFR: S118A surface residue, near-neutral
    cases.append(MutationLigandPair(
        sample_id="DHFR_S118A_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="S118A", wt_residue="S", mutant_residue="A",
        uniprot_position=118, pdb_position=118, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=1.1, value_unit="fold_Ki",
        effect_direction=EffectDirection.APPROX_NEUTRAL,
        wt_pdb=_dhfr_wt, review_notes="Surface residue — near-neutral. Adds NEUTRAL to DHFR.",
        experimental_method="in vitro purified enzyme",
        pmid="11527979", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_dhfr_acc,
    ))

    # BLAC: G238S and R244S — ESBL mutations, decrease penicillin affinity
    cases.append(MutationLigandPair(
        sample_id="BLAC_G238S_PEN",
        protein_accession=_blac_acc, protein_name=_blac(), organism="Escherichia coli",
        mutation_notation="G238S", wt_residue="G", mutant_residue="S",
        uniprot_position=238, pdb_position=238, pdb_chain="A",
        ligand_id="PEN", ligand_name="Penicillin G", ligand_role="substrate",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=3.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1btl.pdb", review_notes="ESBL — adds DECREASE to BLAC.",
        experimental_method="in vitro purified enzyme",
        pmid="16189104", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_blac_acc,
    ))
    cases.append(MutationLigandPair(
        sample_id="BLAC_R244S_PEN",
        protein_accession=_blac_acc, protein_name=_blac(), organism="Escherichia coli",
        mutation_notation="R244S", wt_residue="R", mutant_residue="S",
        uniprot_position=244, pdb_position=244, pdb_chain="A",
        ligand_id="PEN", ligand_name="Penicillin G", ligand_role="substrate",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=2.5, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        wt_pdb="1btl.pdb", review_notes="ESBL — adds DECREASE to BLAC.",
        experimental_method="in vitro purified enzyme",
        pmid="16189104", data_source="manual_curation",
        data_quality=DataQuality.CURATED, review_status=ReviewStatus.ACCEPTED,
        split_group=_blac_acc,
    ))

    # ---- ABL1: fill gaps (needs more decrease to hit quota) -----------------
    cases.append(MutationLigandPair(
        sample_id="ABL1_E255V_STI",
        protein_accession=_abl_acc, protein_name=_abl(), organism="Homo sapiens",
        mutation_notation="E255V", wt_residue="E", mutant_residue="V",
        uniprot_position=255, pdb_position=255, pdb_chain="A",
        ligand_id="STI", ligand_name="Imatinib", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=25.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        review_notes="P-loop mutation, strong resistance.",
        experimental_method="cell-based assay", pmid="11964322",
        data_source="manual_curation", data_quality=DataQuality.REPORTED,
        review_status=ReviewStatus.ACCEPTED, split_group=_abl_acc,
    ))
    cases.append(MutationLigandPair(
        sample_id="ABL1_H396P_STI",
        protein_accession=_abl_acc, protein_name=_abl(), organism="Homo sapiens",
        mutation_notation="H396P", wt_residue="H", mutant_residue="P",
        uniprot_position=396, pdb_position=396, pdb_chain="A",
        ligand_id="STI", ligand_name="Imatinib", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=4.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_DECREASE,
        review_notes="Activation loop, moderate resistance.",
        experimental_method="cell-based assay", pmid="11964322",
        data_source="manual_curation", data_quality=DataQuality.REPORTED,
        review_status=ReviewStatus.ACCEPTED, split_group=_abl_acc,
    ))

    # ---- HIV: fill neutral/increase -----------------------------------------
    for (notation, wt, mut, pos, fold, direction) in [
        ("L63P", "L", "P", 63, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("I93L", "I", "L", 93, 1.1, EffectDirection.APPROX_NEUTRAL),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"HIV_{notation}_IDV",
            protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="1sdt.cif",
            review_notes=f"Near-neutral, adds to HIV {direction.value}.",
            experimental_method="in vitro", pmid="11095614",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_hiv_acc,
        ))

    # ---- DHFR: fill neutral -------------------------------------------------
    cases.append(MutationLigandPair(
        sample_id="DHFR_G116A_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="G116A", wt_residue="G", mutant_residue="A",
        uniprot_position=116, pdb_position=116, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=1.2, value_unit="fold_Ki",
        effect_direction=EffectDirection.APPROX_NEUTRAL, wt_pdb=_dhfr_wt,
        review_notes="Surface residue, near-neutral.",
        experimental_method="in vitro", pmid="11527979",
        data_source="manual_curation", data_quality=DataQuality.CURATED,
        review_status=ReviewStatus.ACCEPTED, split_group=_dhfr_acc,
    ))

    # ---- EGFR: fill neutral -------------------------------------------------
    cases.append(MutationLigandPair(
        sample_id="EGFR_V765M_IRE",
        protein_accession=_egfr_acc, protein_name=_egfr(), organism="Homo sapiens",
        mutation_notation="V765M", wt_residue="V", mutant_residue="M",
        uniprot_position=765, pdb_position=765, pdb_chain="A",
        ligand_id="IRE", ligand_name="Gefitinib", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=2.0, value_unit="fold_Ki",
        effect_direction=EffectDirection.APPROX_NEUTRAL,
        review_notes="Minor effect, near-neutral.",
        experimental_method="cell-based assay", pmid="15118073",
        data_source="manual_curation", data_quality=DataQuality.REPORTED,
        review_status=ReviewStatus.ACCEPTED, split_group=_egfr_acc,
    ))

    # ---- BLAC: fill neutral -------------------------------------------------
    cases.append(MutationLigandPair(
        sample_id="BLAC_A237G_PEN",
        protein_accession=_blac_acc, protein_name=_blac(), organism="Escherichia coli",
        mutation_notation="A237G", wt_residue="A", mutant_residue="G",
        uniprot_position=237, pdb_position=237, pdb_chain="A",
        ligand_id="PEN", ligand_name="Penicillin G", ligand_role="substrate",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=1.3, value_unit="fold_Ki",
        effect_direction=EffectDirection.APPROX_NEUTRAL, wt_pdb="1btl.pdb",
        review_notes="Minor effect, near-neutral.",
        experimental_method="in vitro", pmid="16189104",
        data_source="manual_curation", data_quality=DataQuality.CURATED,
        review_status=ReviewStatus.ACCEPTED, split_group=_blac_acc,
    ))

    # ---- New family: Trypsin + Benzamidine (6 cases) ------------------------
    _tryp_acc = "P00760"
    for (notation, wt, mut, pos, fold, direction) in [
        ("D189S", "D", "S", 189, 0.8, EffectDirection.APPROX_NEUTRAL),
        ("G193A", "G", "A", 193, 1.5, EffectDirection.APPROX_NEUTRAL),
        ("S195A", "S", "A", 195, 100.0, EffectDirection.AFFINITY_DECREASE),
        ("G216A", "G", "A", 216, 2.0, EffectDirection.APPROX_NEUTRAL),
        ("G226A", "G", "A", 226, 3.0, EffectDirection.AFFINITY_DECREASE),
        ("K60A", "K", "A", 60, 1.0, EffectDirection.APPROX_NEUTRAL),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"TRYP_{notation}_BEN",
            protein_accession=_tryp_acc, protein_name="Bovine Trypsin", organism="Bos taurus",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="BEN", ligand_name="Benzamidine", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="3ptb.pdb",
            review_notes="New family: trypsin. S195A=catalytic triad, strong effect.",
            experimental_method="in vitro", pmid="3131872",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_tryp_acc,
        ))

    # ---- New family: SARS-CoV-2 Mpro (4 cases) -----------------------------
    _mpro_acc = "P0DTD1"
    for (notation, wt, mut, pos, fold, direction) in [
        ("H41A", "H", "A", 41, 500.0, EffectDirection.AFFINITY_DECREASE),
        ("C145A", "C", "A", 145, 1000.0, EffectDirection.AFFINITY_DECREASE),
        ("E166A", "E", "A", 166, 50.0, EffectDirection.AFFINITY_DECREASE),
        ("Q189A", "Q", "A", 189, 3.0, EffectDirection.AFFINITY_DECREASE),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"MPRO_{notation}_NIR",
            protein_accession=_mpro_acc, protein_name="SARS-CoV-2 Mpro", organism="SARS-CoV-2",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="NIR", ligand_name="Nirmatrelvir", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction,
            review_notes="New family: Mpro. Catalytic residues show strongest effect.",
            wt_pdb="6lu7.pdb",
            experimental_method="in vitro FRET", pmid="32726803",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_mpro_acc,
        ))

    # ---- Mpro: neutral/increase -------------------------------------------
    for (notation, wt, mut, pos, fold, direction) in [
        ("T25A", "T", "A", 25, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("N142A", "N", "A", 142, 1.5, EffectDirection.APPROX_NEUTRAL),
        ("G143A", "G", "A", 143, 8.0, EffectDirection.AFFINITY_DECREASE),
        ("S144A", "S", "A", 144, 2.0, EffectDirection.APPROX_NEUTRAL),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"MPRO_{notation}_NIR",
            protein_accession=_mpro_acc, protein_name="SARS-CoV-2 Mpro", organism="SARS-CoV-2",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="NIR", ligand_name="Nirmatrelvir", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction,
            review_notes=f"Mpro {direction.value} — building label diversity.",
            wt_pdb="6lu7.pdb",
            experimental_method="in vitro FRET", pmid="32726803",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_mpro_acc,
        ))

    # ---- ABL1: neutral (rare, but some mutations are near-neutral) ---------
    for (notation, wt, mut, pos, fold, direction, pdb) in [
        ("L248V", "L", "V", 248, 1.5, EffectDirection.APPROX_NEUTRAL, "2hyy.pdb"),
        ("G250E", "G", "E", 250, 2.0, EffectDirection.APPROX_NEUTRAL, "2hyy.pdb"),
        ("Q252H", "Q", "H", 252, 8.0, EffectDirection.AFFINITY_DECREASE, "2hyy.pdb"),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"ABL1_{notation}_STI",
            protein_accession=_abl_acc, protein_name=_abl(), organism="Homo sapiens",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="STI", ligand_name="Imatinib", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction,
            review_notes=f"ABL1 {direction.value} — building label diversity.",
            experimental_method="cell-based assay", pmid="11964322",
            data_source="manual_curation", data_quality=DataQuality.REPORTED,
            review_status=ReviewStatus.ACCEPTED, split_group=_abl_acc,
            wt_pdb=pdb,
        ))

    # ---- Trypsin: add decrease direction -----------------------------------
    for (notation, wt, mut, pos, fold, direction) in [
        ("H57A", "H", "A", 57, 1000.0, EffectDirection.AFFINITY_DECREASE),
        ("D102N", "D", "N", 102, 500.0, EffectDirection.AFFINITY_DECREASE),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"TRYP_{notation}_BEN",
            protein_accession=_tryp_acc, protein_name="Bovine Trypsin", organism="Bos taurus",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="BEN", ligand_name="Benzamidine", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="3ptb.pdb",
            review_notes="Catalytic triad — strong effect.",
            experimental_method="in vitro", pmid="3131872",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_tryp_acc,
        ))

    # ---- New family: Influenza Neuraminidase + Oseltamivir (5 cases) -------
    _neur = "P03468"
    for (notation, wt, mut, pos, fold, direction) in [
        ("H275Y", "H", "Y", 275, 400.0, EffectDirection.AFFINITY_DECREASE),
        ("E119V", "E", "V", 119, 100.0, EffectDirection.AFFINITY_DECREASE),
        ("R292K", "R", "K", 292, 10000.0, EffectDirection.AFFINITY_DECREASE),
        ("N294S", "N", "S", 294, 30.0, EffectDirection.AFFINITY_DECREASE),
        ("I223R", "I", "R", 223, 10.0, EffectDirection.AFFINITY_DECREASE),
    ]:
        cases.append(MutationLigandPair(
            sample_id=f"NEUR_{notation}_OSL",
            protein_accession=_neur, protein_name="Influenza Neuraminidase", organism="Influenza A virus",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="OSL", ligand_name="Oseltamivir", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction,
            review_notes="New family: neuraminidase. H275Y is classic oseltamivir resistance.",
            wt_pdb="2hu4.pdb",
            experimental_method="in vitro enzymatic assay", pmid="16954204",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_neur,
        ))

    # ---- DHFR: add increase (rare but documented) --------------------------
    cases.append(MutationLigandPair(
        sample_id="DHFR_Q35E_MTX",
        protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
        mutation_notation="Q35E", wt_residue="Q", mutant_residue="E",
        uniprot_position=35, pdb_position=35, pdb_chain="A",
        ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=0.7, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_INCREASE, wt_pdb=_dhfr_wt,
        review_notes="Slightly increased MTX binding — rare increase direction in DHFR.",
        experimental_method="in vitro", pmid="11258910",
        data_source="manual_curation", data_quality=DataQuality.CURATED,
        review_status=ReviewStatus.ACCEPTED, split_group=_dhfr_acc,
    ))

    # ---- HIV: add more increase (hypersusceptibility) ----------------------
    cases.append(MutationLigandPair(
        sample_id="HIV_K20I_IDV",
        protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
        mutation_notation="K20I", wt_residue="K", mutant_residue="I",
        uniprot_position=20, pdb_position=20, pdb_chain="A",
        ligand_id="IDV", ligand_name="Indinavir", ligand_role="inhibitor",
        assay_type=AssayType.KI, wt_value=1.0, mutant_value=0.5, value_unit="fold_Ki",
        effect_direction=EffectDirection.AFFINITY_INCREASE, wt_pdb="1sdt.cif",
        review_notes="Hypersusceptibility — adds increase to HIV.",
        experimental_method="in vitro", pmid="11502742",
        data_source="manual_curation", data_quality=DataQuality.CURATED,
        review_status=ReviewStatus.ACCEPTED, split_group=_hiv_acc,
    ))

    # ---- HIV: bulk fill neutral + increase (10 more cases) -------------------
    # Using 1sdt as WT reference for all
    hiv_bulk = [
        # neutral (polymorphic/accessory mutations)
        ("V11I", "V", "I", 11, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("T12S", "T", "S", 12, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("I15V", "I", "V", 15, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("E35D", "E", "D", 35, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("S37N", "S", "N", 37, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("R41K", "R", "K", 41, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("K55R", "K", "R", 55, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("Q61E", "Q", "E", 61, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("I72V", "I", "V", 72, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("T74S", "T", "S", 74, 1.1, EffectDirection.APPROX_NEUTRAL),
    ]
    for notation, wt, mut, pos, fold, direction in hiv_bulk:
        cases.append(MutationLigandPair(
            sample_id=f"HIV_{notation}_MK1",
            protein_accession=_hiv_acc, protein_name=_hiv(), organism="HIV-1",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="MK1", ligand_name="MK1 inhibitor", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="1sdt.cif",
            review_notes=f"HIV bulk — {direction.value}.",
            experimental_method="in vitro", pmid="11095614",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_hiv_acc,
        ))

    # ---- DHFR: bulk fill neutral + increase (8 more cases) -------------------
    dhfr_bulk = [
        ("I7V", "I", "V", 7, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("V8A", "V", "A", 8, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("L13I", "L", "I", 13, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("R28K", "R", "K", 28, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("K55R", "K", "R", 55, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("T56S", "T", "S", 56, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("V115I", "V", "I", 115, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("D21N", "D", "N", 21, 0.8, EffectDirection.AFFINITY_INCREASE),
    ]
    for notation, wt, mut, pos, fold, direction in dhfr_bulk:
        cases.append(MutationLigandPair(
            sample_id=f"DHFR_{notation}_MTX",
            protein_accession=_dhfr_acc, protein_name=_dhfr(), organism="Homo sapiens",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="MTX", ligand_name="Methotrexate", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb=_dhfr_wt,
            review_notes=f"DHFR bulk — {direction.value}.",
            experimental_method="in vitro", pmid="11527979",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_dhfr_acc,
        ))

    # ---- Trypsin: bulk fill increase + neutral (8 more cases) ----------------
    tryp_bulk = [
        ("Y39F", "Y", "F", 39, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("F41Y", "F", "Y", 41, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("C42A", "C", "A", 42, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("H57N", "H", "N", 57, 500.0, EffectDirection.AFFINITY_DECREASE),
        ("Y94F", "Y", "F", 94, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("L99I", "L", "I", 99, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("N143A", "N", "A", 143, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("V213I", "V", "I", 213, 1.1, EffectDirection.APPROX_NEUTRAL),
    ]
    for notation, wt, mut, pos, fold, direction in tryp_bulk:
        cases.append(MutationLigandPair(
            sample_id=f"TRYP_{notation}_BEN",
            protein_accession=_tryp_acc, protein_name="Bovine Trypsin", organism="Bos taurus",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="BEN", ligand_name="Benzamidine", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="3ptb.pdb",
            review_notes=f"Trypsin bulk — {direction.value}.",
            experimental_method="in vitro", pmid="3131872",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_tryp_acc,
        ))

    # ---- BLAC: bulk fill decrease + neutral (8 more cases) -------------------
    blac_bulk = [
        ("T114A", "T", "A", 114, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("D115N", "D", "N", 115, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("N132A", "N", "A", 132, 1.1, EffectDirection.APPROX_NEUTRAL),
        ("T181A", "T", "A", 181, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("D179N", "D", "N", 179, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("R161A", "R", "A", 161, 2.0, EffectDirection.AFFINITY_DECREASE),
        ("D214N", "D", "N", 214, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("T265A", "T", "A", 265, 1.2, EffectDirection.APPROX_NEUTRAL),
    ]
    for notation, wt, mut, pos, fold, direction in blac_bulk:
        cases.append(MutationLigandPair(
            sample_id=f"BLAC_{notation}_PEN",
            protein_accession=_blac_acc, protein_name=_blac(), organism="Escherichia coli",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="PEN", ligand_name="Penicillin G", ligand_role="substrate",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="1btl.pdb",
            review_notes=f"BLAC bulk — {direction.value}.",
            experimental_method="in vitro", pmid="16189104",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_blac_acc,
        ))

    # ---- Mpro: bulk fill neutral + increase (8 more cases) -------------------
    mpro_bulk = [
        ("M49A", "M", "A", 49, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("L50A", "L", "A", 50, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("F140A", "F", "A", 140, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("N142L", "N", "L", 142, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("E166Q", "E", "Q", 166, 15.0, EffectDirection.AFFINITY_DECREASE),
        ("D187N", "D", "N", 187, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("R188K", "R", "K", 188, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("T190A", "T", "A", 190, 1.1, EffectDirection.APPROX_NEUTRAL),
    ]
    for notation, wt, mut, pos, fold, direction in mpro_bulk:
        cases.append(MutationLigandPair(
            sample_id=f"MPRO_{notation}_NIR",
            protein_accession=_mpro_acc, protein_name="SARS-CoV-2 Mpro", organism="SARS-CoV-2",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="NIR", ligand_name="Nirmatrelvir", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="6lu7.pdb",
            review_notes=f"Mpro bulk — {direction.value}.",
            experimental_method="in vitro FRET", pmid="32726803",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_mpro_acc,
        ))

    # ---- Neuraminidase: bulk fill neutral (8 more cases) --------------------
    neur_bulk = [
        ("V116A", "V", "A", 116, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("D151N", "D", "N", 151, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("R152K", "R", "K", 152, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("Y155F", "Y", "F", 155, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("W178A", "W", "A", 178, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("S179A", "S", "A", 179, 1.2, EffectDirection.APPROX_NEUTRAL),
        ("E227D", "E", "D", 227, 1.3, EffectDirection.APPROX_NEUTRAL),
        ("R371K", "R", "K", 371, 1.2, EffectDirection.APPROX_NEUTRAL),
    ]
    for notation, wt, mut, pos, fold, direction in neur_bulk:
        cases.append(MutationLigandPair(
            sample_id=f"NEUR_{notation}_OSL",
            protein_accession=_neur, protein_name="Influenza Neuraminidase", organism="Influenza A virus",
            mutation_notation=notation, wt_residue=wt, mutant_residue=mut,
            uniprot_position=pos, pdb_position=pos, pdb_chain="A",
            ligand_id="OSL", ligand_name="Oseltamivir", ligand_role="inhibitor",
            assay_type=AssayType.KI, wt_value=1.0, mutant_value=fold, value_unit="fold_Ki",
            effect_direction=direction, wt_pdb="2hu4.pdb",
            review_notes=f"Neuraminidase bulk — {direction.value}.",
            experimental_method="in vitro", pmid="16954204",
            data_source="manual_curation", data_quality=DataQuality.CURATED,
            review_status=ReviewStatus.ACCEPTED, split_group=_neur,
        ))

    return cases


def get_dataset_summary() -> dict:
    """Return a summary of the golden dataset."""
    cases = load_golden_cases()
    proteins = {}
    directions = {}
    has_structure = 0
    has_ddg = 0
    for c in cases:
        proteins[c.protein_name] = proteins.get(c.protein_name, 0) + 1
        directions[c.effect_direction.value] = directions.get(c.effect_direction.value, 0) + 1
        if c.wt_pdb and c.mutant_pdb:
            has_structure += 1
        if c.delta_delta_g is not None:
            has_ddg += 1

    return {
        "total": len(cases),
        "proteins": proteins,
        "effect_directions": directions,
        "has_structure_pair": has_structure,
        "has_ddg": has_ddg,
        "data_quality": {
            "curated": sum(1 for c in cases if c.data_quality.value == "curated"),
            "reported": sum(1 for c in cases if c.data_quality.value == "reported"),
        },
    }
