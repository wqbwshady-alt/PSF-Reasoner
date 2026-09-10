# PSF-Reasoner 证据核验报告（EVIDENCE-REVIEW）

- 核验日期：2026-09-10
- 核验范围：`src/psf_reasoner/datasets/golden_cases.py`（118 案例）、`src/psf_reasoner/knowledge/literature_evidence.py`（9 条证据）、`src/psf_reasoner/benchmarks/schemas.py`、`benchmarks/hiv1_protease/{pilot,v1.0.0,v1.1.0,v1.2.0}.json`、`examples/data/` 下 49 个结构文件、`pilot_validity_audit/`、`docs/interaction-validation.md`、`docs/PROJECT-STATE.md`、`progress.md`
- 核验方法：
  - 文献身份：NCBI E-utilities（`esummary`/`efetch`）逐条查询 PMID，读取题名/作者/期刊/年卷页/摘要
  - DOI 存在性：Crossref REST API（`api.crossref.org/works/<doi>`）+ `doi.org` 解析。方法学对照：先确认已知真实 DOI 返回 200，再采信 404 为"不存在"
  - 结构内容：本地解析 `examples/data/` 中文件的 `_atom_site` / `HETATM` / `SEQRES` / `SEQADV` / `HETNAM` / `_refine.ls_d_res_high`，并与 RCSB Data API（`data.rcsb.org/rest/v1/core/...`）交叉核对
  - 数值核实：优先使用 PubMed 摘要原文；摘要未覆盖的表格值标注为"未核实"并列入表 4
- 本报告只做调查，未修改任何代码或数据。**凡未能在线核实的事项一律标注"未核实"，无任何推测性数值。**

---

## 一、总体结论

**核心结论：`golden_cases.py` 的"118 个手动整理、每项都经过验证的金案例"这一说法不成立。该文件不具备作为校准/评测金标准的数据资格。**

1. **118 个案例中，103 个（87%）引用的 PMID 指向与该案例完全无关的论文。** 这些 PMID 格式合法、确实存在，但内容是护理教育、猪寄生虫病、植物糖蛋白、眼科病例报告等。其中 8 个 PMID（12730686、15632378、10681379、9149701、7540751、8810284、11502742、11095614）覆盖 HIV-1 蛋白酶全部案例；3131872、32726803、16954204 覆盖胰蛋白酶/MPRO/神经氨酸酶全部案例。这不是"个别笔误"，而是**成体系的伪造引用**。
2. **另 15 个案例（EGFR 5 + ABL1 10）的 PMID 真实且主题相邻，但论文本身不报告代码声称的具体倍数。** 例如 PMID 11964322（Branford 2002）是**患者突变筛查**，报告的是"T315I 见于 3 例患者"，没有任何 IC50 倍数；代码却给出 T315I 100×、E255K 30× 等 10 个精确倍数。
3. **13 处 DOI 中 7 处根本不存在**（Crossref 404），且多为真实 DOI 的**数字换位**（如 `10.1056/NEJMoa040238` 实为 `NEJMoa040938`；`10.1128/AAC.47.10.3123-3128.2003` 实为 `...3123-3129.2003`）。最典型的是 `10.1126/science.2548654`——把 PMID `2548654` 直接拼到 `10.1126/science.` 前缀上，而该 PMID 实为 1989 年《Br J Surg》的**幼年性息肉病例报告**。
4. **59 个案例（50%）的"实验配体"与所挂结构文件中的真实配体不一致。** 最严重的是 16 个 MPRO 案例声称配体为"nirmatrelvir (NIR)"却挂 `6lu7.pdb`（真实配体是 **N3**，且 nirmatrelvir 在 2020 年尚未公开）；16 个 BLAC/PEN 案例挂 `1btl.pdb`（**该结构不含任何配体，只有硫酸根**）。仓库中其实已存有正确结构（`7vh8.pdb` = Mpro + PF-07321332，`1fqg.pdb` = TEM-1 青霉素 G 酰基酶），但未被使用。
5. **114 个 fold_Ki 案例的倍数取值全部落在"整数或一位小数"上**（1.1/1.2/1.3/1.5/2.0/2.5/3/4/5/6/7/8/10/12/13/15/20/25/30/50/80/100/400/500/1000/10000），4 个 ΔΔG 案例为 2.1/1.5/3.5/2.8 kcal/mol（同样全为一位小数）。**没有任何一个带"零头"的值**。而真实测量值长这样：**3.35×、0.16×、86×、31×、15×、5×**（Liu 2008 Table 1）、**3.3×、0.16×**（Mahalingam 2004 摘要）、**88×**（Ercikan-Abali 1996）。这是数值被"编造"而非"抄录"的统计学指纹。
6. **62/118（53%）案例的方向标签是 `approximately_neutral`，代码注释明写"building label diversity"、"fills quota"、"bulk fill"、"to hit quota"。** 第 714 行之后的 50 个案例是六个批量 for 循环生成的，全部使用 `review_notes=f"... bulk — {direction}"` 模板，且全部标记 `review_status=ACCEPTED`。
7. **`review_status=ACCEPTED` 与 `DataQuality.CURATED` 不构成任何验证。** 上述 103 个错误引用案例全部为 `ACCEPTED`。`golden_cases.py` 顶部 docstring 声称"Every entry has been verified for … Same ligand in WT and mutant measurements … No unaccounted background mutations in the PDB structures used"，而数据本身直接违反这两条（见 表 2）。
8. **benchmarks/hiv1_protease 的情况显著好于 golden_cases**：v1.2.0 的 11 个案例中，4 个来自 Liu 2008 Table 1 的数值已逐项核对**完全正确**（0.42→36 nM / 86×、0.58→18 nM / 31×、0.42→6 nM / 15×、0.42→2.2 nM / 5×），Mahalingam 2004 的 3.3×/0.16× 也由摘要确证。但 `progress.md` 所称"v1.2.0 全部从论文表格核实"**言过其实**：来自 Mahalingam 1999 的 3 个案例（L90M 20×、G48V 160×、G48V+L90M 1000×）摘要未给出，仍属未核实；且 v1.2.0 把 1SDV/1SDU **张冠李戴**（见 表 2）。
9. **`pilot_validity_audit/` 的"Identity-blinded MCC = 0.000（跨 8 家族 118 案例）"结论不可采信**：该结论无任何产物文件支撑，且审计代码 `identity_audit.py` 的 `_FAMILY_MAP` 只覆盖 **5** 个蛋白（不含 trypsin/Mpro/neuraminidase），与"8 家族"矛盾；`pilot_validity_summary.md` 自身的数据（留一蛋白 CV 全部 MCC=0.000，logistic 回归 balanced_acc=0.110 **低于随机**）直接否定了其"Strong signal detected"的表述。
10. **`docs/interaction-validation.md` 引用的 PLIP 文献 PMID 33950225 也是错的**——该 PMID 实为《Rheumatology》关于 JAK1 抑制剂类风湿关节炎 III 期试验的论文；PLIP 2021 的正确 PMID 是 **33950214**。

**处置建议总纲：**
- **必须排除**：103 个引用无关 PMID 的案例（表 3-A）；15 个数值无来源的 EGFR/ABL1 案例（表 3-B）；59 个结构配体不匹配的案例在"基于结构的特征/校准"中必须排除（表 3-C）；50 个批量填充案例（表 3-D）。
- **可保留但须更正引用**：`HIV_V82A_MK1`（数值 5.0 改为 3.3，PMID 改为 15066177）、`DHFR_L22Y_MTX`（PMID 改为 7890613）、`DHFR_F31R_MTX`（数值 3.5 改为 2.1，来源 Volpato 2009 / PMID 19478082）、`EGFR_C797S_IRE`（来源改为 Thress 2015 / PMID 25939061，数值 80× 待核）。
- **可保留**：`benchmarks/hiv1_protease/v1.2.0.json` 中 Liu 2008 来源的 4 个案例（须修正 1SDV/1SDU 互换）；`examples/data/` 的结构文件本身是真实的原始沉积文件，问题出在**配对与标注**而非文件。

---

## 二、表 1 — 被引 PMID 核验结果

> 说明："是否支持"指该论文是否真的报告了代码声称的具体数值与方向。
> DOI 状态由 Crossref API 逐条判定。"不存在" = HTTP 404 / Resource not found。

### 1.1 `golden_cases.py`

