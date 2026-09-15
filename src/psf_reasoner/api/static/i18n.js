/* PSF-Reasoner 前端翻译层
 *
 * 后端报告内容（证据标题/描述、机制、假设、因果图）由确定性引擎以英文
 * 生成。本层在渲染时把它们翻译为中文；未知字符串原样返回（不丢信息）。
 */

window.PSF_I18N = (function () {
  "use strict";

  const exact = {
    // ---- section / chrome ----
    "Executive Summary": "执行摘要",
    "Structure Pair QC": "结构对质控",
    "Physical Evidence": "物理证据",
    "Structural Mechanisms": "结构机制",
    "Functional Hypotheses": "功能假设",
    "Consistency": "一致性检查",
    "Evidence Gap Analysis": "证据缺口分析",
    "Missing Evidence": "缺失证据",
    "Validation Plan": "验证计划",
    "Limitations": "局限性",
    "Literature Evidence": "文献证据",
    "Causal Mechanism Graph": "因果机制图",
    "comparable": "可比",
    "partially_comparable": "部分可比",
    "poorly_comparable": "低可比",
    "Strongly Supported": "强支持",
    "Moderately Supported": "中等支持",
    "Weakly Supported": "弱支持",
    "Strong": "强",
    "Moderate": "中",
    "Weak": "弱",
    "Low confidence": "低置信度",

    // ---- evidence titles ----
    "Nearest heavy-atom distance comparison": "最近重原子距离对比（WT vs 突变体）",
    "Residue-ligand contact state comparison": "残基-配体接触状态对比",
    "Residue solvent-accessible surface area comparison": "残基溶剂可及表面积（SASA）对比",
    "Typed hydrogen-bond geometry comparison": "氢键几何对比",
    "Typed hydrophobic-contact geometry comparison": "疏水接触几何对比",
    "Typed salt-bridge geometry comparison": "盐桥几何对比",
    "Typed pi-interaction geometry comparison": "π 相互作用几何对比",
    "Water-bridge geometry comparison": "水桥几何对比",
    "Ligand-proximal shell geometry comparison": "配体邻近壳层几何对比",
    "Operational ligand-pocket residue-count comparison": "配体口袋残基数对比",
    "Ligand-pocket residue-network comparison": "配体口袋残基网络对比",
    "Lightweight local interaction-score comparison": "局部相互作用评分对比（非 ΔΔG）",
    "HIV-1 protease V82A indinavir-site calibration label": "HIV-1 蛋白酶 V82A/indinavir 位点校准标签",
    "Expected loss or reorganization of inhibitor contacts": "预期证据：抑制剂接触的丢失或重组",
    "Expected inhibitor-pocket geometry change": "预期证据：抑制剂口袋几何变化",
    "Expected water-network change": "预期证据：水网络变化",
    "Expected reduction in favorable inhibitor binding": "预期证据：有利抑制剂结合的减弱",

    // ---- evidence descriptions (exact) ----
    "The resistant state should show altered contact occupancy near the inhibitor.":
      "耐药状态应显示抑制剂附近接触占据的变化。",
    "A packing mechanism predicts a detectable local cavity, shape, or flexibility change.":
      "堆积机制预测存在可检测的局部空腔、形状或柔性变化。",
    "A hydration mechanism predicts changed water occupancy or bridge persistence.":
      "水合机制预测水占据或水桥持续性改变。",
    "Resistance via weaker binding predicts a less favorable mutant local interaction score.":
      "结合减弱型耐药预测突变体的局部相互作用评分更差。",
    "Computed mutation-site graph degree changes indicate local residue-network rewiring.":
      "计算得到的突变位点网络度变化表明局部残基网络重连。",
    "Typed direct or water-mediated interaction deltas suggest altered ligand anchoring.":
      "直接或水介导的相互作用变化提示配体锚定改变。",
    "Resistance could arise if pocket packing changes preferentially weaken inhibitor binding.":
      "若口袋堆积变化优先削弱抑制剂结合，可能产生耐药。",
    "Resistance could arise from loss of a direct or water-mediated inhibitor anchor.":
      "耐药可能源于直接或水介导的抑制剂锚定丢失。",
    "Resistance could arise if conserved hydration interactions are disrupted or displaced.":
      "若保守的水合相互作用被破坏或置换，可能产生耐药。",
    "If the candidate packing loss weakens favorable protein-ligand contacts, ligand affinity may decrease.":
      "若候选的堆积丢失削弱有利的蛋白-配体接触，配体亲和力可能下降。",
    "If the ligand is an inhibitor and binding is selectively weakened while protein function is retained, resistance may increase.":
      "若配体为抑制剂、结合被选择性削弱而蛋白功能保留，耐药性可能上升。",

    // ---- reason / impact / objective / expected_result ----
    "A local mutant-versus-reference comparison is available, but no full contact-map or conformational-ensemble comparison has been computed.":
      "已做局部突变体-参考对比，但未计算完整接触图或构象系综对比。",
    "A ligand-shell geometry proxy is available, but pocket shape and absolute cavity volume have not been evaluated with a validated cavity definition.":
      "已有配体壳层几何代理，但口袋形状与绝对空腔体积未经验证的空腔定义评估。",
    "No binding-energy calculation or experimental affinity measurement is available.":
      "无结合能计算或实验亲和力测量。",
    "Contact changes are needed to support or reject the packing mechanism.":
      "需要接触变化证据来支持或否定堆积机制。",
    "The direction and magnitude of pocket remodelling remain unknown.":
      "口袋重塑的方向与幅度仍然未知。",
    "Functional affinity and resistance hypotheses remain qualitative.":
      "功能亲和力与耐药假设仍为定性。",
    "The associated reverse mechanism cannot yet be discriminated.":
      "相关反向机制目前无法区分。",
    "Test whether the mutation changes direct ligand contacts and pocket packing.":
      "检验突变是否改变直接的配体接触与口袋堆积。",
    "Quantify mutation-associated pocket geometry and solvent exposure changes.":
      "定量突变相关的口袋几何与溶剂暴露变化。",
    "Determine whether inhibitor affinity decreases in the mutant.":
      "确定突变体中抑制剂亲和力是否下降。",
    "Characterize conformational dynamics and interaction occupancies.":
      "表征构象动力学与相互作用占据。",
    "Validate resistance phenotype experimentally.":
      "实验验证耐药表型。",
    "Discriminate packing, anchoring, and hydration mechanisms.":
      "区分堆积、锚定与水合机制。",
    "Link the resistant phenotype to altered inhibitor binding.":
      "将耐药表型与抑制剂结合改变关联。",
    "Reduced or reorganized contacts would support the packing mechanism.":
      "接触减少或重组将支持堆积机制。",
    "A reproducible cavity or exposure change would strengthen the mechanism.":
      "可复现的空腔或暴露变化将增强该机制。",
    "Lower mutant affinity would support the functional hypothesis.":
      "突变体亲和力降低将支持功能假设。",
    "MD-derived occupancies and dynamics should corroborate structural mechanisms.":
      "MD 占据与动力学应佐证结构机制。",
    "One or more candidate-specific physical signatures should emerge.":
      "应出现一个或多个候选特异性的物理特征。",
    "Reduced inhibitor affinity with retained function would support resistance.":
      "亲和力降低且功能保留将支持耐药。",

    // ---- limitations ----
    "Baseline structural mechanisms remain qualitative; coordinate evidence describes only the supplied reference and mutant structures.":
      "基线结构机制仍为定性；坐标证据仅描述所提供的参考与突变体结构。",
    "Required evidence denotes predictions to test, not completed calculations.":
      "所需证据表示待检验的预测，而非已完成的计算。",

    // ---- causal graph: node labels ----
    "Volume change": "体积变化",
    "Polarity change": "极性变化",
    "Aromaticity change": "芳香性变化",
    "H-bond donor gained": "氢键供体新增",
    "H-bond acceptor gained": "氢键受体新增",
    "No significant change": "无显著变化",
    "Atom composition change": "原子组成变化",
    "Contact change": "接触变化",
    "Neighborhood context": "邻域上下文",
    "Steric repacking": "空间重排",
    "Packing loss": "堆积丢失",
    "New H-bond potential": "新氢键潜力",
    "New aromatic potential": "新芳香作用潜力",
    "No interaction change": "无相互作用变化",
    "Steric affinity reduction": "位阻亲和力降低",
    "Packing affinity reduction": "堆积亲和力降低",
    "H-bond compensation": "氢键补偿",
    "Binding effect unknown": "结合效应未知",
    "Potential resistance": "潜在耐药",
    "Phenotype unknown": "表型未知",

    // ---- causal graph: node descriptions (exact) ----
    "Decreased side-chain volume leads to loss of packing contacts":
      "侧链体积减小导致堆积接触丢失",
    "Increased side-chain volume may cause steric clash or repacking near the ligand":
      "侧链体积增大可能在配体附近造成位阻冲突或重排",
    "New H-bond donor/acceptor capability may enable novel interactions with ligand or water":
      "新增氢键供体/受体能力可能产生新的配体或水相互作用",
    "New aromatic ring may enable π-stacking or CH-π interactions":
      "新增芳香环可能形成 π 堆积或 CH-π 相互作用",
    "Steric clash may reduce ligand binding affinity":
      "空间位阻可能降低配体结合亲和力",
    "Loss of packing contacts may reduce binding affinity":
      "堆积接触丢失可能降低结合亲和力",
    "New H-bond capability may partially compensate for steric/packing losses":
      "新氢键能力可能部分补偿位阻/堆积损失",
    "Insufficient evidence to predict binding affinity change":
      "证据不足以预测结合亲和力变化",
    "Reduced inhibitor binding may confer drug resistance, provided catalytic activity is retained":
      "抑制剂结合减弱可能导致耐药（前提：催化活性保留）",
    "Phenotype cannot be predicted from available evidence":
      "现有证据无法预测表型",

    // ---- causal graph: uncertainties ----
    "No MD or ensemble data — contact occupancies and H-bond lifetimes are unknown":
      "无 MD 或系综数据——接触占据与氢键寿命未知",
    "No ΔΔG calculation — binding affinity change is qualitative not quantitative":
      "无 ΔΔG 计算——结合亲和力变化是定性的",
    "No curated literature evidence available for this protein/mutation/ligand combination":
      "该蛋白/突变/配体组合没有已整理的文献证据",
    "No direct or strong literature evidence — relying on structural inference only":
      "无直接或强文献证据——仅依赖结构推断",

    // ---- causal graph: assumptions ----
    "Volume change matters only if it alters contacts within the binding pocket":
      "体积变化仅在改变结合口袋内接触时才有意义",
    "Resistance requires catalytic activity retention (not assessed here)":
      "耐药要求催化活性保留（本平台未评估）",
    "In vivo resistance depends on expression, fitness, drug exposure":
      "体内耐药取决于表达、适应度与药物暴露",
    "Volume increase in a confined pocket causes steric clash":
      "密闭口袋中的体积增大会造成位阻冲突",
    "New H-bond capability only matters if geometry allows actual bond formation":
      "新氢键能力仅在几何允许成键时才有意义",
    "Requires < 3.5 Å donor-acceptor distance and > 100° angle":
      "要求供体-受体距离 <3.5 Å 且角度 >100°",
    "π interactions require appropriate geometry and ring orientation":
      "π 相互作用要求合适的几何与环取向",
    "New H-bond donors can form favorable interactions if geometrically feasible":
      "新氢键供体在几何可行时可形成有利相互作用",
    "New H-bond acceptors can form favorable interactions if geometrically feasible":
      "新氢键受体在几何可行时可形成有利相互作用",
    "Polarity change affects solvation and H-bond energetics locally":
      "极性变化局部影响溶剂化与氢键能量",
    "Aromatic ring can form π-stacking or CH-π interactions":
      "芳香环可形成 π 堆积或 CH-π 相互作用",
    "New H-bonds require specific geometry to form":
      "新氢键需要特定几何才能形成",
    "Steric clash in the binding pocket reduces binding free energy":
      "结合口袋中的位阻冲突降低结合自由能",
    "Lost contacts → fewer favorable vdW interactions":
      "接触丢失 → 有利的范德华相互作用减少",

    // ---- measurement names ----
    "side_chain_size_class_delta": "侧链大小等级变化",
    "minimum_heavy_atom_distance": "最小重原子距离",
    "nearest_heavy_atom_distance_delta": "最近重原子距离变化",
    "contact_state_delta": "接触状态变化",
    "binary_contact_state": "接触状态（是/否）",
    "residue_sasa_delta": "残基 SASA 变化",
    "typed_hydrogen_bond_count_delta": "氢键数变化",
    "typed_atom_pairs": "类型化原子对",
    "typed_hydrophobic_contact_count_delta": "疏水接触数变化",
    "typed_salt_bridge_count_delta": "盐桥数变化",
    "typed_pi_interaction_count_delta": "π 相互作用数变化",
    "ring_centroid_pairs": "环心对",
    "water_bridge_count_delta": "水桥数变化",
    "bridging_waters": "桥接水分子",
    "ligand_shell_bounding_box_volume_delta": "配体壳层体积变化",
    "pocket_residue_count_delta": "口袋残基数变化",
    "mutation_site_network_degree_delta": "突变位点网络度变化",
    "local_interaction_score_delta": "局部相互作用评分变化",
    "qualitative_resistance_affinity_label": "定性耐药/亲和力标签",
    "residue_contact": "残基接触",
    "pocket_geometry": "口袋几何",
    "water_bridge": "水桥",
    "energy_component": "能量分量",

    // ---- evidence applicability ----
    "exact_match": "完全匹配",
    "same_site_same_protein": "同一位点·同一蛋白",
    "nearby_site": "邻近位点",
    "same_protein_mechanism": "同一蛋白·机制层面",
    "family_analogy": "家族类比",
    "general_prior": "通用先验",

    // ---- units ----
    "ordinal_class": "等级",
    "angstrom": "Å",
    "angstrom_squared": "Å²",
    "angstrom_cubed_proxy": "Å³（代理）",
    "typed_atom_pairs": "对",
    "residues": "个残基",
    "residue_contact_edges": "条边",
    "ring_centroid_pairs": "对",
    "bridging_waters": "个",
    "local_score_units": "局部评分单位",
    "directional_label": "方向标签",
  };

  // Parameterized patterns: [regex, replacer(string)]
  const patterns = [
    [/^Side-chain size change for (.+)$/, m => `侧链大小变化：${m[1]}`],
    [/^Nearest heavy-atom distance: (.+) to (.+)$/, m => `最近重原子距离：${m[1]} → ${m[2]}`],
    [/^Coordinate-derived contact: (.+) to (.+)$/, m => `坐标接触：${m[1]} → ${m[2]}`],
    [/^The declared substitution changes the qualitative side-chain size class from (\d+) to (\d+)\.$/,
      m => `该替换将侧链大小等级从 ${m[1]} 变为 ${m[2]}。`],
    [/^The nearest heavy-atom pair is (.+) to (.+) at (.+) A in the supplied structure\.$/,
      m => `参考结构中最近重原子对：${m[1]} → ${m[2]}，距离 ${m[3]} Å。`],
    [/^The nearest heavy-atom pair \((.+), (.+)\) is within the 4\.0 A contact cutoff\.$/,
      m => `最近重原子对（${m[1]}、${m[2]}）处于 4.0 Å 接触截断内。`],
    [/^WT (.+) to (.+): (.+) A; mutant (.+) to (.+): (.+) A\.$/,
      m => `WT：${m[1]} → ${m[2]} = ${m[3]} Å；突变体：${m[4]} → ${m[5]} = ${m[6]} Å。`],
    [/^WT contact=(True|False); mutant contact=(True|False); cutoff=(.+) A\.$/,
      m => `WT 接触=${m[1] === "True" ? "是" : "否"}；突变体接触=${m[2] === "True" ? "是" : "否"}；截断=${m[3]} Å。`],
    [/^WT SASA=(.+) A\^2; mutant SASA=(.+) A\^2; Shrake-Rupley approximation with (\d+) points per atom\.$/,
      m => `WT SASA=${m[1]} Å²；突变体 SASA=${m[2]} Å²（Shrake-Rupley 近似，每原子 ${m[3]} 点）。`],
    [/^WT typed pairs=(\d+); mutant typed pairs=(\d+); donor-acceptor cutoff=(.+) A\.$/,
      m => `WT 氢键对=${m[1]}；突变体=${m[2]}；供体-受体截断=${m[3]} Å。`],
    [/^WT typed pairs=(\d+); mutant typed pairs=(\d+); hydrophobic cutoff=(.+) A\.$/,
      m => `WT 疏水接触对=${m[1]}；突变体=${m[2]}；截断=${m[3]} Å。`],
    [/^WT typed pairs=(\d+); mutant typed pairs=(\d+); charged-atom cutoff=(.+) A\.$/,
      m => `WT 盐桥对=${m[1]}；突变体=${m[2]}；带电原子截断=${m[3]} Å。`],
    [/^WT ring pairs=(\d+); mutant ring pairs=(\d+); centroid cutoff=(.+) A\.$/,
      m => `WT 环对=${m[1]}；突变体=${m[2]}；环心截断=${m[3]} Å。`],
    [/^WT bridges=(\d+); mutant bridges=(\d+); water-to-typed-donor-or-acceptor cutoff=(.+) A\.$/,
      m => `WT 水桥=${m[1]}；突变体=${m[2]}；水-供体/受体截断=${m[3]} Å。`],
    [/^WT shell volume proxy=(.+) A\^3 \((\d+) protein atoms\); mutant=(.+) A\^3 \((\d+) protein atoms\); shell radius=(.+) A\.$/,
      m => `WT 壳层体积代理=${m[1]} Å³（${m[2]} 个蛋白原子）；突变体=${m[3]} Å³（${m[4]} 个）；壳层半径=${m[5]} Å。`],
    [/^WT pocket residues=(\d+); mutant pocket residues=(\d+); residues are included when any heavy atom is within (.+) A of ligand\.$/,
      m => `WT 口袋残基=${m[1]}；突变体=${m[2]}；判定：任一重原子距配体 ≤${m[3]} Å。`],
    [/^WT pocket network edges=(\d+); mutant edges=(\d+); mutation-site degree delta=(-?\d+)\.$/,
      m => `WT 口袋网络边=${m[1]}；突变体=${m[2]}；突变位点网络度变化=${m[3]}。`],
    [/^WT local score=(.+); mutant score=(.+); positive delta indicates a less favorable local interaction score\.$/,
      m => `WT 局部评分=${m[1]}；突变体=${m[2]}；delta 为正表示局部相互作用评分变差（注意：这不是 ΔΔG）。`],
    [/^Curated benchmark label: the V82A HIV-1 protease mutant is treated as an inhibitor-binding-site resistance case for MK1\/indinavir-like pocket analysis\. Literature: 3\.3-fold Ki increase \(Mahalingam et al\. 2004, abstract\)\.$/,
      () => "已整理基准标签：V82A 被列为 MK1/indinavir 类抑制剂结合位点耐药案例。文献：Ki 升高 3.3 倍（Mahalingam 2004 摘要）。"],
    [/^Required reverse-predicted evidence is not yet available: (.+)$/,
      m => `反向预测证据尚不可用：${zh(m[1])}`],
    [/^The (.+) side-chain change may alter local packing around ligand (.+); coordinates are required to establish contact loss\.$/,
      m => `${m[1]} 侧链变化可能改变配体 ${m[2]} 周围的局部堆积；需要坐标证据确认接触丢失。`],
    [/^Mutant retains catalytic function while inhibitor potency drops ≥ 5-fold\.$/,
      () => "突变体保留催化功能而抑制剂效力下降 ≥5 倍。"],
    [/^\[LEGACY HEURISTIC ENGINE\] All confidence values are uncalibrated heuristic weights \(e\.g\. \+0\.06 per evidence match\)\.  Qualitative labels \(Strong\/Moderate\/Weak\/Insufficient\) are derived from these uncalibrated scores and must not be interpreted as probabilities\.  See V3 roadmap for planned calibration against experimental ΔΔG \/ Ki data\.$/,
      () => "【旧版启发式引擎】所有置信度均为未校准的启发式权重（如每条证据匹配 +0.06）。定性标签（强/中/弱/不足）来自这些未校准评分，不可解释为概率。"],
    [/^Side-chain volume (increased|decreased): ([A-Z]+) \((\d+) Å³\) → ([A-Z]+) \((\d+) Å³\)$/,
      m => `侧链体积${m[1] === "increased" ? "增大" : "减小"}：${m[2]}（${m[3]} Å³）→ ${m[4]}（${m[5]} Å³）`],
    [/^Atom-level change: lost=(.*), gained=(.*)$/,
      m => `原子级变化：丢失=[${m[1]}]，新增=[${m[2]}]`],
    [/^Residue-ligand contacts (lost|gained): (\d+) contacts$/,
      m => `残基-配体接触${m[1] === "lost" ? "丢失" : "新增"}：${m[2]} 个`],
    [/^Mutation site has (\d+) residues within 4Å$/,
      m => `突变位点 4Å 内有 ${m[1]} 个残基`],
    [/^No specific interaction type change detected\. Nearest ligand distance: (.+)Å$/,
      m => `未检测到特定相互作用类型变化。最近配体距离：${m[1]} Å`],
    [/^Polarity (.*): ([A-Z]+) → ([A-Z]+)$/,
      m => `极性${m[1]}：${m[2]} → ${m[3]}`],
    [/^Aromaticity (.*): ([A-Z]+) → ([A-Z]+)$/,
      m => `芳香性${m[1]}：${m[2]} → ${m[3]}`],
    [/^H-bond donor (.*): ([A-Z]+) → ([A-Z]+)$/,
      m => `氢键供体${m[1]}：${m[2]} → ${m[3]}`],
    [/^H-bond acceptor (.*): ([A-Z]+) → ([A-Z]+)$/,
      m => `氢键受体${m[1]}：${m[2]} → ${m[3]}`],
    [/^Contact count delta: (-?\d+)$/, m => `接触数变化：${m[1]}`],
    [/^(\d+) atoms lost, (\d+) gained$/, m => `丢失 ${m[1]} 个原子，新增 ${m[2]} 个`],
    [/^Volume delta: (.+) Å³$/, m => `体积变化：${m[1]} Å³`],
    [/^Polarity: (.+)$/, m => `极性：${m[1]}`],
    [/^Aromaticity: (.+)$/, m => `芳香性：${m[1]}`],
    [/^H-bond donor (.+), acceptor (.+)$/, m => `氢键供体${m[1]}，受体${m[2]}`],
    [/^Side-chain volume (increased|decreased): ([A-Z]+) \(.*$/,
      m => `侧链体积${m[1] === "increased" ? "增大" : "减小"}：${m[2]}`],
    [/^Forward and reverse paths converge on (.+)$/,
      m => `正向与反向路径在「${zh(m[1])}」上收敛`],
    [/^Candidate (.+) change$/, m => `候选机制：${zh(m[1])}变化`],
    [/^pocket-packing$/, () => "口袋堆积"],
    [/^pocket residue-network$/, () => "口袋残基网络"],
    [/^ligand-anchoring$/, () => "配体锚定"],
    [/^Potential ligand-affinity (decrease|increase)$/,
      m => `潜在配体亲和力${m[1] === "decrease" ? "下降" : "上升"}`],
    [/^Potential inhibitor-resistance (increase|decrease)$/,
      m => `潜在抑制剂耐药性${m[1] === "increase" ? "上升" : "下降"}`],
    [/^Candidate loss or reorganization of inhibitor pocket packing$/,
      () => "候选：抑制剂口袋堆积的丢失或重组"],
    [/^Candidate weakening of ligand anchoring$/, () => "候选：配体锚定减弱"],
    [/^Candidate binding-site water-network reorganization$/, () => "候选：结合位点水网络重组"],
    [/^The mutation-driven path and phenotype-driven path independently nominate the same structural mechanism class\.$/,
      () => "突变驱动路径与表型驱动路径独立指向同一类结构机制。"],
    [/^ligand_anchoring$/, () => "配体锚定"],
    [/^pocket_packing$/, () => "口袋堆积"],
    [/^residue_network$/, () => "残基网络"],
    [/^pocket_geometry$/, () => "口袋几何"],
    [/^local_stability$/, () => "局部稳定性"],
    [/^water_network$/, () => "水网络"],
  ];

  function zh(text) {
    if (text == null) return text;
    const s = String(text);
    if (exact[s] !== undefined) return exact[s];
    for (const [re, replacer] of patterns) {
      const m = s.match(re);
      if (m) return replacer(m);
    }
    return s;
  }

  // Translate a path/edge label like "A → B → C" by mapping each segment.
  function zhPath(label) {
    if (label == null) return label;
    return String(label)
      .split(" → ")
      .map(seg => zh(seg))
      .join(" → ");
  }

  return { zh, zhPath, exact };
})();