| # | PMID | 出现位置 | 代码声称 | PMID 存在 | 实际对应论文 | 是否支持 | 正确来源 | 处置 |
|---|---|---|---|---|---|---|---|---|
| 1 | **2548654** | `datasets/golden_cases.py:48`、`knowledge/literature_evidence.py:35`、`benchmarks/schemas.py:60` | V82A + MK1(indinavir) = 5.0× Ki；`literature_evidence.py` 还配 DOI `10.1126/science.2548654` 并称"V82A reduces susceptibility to MK1-class inhibitors" | 是 | **Sene A, et al. "Juvenile polyp in an ileoanal J pouch following restorative proctocolectomy for juvenile polyposis coli." *Br J Surg.* 1989 Aug;76(8):801.**（幼年性息肉病例报告，DOI `10.1002/bjs.1800760812`） | **否** | **PMID 15066177**（Mahalingam 2004, *Eur J Biochem* 271(8):1516-24）：V82A = **3.3 倍**，L90M = **0.16 倍**（摘要原文确证）。数值应改为 3.3 | **更正**（PMID 与数值同时更正） |
| 2 | **12730686** | `golden_cases.py:69`、`literature_evidence.py:45`、`benchmarks/schemas.py:71` | V82A + DRV = 5.0× Ki；DOI `10.1128/AAC.47.10.3123-3128.2003` | 是 | **Howard BR, et al. "Structural insights into the catalytic mechanism of cyclophilin A." *Nat Struct Biol.* 2003;10(6):475-81**（亲环素 A 晶体结构，与蛋白酶无关） | **否** | 未找到报告 darunavir **Ki** 倍数且覆盖 V82A 的来源。最接近的 Koh Y 2003 *AAC* 47(10):3123-**3129**（PMID 14506019）报告的是 **IC50 不是 Ki**，且全文无 "V82A" | **排除**。另：DOI `...3123-3128.2003` **不存在**（Crossref 404），真实为 `...3123-3129.2003` |
| 3 | **15632378** | `golden_cases.py:84`、`literature_evidence.py:58` | I84V + DRV = 8.0× Ki；DOI `10.1128/AAC.49.1.356-360.2005` | 是 | **Jin Y, et al. "CYP2D6 genotype, antidepressant use, and tamoxifen metabolism…" *J Natl Cancer Inst.* 2005;97(1):30-9**（乳腺癌药物基因组学） | **否** | 无。King NM 2004 *J Virol* 78(21):12012-21（PMID 15479840）用 ITC 测 **Kd**，且用的是 **L63P/V82T/I84V 三突变体**，非单 I84V | **排除**。DOI `...356-360.2005` **不存在**（Crossref 404，该期无此文） |
| 4 | **10681379** | `golden_cases.py:99` | I50V + APV = 20.0× Ki | 是 | **Iwamoto LM, et al. "m-hydroxy benzoylecgonine recovery in fetal guinea pigs." *Drug Metab Dispos.* 2000;28(3):335-8**（可卡因代谢物药代动力学） | **否** | 未核实 | **排除** |
| 5 | **9149701** | `golden_cases.py:114` | D30N + NFV = 15.0× Ki | 是 | **Okano Y, et al. "Orally active prostacyclin analogue in primary pulmonary hypertension." *Lancet.* 1997;349(9062):1365** | **否** | **PMID 14690411**（Clemente 2003, *Biochemistry* 42(51):15029-35）：D30N 对全部受试抑制剂 **2–6 倍**，nelfinavir 最高。数值 15.0 应改为 ~6 | **排除/更正** |
| 6 | **7540751** | `golden_cases.py:129,144` | G48V + SQV = 13.0×；L90M + SQV = 7.0× | 是 | **Barry CD. "Face painting as metaphor." *NLN Publ.* 1994;(14-2634):279-86**（护理人文） | **否** | G48V+SQV：**PMID 18597780**（Liu 2008, *JMB* 381(1):102-15）Table 1 = **86×**；或 **PMID 10429209**（Mahalingam 1999）= **160×**。L90M+SQV：PMID 10429209 = **20×**（未核实，见 表 4） | **排除** |
| 7 | **8810284** | `golden_cases.py:159,174,189,394` | I54V 6.0×、I54M 12.0×、V32I 3.0×、M46I 1.5×（均 + IDV） | 是 | **Pallante KM, et al. "The chick alpha2(I) collagen gene contains two functional promoters…" *J Biol Chem.* 1996;271(41):25233-9**（鸡胶原基因调控） | **否** | 可能真源为 **PMID 7626598**（Gulnik 1995, *Biochemistry* 34(29):9282-7，测 L-735,524 与 Ro31-8959 对 V32I/M46I/V82A/F/I/I84V），但摘要无逐突变倍数，**未核实**；该文亦不含 I54V/I54M | **排除** |
| 8 | **11502742** | `golden_cases.py:408,709` | N88S + IDV = 0.3×（超敏感）、K20I + IDV = 0.5× | 是 | **Andreeva AY, et al. "Protein kinase C regulates the phosphorylation and cellular localization of occludin." *J Biol Chem.* 2001;276(42):38480-6**（紧密连接细胞生物学） | **否** | 未核实。另注：N88S 超敏感主要在 **amprenavir** 文献中报道，非 indinavir；K20I 为非 B 亚型常见多态，对 PI 敏感性影响很小 | **排除** |
| 9 | **11095614** | `golden_cases.py:501,739`（共 12 处） | L63P 1.3、I93L 1.1，以及 bulk 填充的 V11I/T12S/I15V/E35D/S37N/R41K/K55R/Q61E/I72V/T74S（全部 1.1–1.3） | 是 | **Dong Z, et al. "Membrane-type matrix metalloproteinases in mice intracorneally infected with Pseudomonas aeruginosa." *Invest Ophthalmol Vis Sci.* 2000;41(13):4189-94**（小鼠角膜 MMP 表达，RT-PCR/免疫印迹） | **否** | 未找到任何来源逐条报告这 12 个突变的 ~1.1–1.3 倍 Ki 值。作为对照，多药耐药株（PR20/PRS17/PRS5B）的**整株**相对 Kd 变化为 800–10000 倍，与"每个点突变 1.1–1.3 倍"完全不同 | **排除**（12 个案例） |
| 10 | **15118073** | `golden_cases.py:330-333,531`、`literature_evidence.py:117`、`benchmarks/schemas.py:96` | EGFR T790M 对 gefitinib 100×、对 erlotinib 50×；L858R 0.05；G719S 0.10；V765M 2.0；DOI `10.1056/NEJMoa040238` | 是 | **Lynch TJ, et al. "Activating mutations in the epidermal growth factor receptor underlying responsiveness of NSCLC to gefitinib." *N Engl J Med.* 2004;350(21):2129-39**（真实、主题相关） | **部分/否** | 该文报告的是**敏感化（sensitizing）突变**，无倍数表；**T790M 不在该文中**（2005 年才由 PMID 15728811 / 15737014 报道）；**V765M 在文献中无对应来源**。正确 DOI 为 `10.1056/NEJMoa040938` | **更正 DOI**；T790M 数值**排除**（需另找来源）；V765M **排除** |
| 11 | **24722272** | `golden_cases.py:334`、`literature_evidence.py:140` | EGFR C797S + gefitinib = 80×；DOI `10.1038/nrc3712`（称"gatekeeper 突变综述"） | 是 | **Khan B, et al. "Excellent outcome of Aspergillous endophthalmitis in a case of allergic bronchopulmonary aspergillosis." *Indian J Ophthalmol.* 2014;62(3):352-4**（眼科病例报告） | **否** | C797S 正确来源为 **PMID 25939061**（Thress KS, et al. *Nat Med.* 2015;21(6):560-2）。DOI `10.1038/nrc3712` **存在但不是主题**：实为 Korolev/Xavier/Gore "Turning ecology and evolution against cancer" *Nat Rev Cancer* 2014 | **更正**；80× 待核 |
| 12 | **11964322** | `golden_cases.py:360-364,469,482,635`、`benchmarks/schemas.py:107` | ABL1 T315I 100×、E255K 30×、F317L 15×、Y253H 20×、M351T 3×、E255V 25×、H396P 4.0、L248V 1.5、G250E 2.0、Q252H 8.0（均 vs imatinib） | 是 | **Branford S, et al. "High frequency of point mutations clustered within the ATP-binding region of BCR/ABL…" *Blood.* 2002;99(9):3472-5** | **否** | 该文为**患者突变筛查**，只报告例数（T315I 3 例、Y253H 1 例、F317L 1 例、E255K 4 例、G250E 2 例、M351T 2 例），**无任何倍数**；且明确称 E255K/G250E/M351T "不"预测破坏 imatinib 结合；**E255V/H396P/L248V/Q252H 完全不在文中**。可能真源：PMID 15930265（O'Hare 2005 *Cancer Res*），**未核实** | **数值全部排除**；PMID/DOI 本身正确（`10.1182/blood.v99.9.3472`） |
| 13 | **16189104** | `golden_cases.py:440,455,546,817`（共 11 处） | TEM-1 G238S 3×、R244S 2.5×、A237G 1.3×，以及 bulk 填充 8 个 | 是 | **Bauvois C, et al. "Kinetic properties of four plasmid-mediated AmpC beta-lactamases." *Antimicrob Agents Chemother.* 2005;49(10):4240-6** | **否** | 该文研究的是 **class C（AmpC）天然酶** ACT-1/MIR-1/CMY-2/CMY-1，**不是 TEM-1、不是 class A、且不含任何定点突变体**，无 G238S/R244S/A237G。DOI `10.1128/AAC.49.10.4240-4246.2005` 与 PMID 匹配（真实） | **排除**（11 个案例） |
| 14 | **2205042** | `golden_cases.py:299,317`（共 5 处）、`benchmarks/schemas.py:119` | TEM-1 S70A + PEN = 0.05×（亲和力**升高** 20 倍）；S130A/E166A/K73A/E104A 各 0.10× | 是 | **Yang S, et al. "Serum levels of gastrin, insulin and glucagon as possible factors of anorexia in pigs infected once with Ascaris suum." *Vet Parasitol.* 1990;36(3-4):211-9**（猪寄生虫病） | **否** | 未核实，且**机制上不合理**：Ser70 是 class A β-内酰胺酶的**催化亲核体**，S70A 破坏酰化步骤。公认研究（PMID 8823158, Chen 1996 *Biochemistry*）报告 kcat 下降 10⁴–10⁵ 倍，未报告可定量的亲和力**升高** | **排除**（5 个案例） |
| 15 | **3131872** | `golden_cases.py:570,655,791`（共 16 处） | 牛胰蛋白酶 D189S 0.8、G193A 1.5、S195A 100、G216A 2.0、G226A 3.0、K60A 1.0、H57A 1000、D102N 500，及 bulk 8 个 | 是 | **Russi W. "[Current aspects of ambulatory long-term oxygen therapy]." *Schweiz Med Wochenschr.* 1988;118(11):401-4**（德文，门诊长期氧疗） | **否** | 未核实 | **排除**（全部 16 个 TRYP 案例） |
| 16 | **32726803** | `golden_cases.py:593,615,843`（共 16 处） | SARS-CoV-2 Mpro + **nirmatrelvir (NIR)**：H41A 500、C145A 1000、E166A 50、Q189A 3，及 T25A/N142A/G143A/S144A 与 bulk 8 个；`experimental_method="in vitro FRET"` | 是 | **Shin D, et al. "Papain-like protease regulates SARS-CoV-2 viral spread and innate immunity." *Nature.* 2020;587(7835):657-62** | **否** | 四重不匹配：① 该文研究对象是 **PLpro（nsp3 木瓜样蛋白酶）**，不是 Mpro（nsp5/3CLpro），无 Mpro 突变体面板、无 Mpro FRET 数据；② 全文不涉及 nirmatrelvir——该药由 **Owen et al. *Science* 2021;374(6575):1586-93（PMID 34726479）** 首次公开，比该文晚约 15 个月；③ 未报告上述任何突变倍数；④ **`ligand_id="NIR"` 本身是错的化学组分代码**：CCD `NIR` = 3-(aminocarbonyl)-1-[(3R,4S,5R)-3,4-dihydroxy-5-methyltetrahydrofuran-2-yl]pyridinium（C11H18N2O4，2002 年沉积），与 nirmatrelvir 无关；nirmatrelvir 的真实 CCD 是 **ZGW**（游离态）与 **4WI**（共价亚胺加合物）。可能的本意来源为 **PMID 37271339**（Kovalevsky 2023 *J Biol Chem*），但其量级（H41A ~20×、C145A ~400×、E166A ~3.2×）与本代码记录的 500/1000/50/3 **不符**，且未核实全文。Mpro + nirmatrelvir 的真实结构为 **7VH8**（PMID 34687004），仓库已存但未用 | **排除**（全部 16 个 MPRO 案例） |
| 17 | **16954204** | `golden_cases.py:679,869`（共 13 处） | 流感神经氨酸酶 + oseltamivir：H275Y 400、E119V 100、R292K 10000、N294S 30、I223R 10，及 bulk 8 个 | 是 | **Sun F, et al. "Derlin-1 promotes the efficient degradation of the cystic fibrosis transmembrane conductance regulator (CFTR)…" *J Biol Chem.* 2006;281(48):36856-63**（内质网蛋白降解） | **否** | 该文无流感、无神经氨酸酶、无 IC50、无耐药倍数。**另有三类内部矛盾**：① 该面板**混用亚型与编号体系**——H275Y 属 N1（pandemic H1N1 编号）、E119V 与 R292K 属 **N2 编号**、N294S 属 N1/N2、I223R 属 pandemic H1N1；**没有任何单篇论文会把 5 个突变作为同一配体（同一 "OSL"）的 fold-Ki 面板报告**；② 案例统一声明 `protein_accession="P03468"`（= A/Puerto Rico/8/1934 **H1N1**），一个 H1N1 accession 不可能自洽地承载 N2 编号的 E119V/R292K/N294S；③ **`ligand_id="OSL"` 本身是错的化学组分代码**——CCD `OSL` = (2R)-2-hydroxy-3-(sulfooxy)propanoic acid（无关的 3 碳片段），奥司他韦羧酸的真实代码是 **G39**（游离酸）/ OSE（磷酸盐） | **排除**（全部 13 个 NEUR 案例） |
| 18 | **8345919** | `golden_cases.py:215,231`、`literature_evidence.py:76`、`benchmarks/schemas.py:83` | DHFR L22F ΔΔG = 2.1 kcal/mol；L22Y = 1.5 kcal/mol；DOI `10.1021/bi00072a011` | 是 | **Graf MA. "Video taping return demonstrations." *Nurse Educ.* 1993;18(4):29,32**（护理教育） | **否** | **PMID 7890613**（Lewis WS, et al. *J Biol Chem.* 1995;270(10):5057-64，即 1DLR/1DLS 的原始文献）与 **PMID 8643082**（Ercikan-Abali 1996, *Mol Pharmacol* 49(3):430-7，L22F 对 MTX Ki 上升 88 倍 ≈ 2.6 kcal/mol）。DOI `10.1021/bi00072a011` **真实但指向色氨酸合酶论文**（Tsuji 1993 *Biochemistry*） | **更正**（数值 2.1/1.5 未能归属，须重新取值） |
| 19 | **11258910** | `golden_cases.py:246,261,694`、`literature_evidence.py:99` | DHFR F31R ΔΔG=3.5；F31S ΔΔG=2.8；Q35E **提高** MTX 结合（0.7×）；DOI `10.1021/bi0025035` | 是 | **Ferris PJ, et al. "Glycosylated polyproline II rods with kinks… plant hydroxyproline-rich glycoproteins." *Biochemistry.* 2001;40(9):2978-87** | **否** | **PMID 19478082**（Volpato JP, et al. *J Biol Chem.* 2009;284(30):20079-89，PMC2740434 Table 2 可直接读取）：**F31R ΔΔG = 2.1 kcal/mol（35×）**；**Q35E ΔΔG = 0.3 kcal/mol，方向为亲和力下降 1.5 倍（与代码相反）**；**F31S 不在该文中**（未核实，可能见 PMID 8144541） | **更正**（F31R 3.5→2.1）；**Q35E 方向反转，须更正或排除**；F31S **排除**。DOI `10.1021/bi0025035` **不存在**（该 PMID 真实 DOI 为 `10.1021/bi0023605`） |
| 20 | **11527979** | `golden_cases.py:276,424,516,765`（共 11 处）、`literature_evidence.py:89` | DHFR E30A + MTX = 8× Ki；S118A 1.1；G116A 1.2；bulk 8 个；DOI `10.1073/pnas.191361198`；`experimental_system` 写"X-ray crystallography + kinetic assay" | 是 | **Hou ZJ, et al. "Functional analysis of chimeric proteins of the Wilson Cu(I)-ATPase (ATP7B) and ZntA…" *J Biol Chem.* 2001;276(44):40858-63**（金属转运 ATP 酶嵌合体） | **否** | 该文与 DHFR 无关、无逐突变倍数、非晶体学论文。`experimental_system` 字段亦属虚构 | **排除**（11 个案例）。DOI `10.1073/pnas.191361198` **不存在** |
| 21 | **19692680** | `literature_evidence.py:128` | "osimertinib (AZD9291) overcomes T790M-mediated resistance"；DOI `10.1056/NEJMoa0906108` | 是 | **Mok TS, et al. "Gefitinib or carboplatin–paclitaxel in pulmonary adenocarcinoma." *N Engl J Med.* 2009;361(10):947-57**（IPASS 临床试验） | **否** | 正确来源：**PMID 25923549**（Jänne PA, et al. *N Engl J Med.* 2015;372(18):1689-99，DOI `10.1056/NEJMoa1411817`）。2009 年的论文不可能涉及 2015 年上市的 osimertinib | **更正**。DOI `10.1056/NEJMoa0906108` **不存在**（真实为 `10.1056/NEJMoa0810699`） |

### 1.2 `benchmarks/hiv1_protease/`（情况明显更好）

| # | PMID | 出现位置 | 声称 | 是否存在 | 实际论文 | 是否支持 | 处置 |
|---|---|---|---|---|---|---|---|
| 22 | **15066177** | `pilot.json`、`v1.0.0/v1.1.0/v1.2.0.json`、`pilot.md`、`docs/interaction-validation.md:158` | V82A+MK1 = 3.35×（540→1810 pM）；L90M+MK1 = 0.16×（540→86 pM） | 是 | Mahalingam B, et al. *Eur J Biochem.* 2004;271(8):1516-24，DOI `10.1111/j.1432-1033.2004.04060.x` | **是（倍数）**：摘要原文 "The inhibition (K_i) of PR(V82A) and PR(L90M) was **3.3-** and **0.16-fold**"。**绝对值 540/1810/86 pM 与"Table 1"出处未核实**（全文付费墙，无 PMC 本） | **保留**；绝对值列入表 4 待核 |
| 23 | **9628735** | `pilot.json`、`v1.1.0/v1.2.0.json` | V82F+I84V + indinavir ≈ 200× | 是 | Klabe RM, et al. *Biochemistry.* 1998;37(24):8735-42，DOI `10.1021/bi972555l` | **部分**：摘要确证单突变 0.3–86×、双突变 V82F/I84V **10–2000×**；**indinavir 具体的 200× 未核实**。v1.2.0 文件本身已标注 "approximate — verify exact Ki values from full text" 并 `excluded_from_calibration=true` | **保留（已排除于校准）** |
| 24 | **10429209** | `v1.1.0/v1.2.0.json`（3 个案例）、`pilot.md` | L90M+SQV **20×**（WT Ki 0.033 nM）；G48V+SQV **160×**；G48V+L90M **1000×** | 是 | Mahalingam B, et al. *Eur J Biochem.* 1999;263(1):238-45，DOI `10.1046/j.1432-1327.1999.00514.x` | **未核实**：摘要主题是**催化活性与尿素变性稳定性**，只给相对活性百分比（G48V 50–80%、L90M 20–40%），**未给出 SQV 的 Ki 倍数**。v1.2.0 声称取自 "Table II" | **待人工复核**（需全文 PDF） |
| 25 | **18597780** | `v1.1.0/v1.2.0.json`（4 个案例）、`pilot.md` | G48V+SQV 0.42→36 nM（86×）；I50V+DRV 0.58→18 nM（31×）；I54V+SQV 0.42→6 nM（15×）；I54M+SQV 0.42→2.2 nM（5×） | 是 | Liu F, et al. *J Mol Biol.* 2008;381(1):102-15，DOI `10.1016/j.jmb.2008.05.062`（PMC2754059） | **是**：Table 1 数值（WT DRV 0.58±0.10 / SQV 0.42±0.07 nM；G48V 17±2 / 36±3；I50V 18±1 / 10±1；I54V 5±1 / 6±1；I54M 1.6±0.1 / 2.2±0.3）与 v1.2.0 **逐项一致**；kcat/Km 7.4→7.3（I54M）亦一致 | **保留（已核实）** |
| 26 | **14690411** | `pilot.json`、`v1.1.0/v1.2.0.json`、`pilot.md`、`docs/TODO.md:11` | D30N+NFV ~6×；D30N+M36I+A71V ~22× | 是 | **Clemente JC**, et al. *Biochemistry.* 2003;42(51):15029-35，DOI `10.1021/bi035701y` | **是**：摘要原文 "D30N displayed a **2-6-fold** increase in K_i for all inhibitors tested, with **nelfinavir showing the greatest**"；"triple mutant showed … nelfinavir … **22-**fold" | **保留**。**但 `pilot.md:15` 作者署名错误**：写作"Sayer et al. 2003"，实为 **Clemente** 等；`docs/TODO.md:11` 写 "WT Ki ~2 nM" 属估算 | 

### 1.3 其他文件

| # | 标识符 | 位置 | 声称 | 核验结果 | 处置 |
|---|---|---|---|---|---|
| 27 | **PMID 33950225** | `docs/interaction-validation.md:156` | 引为 "PLIP 2021: expanding the scope of the protein–ligand interaction profiler to DNA and RNA" | **错误**：该 PMID 实为 *Rheumatology (Oxford)* 2021 关于 JAK1 抑制剂类风湿关节炎 III 期试验的论文。PLIP 2021 正确 PMID 为 **33950214**（*Nucleic Acids Res.* 2021;49(W1):W530-W534） | **更正** |
| 28 | **DOI `10.1126/science.2548654`** | `literature_evidence.py:36` | — | **不存在**（Crossref 404；doi.org 无法解析）。与 PMID 2548654（Br J Surg 息肉报告，DOI `10.1002/bjs.1800760812`）无任何关系 | **删除** |
| 29 | **DOI `10.1126/science.2548279`** | 未被仓库引用（仅见于本报告） | — | **存在且正确**：Wlodawer A, et al. "Conserved folding in retroviral proteases: crystal structure of a synthetic HIV-1 protease." *Science.* 1989;245(4918):616-21，**PMID 2548279**（2.8 Å；半胱氨酸被 α-氨基丁酸取代）。注意 **2548279 ↔ 2548654 是数字换位**，代码误用了后者 | 参考信息：若需引 Wlodawer 1989，应使用 2548279 |
| 30 | **DOI `10.1073/pnas.191361198`** | `literature_evidence.py:90` | — | **不存在** | **删除** |
| 31 | **DOI `10.1021/bi0025035`** | `literature_evidence.py:100` | — | **不存在**（真实邻近 DOI `10.1021/bi0023605` 属于植物糖蛋白论文） | **删除** |
| 32 | **DOI `10.1056/NEJMoa040238`** | `literature_evidence.py:118` | — | **不存在**（真实 `10.1056/NEJMoa040938`，数字 040938→040238） | **更正** |
| 33 | **DOI `10.1056/NEJMoa0906108`** | `literature_evidence.py:128` | — | **不存在**（真实 `10.1056/NEJMoa0810699`，数字 0810699→0906108） | **更正** |
| 34 | **DOI `10.1128/AAC.47.10.3123-3128.2003`** | `literature_evidence.py:46` | — | **不存在**（真实 `10.1128/AAC.47.10.3123-3129.2003`，末页 3129→3128） | **更正/删除** |
| 35 | **DOI `10.1128/AAC.49.1.356-360.2005`** | `literature_evidence.py:59` | — | **不存在**（Crossref 404；AAC 49(1) 2005 各文页码连续为 336-341/342-349/350-357/358-365，**不存在 356-360 页的文章**） | **删除** |
| 36 | **DOI `10.1038/nrc3712`** | `literature_evidence.py:141` | 称"gatekeeper 突变综述" | **存在但主题不符**：Korolev KS, Xavier JB, Gore J. "Turning ecology and evolution against cancer." *Nat Rev Cancer.* 2014;14(5):371-80 | **删除** |

---

## 三、表 2 — 结构配对核验

> 结构内容由本地解析 + RCSB Data API 双向确认。`examples/data/` 下的文件本身是真实的原始沉积文件（`data_1SDT`、`data_1SDV` 等数据块名与文件名一致），问题在于**配对与标注**。

| 结构文件 | 真实内容（本地解析 + RCSB 确认） | 案例如何使用 | 是否匹配 |
|---|---|---|---|
| `1sdt.cif` | HIV-1 蛋白酶 **野生型**（残基 82=V、90=L）；配体 **MK1 = indinavir**（C36 H47 N5 O4，613.79）+ 2×CL；**1.30 Å**；携带背景突变 **Q7K/L33I/L63I/C67A/C95A**（相对 UniProt P03367，RCSB 突变注释 5 处）；PMID 15066177 | 作为 **14 个非 MK1 配体案例**（DRV/APV/NFV/SQV/IDV）的 "WT 参考" | **不匹配**：配体为 indinavir，实验配体是 darunavir/amprenavir/nelfinavir/saquinavir/indinavir 等完全不同分子。另 docstring 声称"No unaccounted background mutations"，但它携带 5 个背景突变（`pilot.json` 有记录，`golden_cases.py` 完全未记录） |
| `1sdv.cif` | HIV-1 蛋白酶 **V82A** + **MK1**（indinavir）+ 2×CL；**1.40 Å**；突变位点 [7,33,63,67,**82**,95]。**本报告独立验证**：与 1SDT 序列逐位比较，全序列 99 aa 仅 1 处差异，即第 82 位 V→A | ① `HIV_V82A_MK1`/`HIV_V82A_DRV` 的 mutant_pdb（正确）；② `v1.2.0.json` 与 `pilot.json` 中 **L90M** 案例的 mutant_pdb_id（**错误**） | **①匹配 ②不匹配** |
| `1SDU`（未下载到 `examples/data/`） | RCSB 确认为同篇论文的 **L90M** 复合物（**1.25 Å**，突变位点含 90）；配体 MK1 | `v1.2.0.json`/`pilot.json` 中 **V82A** 案例的 mutant_pdb_id | **不匹配**。即 v1.2.0 把 **1SDV 与 1SDU 完全对调**：`hiv1-v82a-mk1` 应指 1SDV 却写了 1SDU，`hiv1-l90m-mk1` 应指 1SDU 却写了 1SDV；`mechanism_source` 字段（"1SDT vs 1SDU"/"1SDT vs 1SDV"）随之全部反了。**`docs/interaction-validation.md` 与 `progress.md` 中 "1SDV (L90M + MK1)" 的说法同样错误** |
| `1hsg.cif` | HIV-1 蛋白酶（**NY5 分离株**，COMPND 明确写 HIV-1）+ **MK1**（HETNAM 全名 = N-[2(R)-hydroxy-1(S)-indanyl]-5-[(2(S)-tertiary butylaminocarbonyl)-4(3-pyridylmethyl)piperazino]-4(S)-hydroxy-2(R)-phenylmethylpentanamide，RCSB 同义词含 **INDINAVIR**）；**2.00 Å**（题名写 1.9 Å）；RCSB 突变注释 0 处 | `examples/data/1hsg.source.md` 称"HIV-1 protease complexed with L-735,524（配体标识 MK1）" | **匹配**（MK1 = L-735,524 = indinavir 确认无误）。附注：该条目的**原始文献（PMID 7929352）题名写的是 "HIV II protease"**，而其姊妹条目 1HSH/1HSI 才是 HIV-2；文献题名与沉积内容存在冲突（列入表 4） |
| `1U72.pdb` | 人 DHFR **野生型** + **MTX** + **NDP(NADPH)**；**1.9 Å**；残基 22=LEU、30=GLU、31=PHE、35=GLN、116=GLY、118=SER（全部野生型）；PMID 15681865（*Acta Cryst D* 2005，Leu22 变体研究） | `DHFR_L22Y_MTX` 的 wt_pdb；以及其余 15 个 DHFR 案例的 WT 参考 | **匹配** |
| `1dls.pdb` | 人 DHFR **L22Y**（SEQADV：`TYR A 22 UNP P00374 LEU 22 CONFLICT`）+ **MTX** + NDP；**2.3 Å**；PMID **7890613**（Lewis 1995 JBC） | `DHFR_L22Y_MTX` 的 mutant_pdb | **匹配**。与 `HIV_V82A_MK1`（1sdt/1sdv + MK1）并列，是全库**仅有的两组**结构、突变、配体三者全部正确配对的 WT/mutant 对 |
| `1btl.pdb` | TEM-1 β-内酰胺酶 **1.8 Å**；**唯一 HETATM = SO4（硫酸根）**，**不含任何配体/底物**；残基 70=SER、130=SER、166=GLU、73=LYS、104=GLU、237=ALA、238=GLY、244=ARG | **16 个 BLAC/PEN 案例**（S70A/S130A/E166A/K73A/E104A/G238S/R244S/A237G + bulk 8 个）的 wt_pdb | **不匹配**：实验配体是青霉素 G，结构中根本没有配体。仓库内其实存有 `1fqg.pdb`（TEM-1 **E166N** + **PNM = "OPEN FORM - PENICILLIN G" 酰基酶中间体**，1.7 Å，PMID 1436034），**未被使用** |
| `3ptb.pdb` | β-胰蛋白酶（COMPND `BETA-TRYPSIN`, EC 3.4.21.4）+ **BEN（benzamidine，HETNAM 确认）** + **CA（钙离子）**；**1.70 Å**；残基 57=HIS、102=ASP、195=SER（催化三联体完整），189=ASP（S1 口袋）；原始文献 Marquart M, et al. *Acta Crystallogr Sect B* 1983;39:480（该条目**无 DOI/PMID**） | 全部 **16 个 TRYP/BEN 案例**的 wt_pdb | **配体匹配**（BEN = benzamidine 无误），可支持"WT 模板"用途。但 16 个案例所引 PMID 3131872 为 1988 年德文氧疗综述（**引用完全不匹配**，见表 1），且 3PTB 是**纯结构论文，不含任何突变体 Ki 数据**，无法支撑任何倍数 |
| `6lu7.pdb` | SARS-CoV-2 **Mpro** + **抑制剂 N3**（题名明确 "in complex with an inhibitor N3"；N3 被建模为**肽样聚合物实体**（C 链，6 个单体），故 `nonpolymer_entity_count = 0`；其组分代码为 **02J**（5-甲基异噁唑-3-羧酸）、**010**（苯甲醇）、**PJE**（(E,4S)-4-氨基-5-[(3S)-2-氧代吡咯烷-3-基]戊-2-烯酸）+ ALA/VAL/LEU；注意 **"N3" 本身不是 CCD 代码**，`chemcomp/N3` 返回 404）；**2.16 Å**；PMID 32272481（Jin 2020 *Nature* 582:289-293） | **16 个 MPRO/NIR 案例**的 wt_pdb，声称配体为 **nirmatrelvir** | **不匹配**：配体是 **N3**（拟肽抑制剂），**不是 nirmatrelvir**。nirmatrelvir（PF-07321332）2021 年 11 月才公开（PMID 34726479），2020 年 1 月沉积的 6LU7 不可能含它；且 `ligand_id="NIR"` 是错代码（见 表 1 #16）。仓库内已存有正确结构 **`7vh8.pdb`**（Mpro + **4WI = PF-07321332**，1.59 Å，PMID 34687004），**未被使用** |
| `2hu4.pdb` | 流感 **N1 神经氨酸酶**（A/Vietnam/1203/2004 H5N1，**UniProt Q6DPL2**）+ **G39 = 奥司他韦羧酸**（oseltamivir carboxylate，HETNAM 确认，8 份）；**2.5 Å**；PMID 16915235（Russell 2006 *Nature*）；**COMPND 标注 "MUTATION: YES"**，8 条链的 SEQADV 均为 `TYR A 252 UNP Q6DPL2 HIS 233 ENGINEERED MUTATION`，RCSB 突变注释 1 处（沉积编号 252） | **13 个 NEUR/OSL 案例**的 wt_pdb，并声明 `protein_accession="P03468"`、`pdb_position=275` | **四重不匹配**：① 该结构**本身是工程突变体**，不能作 WT 参考；② accession 不符——`P03468` 是 **A/Puerto Rico/8/1934 (H1N1)** 的神经氨酸酶，而结构来自 **A/Vietnam/1203/2004 (H5N1)**（Q6DPL2）；③ 编号不符——沉积文件中突变位点为 **252**，案例声明 `pdb_position=275`；④ **该工程突变并非经典耐药突变 H274Y/H275Y**——SEQADV 记录的是 **H233Y（UniProt 编号）/ H252Y（本条目的编号）**，而经典耐药位点 **His274 在该结构中仍是野生型 His**（距结合的奥司他韦 5.9 Å，而工程 Tyr252 距配体 9.9 Å）。因此 `NEUR_H275Y_OSL` 这个案例名所声称的突变，**在它挂的结构里根本不存在**。配体本身（G39）与实验配体 oseltamivir 基本一致，但 `ligand_id="OSL"` 是错的 CCD 代码 |
| `2hyy.pdb` | 人 ABL1 激酶域 + **STI = imatinib**（HETNAM 确认为伊马替尼）；**2.4 Å**；PMID 17164530；ENGINEERED: YES 但无 SEQADV 记录 | `ABL1_L248V/G250E/Q252H_STI` 三个案例的 wt_pdb | **配体匹配**（STI = imatinib 无误）。但这三个案例的倍数（1.5/2.0/8.0）无来源（见表 1 #12） |

**「结构配体 ≠ 实验配体」案例完整清单（共 59 个，占 118 的 50%）：**

- **`1sdt.cif`（MK1/indinavir）用于非 MK1 配体 — 14 个**：`HIV_V82A_DRV`、`HIV_I84V_DRV`、`HIV_I50V_APV`、`HIV_D30N_NFV`、`HIV_G48V_SQV`、`HIV_L90M_SQV`、`HIV_I54V_IDV`、`HIV_I54M_IDV`、`HIV_V32I_IDV`、`HIV_M46I_IDV`、`HIV_N88S_IDV`、`HIV_L63P_IDV`、`HIV_I93L_IDV`、`HIV_K20I_IDV`
- **`1btl.pdb`（无配体，仅 SO4）用于 PEN — 16 个**：`BLAC_S70A_PEN`、`BLAC_S130A_PEN`、`BLAC_E166A_PEN`、`BLAC_K73A_PEN`、`BLAC_E104A_PEN`、`BLAC_G238S_PEN`、`BLAC_R244S_PEN`、`BLAC_A237G_PEN`、`BLAC_T114A_PEN`、`BLAC_D115N_PEN`、`BLAC_N132A_PEN`、`BLAC_T181A_PEN`、`BLAC_D179N_PEN`、`BLAC_R161A_PEN`、`BLAC_D214N_PEN`、`BLAC_T265A_PEN`
- **`6lu7.pdb`（N3）用于 NIR/nirmatrelvir — 16 个**：`MPRO_H41A_NIR`、`MPRO_C145A_NIR`、`MPRO_E166A_NIR`、`MPRO_Q189A_NIR`、`MPRO_T25A_NIR`、`MPRO_N142A_NIR`、`MPRO_G143A_NIR`、`MPRO_S144A_NIR`、`MPRO_M49A_NIR`、`MPRO_L50A_NIR`、`MPRO_F140A_NIR`、`MPRO_N142L_NIR`、`MPRO_E166Q_NIR`、`MPRO_D187N_NIR`、`MPRO_R188K_NIR`、`MPRO_T190A_NIR`
- **`2hu4.pdb`（H275Y 突变体，G39）用于 OSL — 13 个**：`NEUR_H275Y_OSL`、`NEUR_E119V_OSL`、`NEUR_R292K_OSL`、`NEUR_N294S_OSL`、`NEUR_I223R_OSL`、`NEUR_V116A_OSL`、`NEUR_D151N_OSL`、`NEUR_R152K_OSL`、`NEUR_Y155F_OSL`、`NEUR_W178A_OSL`、`NEUR_S179A_OSL`、`NEUR_E227D_OSL`、`NEUR_R371K_OSL`

**正确的哈希结构（配体匹配）：** `HIV_V82A_MK1`（1sdt/1sdv + MK1）、`DHFR_L22Y_MTX`（1U72/1DLS + MTX）、以及全部 16 个 DHFR/MTX 案例（1U72 + MTX）、16 个 TRYP/BEN 案例（3ptb + BEN）、3 个 `ABL1_L*` 案例（2hyy + STI）。

**突变体结构覆盖极不均衡：** 118 个案例中**只有 3 个**声明了 `mutant_pdb`（`HIV_V82A_MK1`、`HIV_V82A_DRV`、`DHFR_L22Y_MTX`）。所谓"结构配对案例"绝大部分实际上是"单个 WT 结构 + 实验倍数"。

---

## 四、表 3 — 必须排除清单

> 排除 = 不得用于校准、评测、机制推理或任何对外结论。若需保留，必须先重新溯源。

### 表 3-A. 引用 PMID 与案例内容无关（103 个 = 118 中的 87%）

按蛋白家族拆分（合计 103）：

| 家族 | 数量 | 案例 ID | 错误的 PMID |
|---|---|---|---|
| HIV-1 蛋白酶 | **25** | `HIV_V82A_MK1`*、`HIV_V82A_DRV`、`HIV_I84V_DRV`、`HIV_I50V_APV`、`HIV_D30N_NFV`、`HIV_G48V_SQV`、`HIV_L90M_SQV`、`HIV_I54V_IDV`、`HIV_I54M_IDV`、`HIV_V32I_IDV`、`HIV_M46I_IDV`、`HIV_N88S_IDV`、`HIV_L63P_IDV`、`HIV_I93L_IDV`、`HIV_K20I_IDV`、`HIV_V11I_MK1`、`HIV_T12S_MK1`、`HIV_I15V_MK1`、`HIV_E35D_MK1`、`HIV_S37N_MK1`、`HIV_R41K_MK1`、`HIV_K55R_MK1`、`HIV_Q61E_MK1`、`HIV_I72V_MK1`、`HIV_T74S_MK1` | 2548654、12730686、15632378、10681379、9149701、7540751、8810284、11502742、11095614 |
| 人 DHFR | **16** | `DHFR_L22F_MTX`*、`DHFR_L22Y_MTX`*、`DHFR_F31R_MTX`*、`DHFR_F31S_MTX`、`DHFR_E30A_MTX`、`DHFR_S118A_MTX`、`DHFR_G116A_MTX`、`DHFR_Q35E_MTX`、`DHFR_I7V_MTX`、`DHFR_V8A_MTX`、`DHFR_L13I_MTX`、`DHFR_R28K_MTX`、`DHFR_K55R_MTX`、`DHFR_T56S_MTX`、`DHFR_V115I_MTX`、`DHFR_D21N_MTX` | 8345919、11258910、11527979 |
| TEM-1 β-内酰胺酶 | **16** | `BLAC_S70A_PEN`*、`BLAC_S130A_PEN`、`BLAC_E166A_PEN`、`BLAC_K73A_PEN`、`BLAC_E104A_PEN`、`BLAC_G238S_PEN`、`BLAC_R244S_PEN`、`BLAC_A237G_PEN` + bulk 8 个 | 2205042、16189104 |
| 牛胰蛋白酶 | **16** | 全部 `TRYP_*_BEN` | 3131872 |
| SARS-CoV-2 Mpro | **16** | 全部 `MPRO_*_NIR` | 32726803 |
| 流感神经氨酸酶 | **13** | 全部 `NEUR_*_OSL` | 16954204 |
| EGFR | **1** | `EGFR_C797S_IRE` | 24722272 |

\* 标星者虽引用错误，但存在可更正的合法来源，见 3-E（`HIV_V82A_MK1`、`DHFR_L22Y_MTX`、`DHFR_F31R_MTX`、`BLAC_S70A_PEN` 的数值仍有待重建，故在完成更正前同样不得使用）。

**结论：8 个蛋白家族全部受影响，无一幸免。** 不存在"引用正确但数值有小偏差"的情形——要么引用完全无关（3-A），要么引用相邻但数值无来源（3-B）。

### 表 3-B. PMID 真实但数值无来源（15 个）

`EGFR_T790M_IRE`(100×)、`EGFR_T790M_ERL`(50×)、`EGFR_L858R_IRE`(0.05)、`EGFR_G719S_IRE`(0.10)、`EGFR_V765M_IRE`(2.0 — **该突变在文献中无对应来源**)、`ABL1_T315I_STI`(100×)、`ABL1_E255K_STI`(30×)、`ABL1_F317L_STI`(15×)、`ABL1_Y253H_STI`(20×)、`ABL1_M351T_STI`(3.0)、`ABL1_E255V_STI`(25×)、`ABL1_H396P_STI`(4.0)、`ABL1_L248V_STI`(1.5)、`ABL1_G250E_STI`(2.0)、`ABL1_Q252H_STI`(8.0)

### 表 3-C. 结构配体与实验配体不匹配（59 个）

见 表 2 末尾完整清单：1sdt×14 + 1btl×16 + 6lu7×16 + 2hu4×13。
**这 59 个案例必须从任何"基于结构"的特征计算、校准与展示中排除**，否则模型会把 indinavir/N3/硫酸根的结合几何当作 darunavir/nirmatrelvir/青霉素的几何。

### 表 3-D. 配额填充 / 无来源的批量生成案例（50 个）

`golden_cases.py:714-872` 六个 for 循环生成（`hiv_bulk` 10 + `dhfr_bulk` 8 + `tryp_bulk` 8 + `blac_bulk` 8 + `mpro_bulk` 8 + `neur_bulk` 8），`review_notes` 统一为 `"... bulk — {direction}"` 模板，全部 `review_status=ACCEPTED`、`data_quality=CURATED`。

### 表 3-E. 附条件的"更正后可保留"清单（5 个）

| 案例 | 现状 | 更正方案 |
|---|---|---|
| `HIV_V82A_MK1` | 5.0×，PMID 2548654（息肉报告） | 数值改 **3.3**（Mahalingam 2004 / PMID 15066177）；结构 1sdt/1sdv 配对正确，是全库仅有的两组正确结构对之一 |
| `DHFR_L22Y_MTX` | 1.5 kcal/mol，PMID 8345919 | 结构配对正确；来源改为 **PMID 7890613**（Lewis 1995）；ΔΔG 数值须重取（真实效应远大于 1.5，见 PMID 8643082 的 88×） |
| `DHFR_F31R_MTX` | 3.5 kcal/mol，PMID 11258910 | 来源改为 **PMID 19478082**（Volpato 2009）；数值改 **2.1 kcal/mol** |
| `EGFR_C797S_IRE` | 80×，PMID 24722272 | 来源改为 **PMID 25939061**（Thress 2015）；80× 待核 |
| `benchmarks ... hiv1-v82a-mk1` / `hiv1-l90m-mk1` | 1SDU/1SDV 互换 | mutant_pdb_id 对调：V82A→**1SDV**，L90M→**1SDU**；`mechanism_source` 同步对调 |

---

## 五、表 4 — 待人工复核清单（无法在线核实 / 需原始 PDF）

| # | 事项 | 为什么未能核实 | 需要的动作 |
|---|---|---|---|
| 1 | Mahalingam 2004 的 Ki 绝对值 **540 / 1810 / 86 pM** 与"Table 1"出处 | 全文在 Wiley 付费墙后（403），无 PMC 副本；摘要只给倍数（3.3× / 0.16×） | 取原文 PDF 核对 Table 1 与实验条件（pH 5.0, 25 °C, 0.1 M 醋酸钠, 1 mM EDTA, 1 M NaCl） |
| 2 | Mahalingam 1999（PMID 10429209）的 **L90M 20×、G48V 160×、G48V+L90M 1000×** 与 WT Ki 0.033 nM | 摘要主题为催化活性/稳定性，只给相对活性百分比，未给 SQV 的 Ki 倍数；文章不在 PMC | 取 *Eur J Biochem* 263(1):238-45 全文核对 Table II |
| 3 | Klabe 1998 中 **V82F+I84V 对 indinavir 的具体倍数**（v1.2.0 记 200×） | 摘要只给区间（双突变 Ki 10–2000×） | 取 *Biochemistry* 37(24):8735-42 全文 Table 核对 |
| 4 | EGFR **T790M 100× gefitinib / 50× erlotinib** 的原始出处 | Lynch 2004 不含 T790M；候选来源（Pao 2005 PLoS Med、Kobayashi 2005 NEJM）摘要亦无此数值 | 需检索 2005–2006 年 EGFR T790M 酶学/细胞学论文全文 |
| 5 | EGFR **C797S 80× gefitinib** 的原始出处 | C797S 主要针对三代抑制剂定义，对 gefitinib 的具体倍数未在摘要中 | 核对 Thress 2015 *Nat Med* 全文 |
| 6 | ABL1 十个倍数（T315I 100× 等）的原始出处 | 所引 PMID 11964322 为患者筛查，无倍数；候选 O'Hare 2005（PMID 15930265）付费墙 | 核对 O'Hare 2005 *Cancer Res* 65(11):4500-5 或同类激酶谱筛选论文 |
| 7 | DHFR **L22F 2.1 / L22Y 1.5 kcal/mol**、**F31S 2.8 kcal/mol** 的归属 | 所引 PMID 均无关；真实 L22 文献（7890613 / 8643082）报告的是 88×–28000× 的 MTX 结合下降，与 2.1/1.5 量级不符；F31S 未找到来源 | 用 ProTherm / SKEMPI 数据库反查这两个 ΔΔG 的真实条目；注意 `literature_evidence.py:84` 自述来源为 "ProTherm dataset"（ProTherm 存的是**折叠稳定性** ΔΔG，可能被误标为**结合** ΔΔG） |
| 8 | TEM-1 G238S/R244S/A237G 与 bulk 8 个的青霉素 G 倍数 | 所引 PMID 16189104 研究 AmpC 且无突变体 | 检索 TEM-1 ESBL 定点突变体的 kcat/Km 或 Ki 数据（如 PMID 10428907 TEM-19/15，但该文报告头孢他啶表型） |
| 9 | 胰蛋白酶 16 个倍数、Mpro 16 个倍数、神经氨酸酶 13 个倍数 | 所引 PMID 全部与主题无关 | **需要从零重建来源。** 候选（均未核实全文）：Mpro + nirmatrelvir 见 **PMID 37271339**（Kovalevsky 2023 *J Biol Chem* 299(7):104886，但其次级摘要给出的量级 H41A ~20×、C145A ~400×、E166A ~3.2× **与代码的 500/1000/50/3 不符**）与 **PMID 34726479**（Owen 2021 *Science*）；胰蛋白酶-苯甲脒可查 PMID 8038166（Hedstrom 1994，用 proflavin 而非 benzamidine Ki）与 doi `10.1006/jmbi.1993.1211`（D189G/G226D 结构，无 Ki）；神经氨酸酶需按亚型分别取 WHO/CDC 或 N1/N2 专用研究，**不能用同一个 accession（P03468, H1N1）承载 N2 编号突变** |
| 10 | `2hu4.pdb` 的突变身份与编号 | **已基本查清**：SEQADV 记录工程突变为 **H233Y（UniProt Q6DPL2）/ H252Y（条目编号）**，而经典耐药位点 **His274 在该结构中仍是野生型**；案例名却称 `H275Y` 且 `pdb_position=275`。即**该结构根本不含 H275Y**，同时条目内部把耐药 His 编号为 274 而案例写 275 | 若要保留 `NEUR_H275Y_OSL`，须换成真正的 H275Y 结构（或改为该结构真实对应的 H233Y/H252Y 案例）；并统一编号口径。另需核对 Russell 2006 *Nature*（PMID 16915235）正文以确认该工程突变的生物学含义 |
| 11 | `1hsg.cif` 的物种归属冲突 | 原始文献（PMID 7929352）题名写 "HIV **II** protease"，而沉积序列/COMPND 是 HIV-1（NY5）；姊妹条目 1HSH/1HSI 才是 HIV-2；JBC 全文 403 | 核对 *J Biol Chem* 269(42):26344-8 全文，判断是文献题名有误还是沉积配对有误 |
| 12 | `pilot_validity_audit/` 中"Identity-blinded MCC = 0.000（跨 8 家族 118 案例）" | 仓库内**无任何 identity audit 产物文件**；`identity_audit.py` 的 `_FAMILY_MAP` 只列出 5 个蛋白（P03367/P00374/P62593/P00533/P00519），不含 P00760/P0DTD1/P03468；当前环境缺 `gemmi`，无法重跑 | 在装有 gemmi 的环境重跑并落盘产物；把 trypsin/Mpro/neuraminidase 补进 `_FAMILY_MAP`；"8 家族"的表述须改为实际家族数 |
| 13 | 非洲猪瘟/其他 PMID 的最终确认 | — | 无需动作 |

---

## 六、benchmarks/hiv1_protease 专项结论（任务 4）

**`progress.md:310-315` 声称"Verified all fold_change values in v1.1.0 against primary literature… v1.2.0 created: 11 cases, all Ki values verified from paper tables"。核验结果：部分属实。**

| v1.2.0 案例 | 数值 | 来源 | 核验结论 |
|---|---|---|---|
| `hiv1-v82a-mk1` | 540→1810 pM, 3.35× | Mahalingam 2004 | **倍数已核实**（摘要 3.3×）；**绝对值未核实**（付费墙） |
| `hiv1-l90m-mk1` | 540→86 pM, 0.16× | Mahalingam 2004 | **已核实**（摘要 0.16×，"increased_susceptibility"方向亦正确） |
| `hiv1-g48v-sqv` | 0.42→36 nM, 86× | Liu 2008 Table 1 | **已核实**（逐项一致） |
| `hiv1-i50v-drv` | 0.58→18 nM, 31× | Liu 2008 Table 1 | **已核实** |
| `hiv1-i54v-sqv` | 0.42→6 nM, 15× | Liu 2008 Table 1 | **已核实** |
| `hiv1-i54m-sqv` | 0.42→2.2 nM, 5× | Liu 2008 Table 1 | **已核实**（含注释中 "kcat/Km 7.3 vs 7.4" 亦与 Table 1 一致） |
| `hiv1-l90m-sqv` | 0.033→0.68 nM, 20× | Mahalingam 1999 Table II | **未核实**（摘要未给） |
| `hiv1-g48v-sqv_mahalingam` | 0.033→5.4 nM, 160× | Mahalingam 1999 Table II | **未核实** |
| `hiv1-g48v_l90m-sqv` | 0.033→33 nM, 1000× | Mahalingam 1999 Table II | **未核实** |
| `hiv1-d30n-nfv` | 2.0→12 nM, 6× | Clemente 2003 | **方向与量级已核实**（D30N 2–6×，NFV 最高）；**WT 2.0 nM 为估算**（文件自身已标注） |
| `hiv1-v82f_i84v-mk1` | 200× | Klabe 1998 | **未核实**（摘要给区间 10–2000×）；文件自身已标 "approximate" |

**因此："全部从论文表格核实"不成立**——11 个案例中 6 个可核实（其中 4 个精确无误）、1 个量级可核实、4 个未核实。**v1.1.0→v1.2.0 的 3 处"更正"（L90M 5×→20×、G48V 13.5×→86×/160×、I54V 5×→15×）中，只有 G48V 86× 与 I54V 15× 得到确证；L90M 20× 与 G48V 160× 仍无来源。**

**结构性错误（必须修）：** `hiv1-v82a-mk1` 的 `mutant_pdb_id="1SDU"` 应改为 **1SDV**；`hiv1-l90m-mk1` 的 `"1SDV"` 应改为 **1SDU**。`pilot.json` 有同样的互换。`progress.md` 的 PLIP 段落与 `docs/interaction-validation.md` 中 "1SDV (L90M + MK1)" 的表述同样错误（1SDV 是 V82A）。

---

## 七、pilot_validity_audit 专项结论（任务 5）

**核心结论：`pilot_validity_summary.md` 的"Strong signal detected (best MCC=0.711)"与"Structure features contribute independently"结论被其自身数据否定，且"Identity-blinded MCC = 0.000（跨 8 家族 118 案例）"无产物支撑，不可采信。**

1. **"Identity-blinded MCC = 0.000" 无证据**：`pilot_validity_audit/` 下 8 个文件中没有任何 identity audit 结果（无 `identity_*.json`），`docs/PROJECT-STATE.md:87` 的该结论在仓库内找不到对应产物。且 `calibration/identity_audit.py:22` 的 `_FAMILY_MAP` **只有 5 个蛋白**，与"8 家族"直接矛盾；Mpro（P0DTD1）、trypsin（P00760）、神经氨酸酶（P03468）均不在映射中，会被 `split_group` 匹配失败而剔除。
2. **审计是在 30 个案例上做的，不是 118 个**：`complete_subset_results.json` 的 `A_all_30`（n=30）、`missingness_baseline.json`、`target_masked_results.json` 全部对应旧版 30 案例；而 `PROJECT-STATE.md:87` 却声称"跨 8 家族 118 案例"。**同一声明把两次不同规模运行的数据混在一起。**
3. **"Strong signal" 不成立**：`ablation_metrics.json` 显示 M0_chemistry（accuracy 0.767 / MCC 0.000）、M2_literature（0.767 / 0.000）、M4_chem+lit（0.767 / 0.000）**与多数类基线完全相同**（missingness baseline accuracy 恰为 0.767，因为 23/30 案例同为 decrease）。即**化学特征与文献特征相对多数类毫无增量**。只有含结构特征的模型（M1/M3/M5/M6）MCC 非零。
4. **`literature_masked` 的 MCC 0.441 不应被解释为"结构独立贡献"**：文献特征在 30 案例中 MCC=0.000（无增量），而"遮蔽后仍有 0.441"只说明结构特征在**这 20 个有结构的案例**上拟合了标签——而这些结构正是团队按已知标签挑选的（结构覆盖与标签高度共线），属循环论证。
5. **留一蛋白 CV 明确否定泛化**：`leave_one_protein_out.csv` 与 `fold_metrics.csv` 内容完全相同（同一份结果被写成两个文件，本身是一个产物管理问题），其中 majority 与 heuristic 全部 MCC=0.000，logistic_regression 的 balanced_accuracy 为 0.110（**远低于随机 0.5**），P03367 折 accuracy=0.1。summary 第 5 节自己也写了 "No cross-protein generalization detected"。
6. **`C_contact_8` 子集 n=0**，却以 `accuracy 0.000 / MCC 0.000` 的形式出现在 summary 表格中（JSON 里实际是 `"error": "too few samples"`），属**把空集渲染成"0 分结果"**的展示缺陷。
7. **`case_error_analysis.json` 的 3 个错误案例全部来自已证伪的数据**：`BLAC_E104A_PEN`（引用猪寄生虫病 PMID，标签"increase"来自 0.10× 的编造值）、`EGFR_L858R_IRE` 与 `EGFR_G719S_IRE`（引用 Lynch 2004 但倍数为编造）。**错误分析的对象本身不可信。**

---

## 八、代码层与文档层的连带问题（非文献问题，但影响可信度）

1. **docstring 与数据不符**：`golden_cases.py:1` 写 "Golden 30 curated mutation–ligand pairs"、`:27` 写 "Return the 30 golden cases"，实际返回 118 个。顶部声称的 6 条验证项中，"Same ligand in WT and mutant measurements" 与 "No unaccounted background mutations in the PDB structures used" **被数据直接违反**（表 2）。
2. **PMID 字段格式不统一**：部分案例的 `pmid` 字段值为 `"PMID:11964322"`、`"PMID:15118073"`、`"PMID:24722272"`（带前缀），其余为纯数字。这会导致任何按 PMID 分组的去重/统计逻辑失效。
3. **`uniprot_position` 与 `pdb_position` 恒等**：代码对所有案例都设成同一个值（如 BLAC 全部 `uniprot_position == pdb_position`）。但 1ZG4 的 SEQADV 明确显示 TEM-1 的 **PDB 编号 = UniProt P62593 编号 + 2**（`ILE A 84 UNP P62593 VAL 82`），即催化丝氨酸的 UniProt 位点是 **68 而非 70**。`datasets/residue_mapper.py` 声称做 UniProt↔PDB 映射，但金案例数据本身已把两者写成同一个数，映射失效。
4. **`literature_evidence.py` 的 `experimental_system` 与 `golden_cases.py` 的 `experimental_method` 字段不可信**：前者如 DHFR 条目写 "in vitro purified enzyme, ProTherm dataset"（ProTherm 是折叠稳定性数据库，被当成结合 ΔΔG 来源）、EGFR C797S 条目写 "review article"、TEM-1 条目写 "X-ray crystallography + kinetic assay"——均与所引 PMID 的实际内容不符；后者如 16 个 MPRO 案例统一写 `experimental_method="in vitro FRET"`，而所引 PMID（32726803）是 PLpro 的细胞/结构研究，**没有任何 FRET 实验**。这类字段构成"有出处"的假象。
5. **配体标识符本身有错代码**：`ligand_id="NIR"` 与 `ligand_id="OSL"` **都不是相应药物的 PDB 化学组分代码**——CCD `NIR`（C11H18N2O4，2002 年沉积）与 nirmatrelvir 无关（nirmatrelvir = **ZGW**/**4WI**）；CCD `OSL` 是 (2R)-2-hydroxy-3-(sulfooxy)propanoic acid，与奥司他韦无关（奥司他韦羧酸 = **G39**）。若下游用 `ligand_id` 去 RCSB/Ligand Expo 反查，会取到完全错误的分子。
6. **`expansion.py` 的目标函数本身就是配额**：该文件以 "systematic expansion to 100+ family-balanced cases" 为目标，并在 summary 中按 `≥4 个标签方向 → ✅` 打分。这与 `golden_cases.py` 中的 "building label diversity"、"fills quota"、"bulk fill" 注释互为因果——**数据是为了满足家族×方向的计数矩阵而生成的**。
7. **`fold_metrics.csv` 与 `leave_one_protein_out.csv` 内容逐字节相同**（同名结果重复落盘）。
8. **数值分布异常**：全部 114 个 fold 值均为 1.1/1.2/1.3/1.5/2/2.5/3/4/5/6/7/8/10/12/13/15/20/25/30/50/80/100/400/500/1000/10000，**无一个非整数倍**；而真实测量值（3.35、0.16、86、31、15、5、3.3、88）全部带小数或非整十。这是编造值最直接的统计指纹。

---

## 九、证据链接汇总

**PMID 核对（NCBI E-utilities）**
- https://pubmed.ncbi.nlm.nih.gov/2548654/ — Sene 1989 *Br J Surg*（幼年性息肉病例报告）
- https://pubmed.ncbi.nlm.nih.gov/15066177/ — Mahalingam 2004 *Eur J Biochem* 271(8):1516-24（V82A 3.3× / L90M 0.16×，indinavir）
- https://pubmed.ncbi.nlm.nih.gov/2548279/ — Wlodawer 1989 *Science* 245(4918):616-21
- https://pubmed.ncbi.nlm.nih.gov/12730686/ — Howard 2003 *Nat Struct Biol*（亲环素 A）
- https://pubmed.ncbi.nlm.nih.gov/15632378/ — Jin 2005 *JNCI*（CYP2D6/他莫昔芬）
- https://pubmed.ncbi.nlm.nih.gov/10681379/、https://pubmed.ncbi.nlm.nih.gov/9149701/、https://pubmed.ncbi.nlm.nih.gov/7540751/、https://pubmed.ncbi.nlm.nih.gov/8810284/、https://pubmed.ncbi.nlm.nih.gov/11502742/、https://pubmed.ncbi.nlm.nih.gov/11095614/、https://pubmed.ncbi.nlm.nih.gov/3131872/、https://pubmed.ncbi.nlm.nih.gov/16954204/、https://pubmed.ncbi.nlm.nih.gov/8345919/、https://pubmed.ncbi.nlm.nih.gov/11258910/、https://pubmed.ncbi.nlm.nih.gov/11527979/、https://pubmed.ncbi.nlm.nih.gov/2205042/ — **均为与该案例无关的论文**
- https://pubmed.ncbi.nlm.nih.gov/32726803/ — Shin 2020 *Nature*（SARS-CoV-2 **PLpro**，非 Mpro）
- https://pubmed.ncbi.nlm.nih.gov/24722272/ — Khan 2014 *Indian J Ophthalmol*（曲霉眼内炎）
- https://pubmed.ncbi.nlm.nih.gov/19692680/ — Mok 2009 *NEJM*（IPASS 试验）
- https://pubmed.ncbi.nlm.nih.gov/15118073/ — Lynch 2004 *NEJM*（EGFR 敏感突变）
- https://pubmed.ncbi.nlm.nih.gov/11964322/ — Branford 2002 *Blood*（患者突变筛查）
- https://pubmed.ncbi.nlm.nih.gov/16189104/ — Bauvois 2005 *AAC*（AmpC，非 TEM-1）
- **正确来源**：https://pubmed.ncbi.nlm.nih.gov/18597780/（Liu 2008 *JMB*）、https://pubmed.ncbi.nlm.nih.gov/10429209/（Mahalingam 1999）、https://pubmed.ncbi.nlm.nih.gov/9628735/（Klabe 1998）、https://pubmed.ncbi.nlm.nih.gov/14690411/（Clemente 2003）、https://pubmed.ncbi.nlm.nih.gov/7890613/（Lewis 1995，L22 与 1DLR/1DLS）、https://pubmed.ncbi.nlm.nih.gov/8643082/（Ercikan-Abali 1996，L22F 88×）、https://pubmed.ncbi.nlm.nih.gov/19478082/（Volpato 2009，F31R ΔΔG 2.1 / Q35E 0.3）、https://pubmed.ncbi.nlm.nih.gov/25939061/（Thress 2015，C797S）、https://pubmed.ncbi.nlm.nih.gov/25923549/（Jänne 2015，osimertinib）、https://pubmed.ncbi.nlm.nih.gov/33950214/（PLIP 2021）
- **其他候选来源（均未核实全文）**：https://pubmed.ncbi.nlm.nih.gov/34726479/（Owen 2021 *Science*，nirmatrelvir 首次公开）、https://pubmed.ncbi.nlm.nih.gov/37271339/（Kovalevsky 2023 *J Biol Chem*，Mpro 催化残基 + nirmatrelvir，量级与代码不符）、https://pubmed.ncbi.nlm.nih.gov/8038166/（Hedstrom 1994，胰蛋白酶→胰凝乳蛋白酶转换）

**化学组分代码（RCSB CCD）**
- nirmatrelvir = **ZGW**（游离态）/ **4WI**（共价亚胺加合物）；`NIR` 是无关的 2002 年条目
- 奥司他韦羧酸 = **G39**；`OSL` 是无关的 3 碳硫酸酯片段
- `N3` **不是** CCD 代码（`chemcomp/N3` → 404）；6LU7 中的 N3 被建模为肽样聚合物实体（C 链）

**DOI 判定（Crossref REST API）**
- 不存在：`10.1126/science.2548654`、`10.1128/AAC.47.10.3123-3128.2003`、`10.1128/AAC.49.1.356-360.2005`、`10.1073/pnas.191361198`、`10.1021/bi0025035`、`10.1056/NEJMoa040238`、`10.1056/NEJMoa0906108`
- 存在但主题不符：`10.1021/bi00072a011`（色氨酸合酶）、`10.1038/nrc3712`（癌症生态学综述）
- 存在且正确：`10.1126/science.2548279`、`10.1111/j.1432-1033.2004.04060.x`、`10.1046/j.1432-1327.1999.00514.x`、`10.1016/j.jmb.2008.05.062`、`10.1021/bi972555l`、`10.1021/bi035701y`、`10.1182/blood.v99.9.3472`

**结构（RCSB）**
- https://www.rcsb.org/structure/1SDT · https://data.rcsb.org/rest/v1/core/entry/1SDT — WT HIV-1 PR + MK1，1.30 Å，PMID 15066177
- https://www.rcsb.org/structure/1SDV · https://data.rcsb.org/rest/v1/core/entry/1SDV — **V82A** + MK1，1.40 Å，突变位点 [7,33,63,67,82,95]
- https://data.rcsb.org/rest/v1/core/entry/1SDU — **L90M** + MK1，1.25 Å
- https://www.rcsb.org/structure/1HSG — HIV-1（NY5）+ MK1 = L-735,524 = indinavir，2.00 Å，PMID 7929352
- https://www.rcsb.org/structure/1U72 — 人 DHFR WT + MTX + NDP，1.9 Å，PMID 15681865
- https://www.rcsb.org/structure/1DLS — 人 DHFR **L22Y** + MTX，2.3 Å，PMID 7890613
- https://www.rcsb.org/structure/1BTL — TEM-1，1.8 Å，**仅 SO4，无配体**，PMID 8356032
- https://www.rcsb.org/structure/1FQG — TEM-1 **E166N** + 青霉素 G 酰基酶，1.7 Å，PMID 1436034（仓库已存、未被使用）
- https://www.rcsb.org/structure/3PTB — β-胰蛋白酶 + **BEN（benzamidine）**，1.7 Å
- https://www.rcsb.org/structure/6LU7 — SARS-CoV-2 Mpro + **N3**（02J/010/PJE），2.16 Å，PMID 32272481
- https://www.rcsb.org/structure/7VH8 — SARS-CoV-2 Mpro + **PF-07321332（nirmatrelvir，4WI）**，1.59 Å，PMID 34687004（仓库已存、未被使用）
- https://www.rcsb.org/structure/2HU4 — **N1 H5N1**（A/Vietnam/1203/2004，Q6DPL2）+ **G39 奥司他韦羧酸**，2.5 Å，PMID 16915235，**工程突变体**（SEQADV HIS233→TYR，沉积编号 252）
- https://www.rcsb.org/structure/2HYY — 人 ABL1 激酶域 + **STI（imatinib）**，2.4 Å，PMID 17164530
- https://www.rcsb.org/structure/1M40 — TEM-1 超高分辨率，0.85 Å，PMID 11996574

---

*本报告由证据核验流程生成，所有结论均附可复核的在线证据链接。凡标注"未核实"者，不得在任何对外材料中被表述为已核实。*
