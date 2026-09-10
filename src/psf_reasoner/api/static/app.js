/* PSF-Reasoner v5 Client — honest, wired end-to-end workbench */

const examplePayload = {
  structure: { path: "examples/data/1sdt.cif", format: "mmcif", model_index: 0 },
  mutant_structure: { path: "examples/data/1sdv.cif", format: "mmcif", model_index: 0 },
  ligand: { identifier: "MK1" },
  mutation: { notation: "V82A", chain: "A" },
  phenotype: { name: "drug_resistance", direction: "increase" },
};
const reverseExamplePayload = {
  structure: { path: "examples/data/1sdt.cif", format: "mmcif", model_index: 0 },
  ligand: { identifier: "MK1" },
  phenotype: { name: "drug_resistance", direction: "increase" },
};

let analysisMode = "bidirectional";
let loadingTimer = null;
let lastPayload = null; // last combined V3 payload (for localization + export)

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

const els = {
  form: $("#analysis-form"),
  status: $("#api-status"),
  empty: $("#empty-state"),
  loading: $("#loading-state"),
  error: $("#error-state"),
  report: $("#report"),
  submit: $("#submit-analysis"),
  viewerPanel: $("#viewer-panel"),
  viewer3d: $("#viewer-3d"),
  viewerClose: $("#viewer-close"),
};

// ---------------------------------------------------------------------------
// 3D Viewer
// ---------------------------------------------------------------------------
let viewer = null;
let viewerMode = "reference";
let structureData = { reference: null, mutant: null }; // { pdbText, path, uploadId }
let highlightState = { chain: "", resi: "", ligand: "", neighbors: [] };

function initViewer() {
  if (viewer) return;
  try { viewer = $3Dmol.createViewer("viewer-3d", { backgroundColor: "white", antialias: true }); }
  catch (e) { showError("3D 查看器初始化失败: " + e.message); }
}

async function loadPDB(path, uploadId) {
  const p = new URLSearchParams();
  if (uploadId) p.set("upload_id", uploadId); else p.set("path", path);
  const r = await fetch(`/structure?${p.toString()}`);
  if (!r.ok) throw new Error(`无法加载结构: ${path || uploadId}`);
  return r.text();
}

function parseNeighborLabels(labels) {
  // "A:VAL82" -> {chain:"A", resi:"82"}; ignore entries without a residue number
  const out = [];
  for (const label of labels || []) {
    const m = String(label).match(/^([A-Za-z0-9]):[A-Z]{1,3}(\d+)/);
    if (m) out.push({ chain: m[1], resi: m[2] });
  }
  return out;
}

function applyHighlights() {
  if (!viewer) return;
  const chain = highlightState.chain || undefined;
  viewer.setStyle({}, { cartoon: { color: "spectrum" } });
  if (highlightState.resi) {
    viewer.setStyle({ chain, resi: highlightState.resi },
      { cartoon: { color: "#ff6b6b" }, stick: { radius: 0.35, color: "#ff6b6b" } });
  }
  if (highlightState.ligand) {
    viewer.setStyle({ resn: highlightState.ligand.toUpperCase() },
      { stick: { radius: 0.25, color: "#0891b2" } });
  }
  for (const nb of highlightState.neighbors) {
    viewer.setStyle({ chain: nb.chain, resi: nb.resi },
      { cartoon: { color: "#f59e0b" }, stick: { radius: 0.3, color: "#f59e0b" } });
  }
  viewer.render();
}

async function showStructurePanel() {
  els.viewerPanel.classList.remove("hidden");
  initViewer();
  if (!viewer) return;
  try {
    const entry = structureData[viewerMode];
    if (!entry) throw new Error(viewerMode === "mutant" ? "未提供突变体结构" : "未提供参考结构");
    if (!entry.pdbText) entry.pdbText = await loadPDB(entry.path, entry.uploadId);
    viewer.removeAllSurfaces();
    viewer.removeAllModels();
    viewer.addModel(entry.pdbText, "pdb");
    applyHighlights();
    viewer.zoomTo();
    viewer.resize();
  } catch (e) { showError("3D 渲染失败: " + e.message); }
}

els.viewerClose.addEventListener("click", () => els.viewerPanel.classList.add("hidden"));
$$(".viewer-tab").forEach(t => t.addEventListener("click", () => {
  viewerMode = t.dataset.mode;
  $$(".viewer-tab").forEach(x => x.classList.toggle("active", x === t));
  showStructurePanel();
}));

// ---------------------------------------------------------------------------
// Loading animation
// ---------------------------------------------------------------------------
const stages = [
  { stage: 'parse', status: '📖 解析蛋白结构...', pct: 10 },
  { stage: 'qc', status: '🔬 结构质量评估中...', pct: 25 },
  { stage: 'physical', status: '⚛️ 计算物理证据 (SASA·相互作用·口袋几何)...', pct: 45 },
  { stage: 'reason', status: '🧬 机制推理与因果图生成...', pct: 70 },
  { stage: 'synthesize', status: '🧪 合成报告与验证计划...', pct: 90 },
];
function startLoading() {
  const bar = document.getElementById('bio-progress-bar');
  const status = document.getElementById('bio-status');
  const stageEls = $$('.bio-stage');
  if (bar) bar.style.width = '0%';
  if (status) status.textContent = '初始化分析引擎';
  stageEls.forEach(s => s.classList.remove('active', 'done'));
  let idx = 0;
  function adv() {
    if (idx >= stages.length) return;
    const s = stages[idx];
    if (status) status.textContent = s.status;
    if (bar) bar.style.width = s.pct + '%';
    stageEls.forEach(el => {
      if (el.dataset.stage === s.stage) el.classList.add('active');
      else if (stages.findIndex(a => a.stage === el.dataset.stage) < idx) el.classList.add('done');
    });
    idx++;
    if (idx < stages.length) loadingTimer = setTimeout(adv, 3000 + Math.random() * 3000);
  }
  adv();
}
function stopLoading() {
  if (loadingTimer) { clearTimeout(loadingTimer); loadingTimer = null; }
  const bar = document.getElementById('bio-progress-bar');
  if (bar) bar.style.width = '100%';
  const status = document.getElementById('bio-status');
  if (status) status.textContent = '✅ 分析完成';
  $$('.bio-stage').forEach(s => s.classList.add('done'));
}
function setLoading(on) {
  els.loading.classList.toggle("hidden", !on);
  els.empty.classList.add("hidden");
  els.error.classList.add("hidden");
  els.report.classList.add("hidden");
  if (on) startLoading(); else stopLoading();
}
function showError(msg) {
  els.loading.classList.add("hidden");
  els.error.textContent = msg;
  els.error.classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
const esc = v => String(v ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (v, u = "") => v == null ? "—" : `${Number(v).toFixed(3)}${u ? " " + u : ""}`;
async function api(url, opts) {
  const r = await fetch(url, opts);
  const b = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(b.detail || "请求失败");
  return b;
}

function qualLabel(item) {
  let qc = item.qualitative_confidence;
  if (!qc && item.confidence !== undefined) {
    const p = item.confidence;
    qc = p >= 0.70 ? "strong" : p >= 0.45 ? "moderate" : p >= 0.25 ? "weak" : "insufficient";
  }
  const labels = { strong: "Strong", moderate: "Moderate", weak: "Weak", insufficient: "Low confidence" };
  const cls = { strong: "ev-label strong", moderate: "ev-label moderate", weak: "ev-label weak", insufficient: "ev-label weak" };
  if (!qc) return "";
  const h = item.calibration_status === "heuristic" ? " ⚠" : "";
  return `<span class="${cls[qc] || 'ev-label weak'}">${labels[qc] || qc}${h}</span>`;
}

// ---------------------------------------------------------------------------
// Renderers
// ---------------------------------------------------------------------------
function metricEl(label, value, unit) {
  return `<div class="metric"><div class="metric-label">${esc(label)}</div><div class="metric-value">${esc(String(value))}</div><div class="metric-unit">${esc(unit||'')}</div></div>`;
}

function section(title, tag, tagClass) {
  return `<div class="section"><div class="section-header"><h3>${esc(title)}</h3>${tag ? `<span class="section-tag ${tagClass}">${esc(tag)}</span>` : ""}</div>`;
}

function evidenceCard(item) {
  const title = item.title || item.objective || item.evidence_type || item.id || '—';
  const desc = item.description || item.reason || item.method || '';
  const impact = item.impact || item.expected_result || '';
  const m = item.measurement;
  const val = m ? `${m.name}: ${num(m.value, m.unit)}` : "";
  const label = qualLabel(item);
  const borderColor = item.status === 'computed' ? 'var(--teal)' :
    (item.priority ? 'var(--blue)' : 'var(--amber)');
  return `<div class="evidence-card" style="border-left-color:${borderColor}">
    <div class="ev-top"><span class="ev-title">${esc(title)}</span>${label}${item.priority ? `<span style="font-size:.65rem;color:var(--text-muted)">Priority ${item.priority}</span>` : ''}</div>
    ${desc ? `<div class="ev-desc">${esc(desc)}</div>` : ''}
    ${impact ? `<div class="ev-desc">${esc(impact)}</div>` : ''}
    ${val ? `<div class="ev-data">${esc(val)}</div>` : ''}
  </div>`;
}

function renderQC(qc) {
  if (!qc) return "";
  const grades = { comparable: "Comparable", partially_comparable: "Partially comparable", poorly_comparable: "Poorly comparable" };
  return section("Structure Pair QC", grades[qc.grade] || qc.grade, "green") +
    `<div class="metrics">` +
    (qc.reference_resolution != null ? metricEl("参考分辨率", qc.reference_resolution.toFixed(2), "Å") : "") +
    (qc.mutant_resolution != null ? metricEl("突变体分辨率", qc.mutant_resolution.toFixed(2), "Å") : "") +
    (qc.rmsd_overall != null ? metricEl("Cα RMSD", qc.rmsd_overall.toFixed(3), "Å") : "") +
    (qc.rmsd_pocket != null ? metricEl("Pocket RMSD", qc.rmsd_pocket.toFixed(3), "Å") : "") +
    (qc.rmsd_ligand != null ? metricEl("Ligand RMSD", qc.rmsd_ligand.toFixed(3), "Å") : "") +
    `</div>` +
    (qc.background_mutations && qc.background_mutations.length ? `<div style="font-size:.75rem;color:var(--text-muted)">背景突变: ${qc.background_mutations.map(b => esc(b.chain+':'+b.residue_number+' '+b.reference_residue+'→'+b.mutant_residue)).join(', ')}</div>` : "") +
    `</div>`;
}

function renderIdentity(identity) {
  if (!identity) return "";
  return section("Protein Identity（来自结构文件头部）", identity.family_hint || "unknown", identity.family_hint ? "green" : "yellow") +
    `<div style="font-size:.78rem">
      <div>标题: <code>${esc(identity.title || '—')}</code></div>
      <div>实体: ${(identity.entity_names||[]).map(n => `<code>${esc(n)}</code>`).join(', ') || '—'}</div>
      <div>知识库家族: <code>${esc(identity.family_hint || '未识别 — 不附加任何文献证据')}</code></div>
    </div></div>`;
}

function renderLiterature(lit) {
  if (!lit) return "";
  const entries = Object.values(lit.by_grade || {}).flat();
  if (!entries.length) {
    return section("Literature Evidence", "无匹配条目", "yellow") +
      `<div style="font-size:.78rem;color:var(--text-muted)">知识库中没有该蛋白家族的已核实文献条目。结论仅基于结构计算，不附加文献推断。</div></div>`;
  }
  return section("Literature Evidence", `${lit.total_entries} 条`, "green") +
    `<div class="evidence-list">${entries.map(e => `
      <div class="evidence-card" style="border-left-color:var(--blue)">
        <div class="ev-top"><span class="ev-title">${esc(e.evidence_id)}</span><span class="ev-label weak">${esc(e.applicability)}</span></div>
        <div class="ev-desc">${esc(e.claim || '')}</div>
        <div class="ev-data">PMID: ${esc(e.pmid || '—')}${e.measured_value != null ? ` · ${esc(e.measured_value)} ${esc(e.measured_unit||'')}` : ''}</div>
      </div>`).join('')}</div></div>`;
}

function renderContext(ctx) {
  if (!ctx) return "";
  if (ctx.note) {
    return section("Structural Context", "未计算", "yellow") +
      `<div style="font-size:.78rem;color:var(--text-muted)">${esc(ctx.note)}</div></div>`;
  }
  if (!ctx.structural_differences) return "";
  const d = ctx.structural_differences || {};
  const ms = ctx.mutation_site || {};
  const lig = ctx.ligand_decomposition || {};
  const props = [];
  if (d.sidechain_volume_change && d.sidechain_volume_change !== "unchanged") props.push({ l: "体积", v: `${d.sidechain_volume_change} (${d.volume_delta} Å³)` });
  if (d.polarity_change && d.polarity_change !== "unchanged") props.push({ l: "极性", v: d.polarity_change });
  if (d.aromaticity_change && d.aromaticity_change !== "unchanged") props.push({ l: "芳香性", v: d.aromaticity_change });
  if (d.hbond_donor_change && d.hbond_donor_change !== "unchanged") props.push({ l: "H-键供体", v: d.hbond_donor_change });
  if (d.hbond_acceptor_change && d.hbond_acceptor_change !== "unchanged") props.push({ l: "H-键受体", v: d.hbond_acceptor_change });

  return section("Structural Context", "V3", "purple") +
    `<div class="ctx-grid">` +
    `<div class="ctx-prop"><div class="ctx-prop-label">突变</div><div class="ctx-prop-value">${esc(d.wild_type||'?')} → ${esc(d.mutant||'?')} @ ${esc(ms.residue_label||'?')}</div></div>` +
    `<div class="ctx-prop"><div class="ctx-prop-label">最近配体距离</div><div class="ctx-prop-value">${ms.nearest_ligand_distance||'?'} Å</div></div>` +
    `<div class="ctx-prop"><div class="ctx-prop-label">接触变化</div><div class="ctx-prop-value">${d.contact_count_delta||0} contacts · 获得${(d.gained_atoms||[]).length}原子 · 丢失${(d.lost_atoms||[]).length}原子</div></div>` +
    `<div class="ctx-prop"><div class="ctx-prop-label">功能角色</div><div class="ctx-prop-value">${(ms.roles||[]).join(', ')}${ms.is_catalytic?' ⚡催化':''}</div></div>` +
    `</div>` +
    (props.length ? `<div style="margin-top:8px;font-size:.78rem"><strong>化学属性:</strong> ${props.map(p => `<span style="margin:0 8px">${esc(p.l)}: <code>${esc(p.v)}</code></span>`).join('')}</div>` : "") +
    (lig.fragments ? `<div class="lig-fragments">${lig.fragments.map(f => `<span class="lig-frag">${esc(f.id)}: ${esc(f.description)}</span>`).join('')}</div>` : "") +
    (ctx.neighborhood_4a ? `<details style="margin-top:8px;font-size:.72rem"><summary>4Å 邻域 (${ctx.neighborhood_4a.length} 残基)</summary>${ctx.neighborhood_4a.slice(0,10).map(n => `<code>${esc(n.label)}</code> (${n.distance_to_mutation}Å)${n.is_catalytic?' ⚡':''}`).join(' · ')}</details>` : "") +
    `</div>`;
}

function renderCausalGraph(graph) {
  if (!graph || !graph.nodes || !graph.nodes.length) return "";
  const lvlColors = { mutation_property: "#dc2626", local_geometry: "#d97706", interaction: "#0891b2", pocket_conformation: "#059669", binding_consequence: "#2563eb", phenotype: "#7c3aed" };
  const lvlNames = { mutation_property: "突变属性", local_geometry: "局部几何", interaction: "相互作用", pocket_conformation: "口袋构象", binding_consequence: "结合影响", phenotype: "表型" };

  return section("Causal Mechanism Graph", "V3", "purple") +
    `<div class="cg-overview"><div class="cg-dominant">主导: ${esc(graph.dominant_mechanism || '未确定')}</div>` +
    (graph.alternative_mechanisms && graph.alternative_mechanisms.length ? `<div class="cg-alt">替代: ${graph.alternative_mechanisms.slice(0,3).map(m => esc(m)).join(' · ')}</div>` : "") +
    `</div>` +
    `<div class="cg-paths">${(graph.paths||[]).slice(0,4).map(p => `<div class="cg-path"><span class="cg-path-rank">#${p.rank}</span><span class="cg-path-label">${esc(p.label.replace(/_/g, ' '))}</span><span class="cg-path-stats">${p.supporting_evidence_count != null ? p.supporting_evidence_count : p.supporting} supporting · ${p.conflicting_evidence_count != null ? p.conflicting_evidence_count : p.conflicting} conflicting</span></div>`).join('')}</div>` +
    `<div class="cg-nodes">${(graph.nodes||[]).map(n => `<div class="cg-node" style="border-left-color:${lvlColors[n.level]||'#999'}"><strong>${esc(n.mechanism_label)}</strong><span>${esc(n.description?.slice(0,80)||'')}${(n.description||'').length>80?'…':''}</span></div>`).join('')}</div>` +
    (graph.key_uncertainties && graph.key_uncertainties.length ? `<div class="cg-uncertainties"><strong>关键不确定性</strong><ul>${graph.key_uncertainties.map(u => `<li>${esc(u)}</li>`).join('')}</ul></div>` : "") +
    `</div>`;
}

function renderLocalization(loc) {
  if (!loc) return "";
  const hasMutation = loc.mutation_residue_number != null;
  const buttons = [];
  if (hasMutation) {
    buttons.push(`<button class="btn-ghost loc-btn" data-loc="mutation" style="width:auto;display:inline-block;margin-right:6px">定位突变位点 ${esc(loc.mutation_chain||'')}:${esc(loc.mutation_residue_number)}</button>`);
  }
  if (loc.ligand) {
    buttons.push(`<button class="btn-ghost loc-btn" data-loc="ligand" style="width:auto;display:inline-block;margin-right:6px">定位配体 ${esc(loc.ligand)}</button>`);
  }
  if ((loc.neighborhood_4a||[]).length) {
    buttons.push(`<button class="btn-ghost loc-btn" data-loc="neighbors" style="width:auto;display:inline-block">定位4Å邻域 (${loc.neighborhood_4a.length})</button>`);
  }
  if (!buttons.length) return "";
  return `<div style="margin-top:10px">${buttons.join('')}</div>`;
}

function renderGapAnalysis(mechanisms, missing) {
  const mechs = mechanisms || [];
  const miss = missing || [];
  if (!mechs.length && !miss.length) return "";

  const rows = [];
  if (miss.length) {
    const byType = {};
    miss.forEach(m => {
      const t = m.evidence_type || 'other';
      if (!byType[t]) byType[t] = [];
      byType[t].push(m);
    });
    for (const [type, items] of Object.entries(byType)) {
      rows.push({
        label: type.replace(/_/g, ' '),
        covered: 0,
        total: items.length,
        detail: items.map(i => i.reason || i.impact).filter(Boolean).slice(0, 2).join('; ')
      });
    }
  }

  mechs.forEach(m => {
    const sb = m.score_breakdown;
    const eg = m.evidence_graph;
    if (sb) {
      rows.push({ label: m.title || m.mechanism_type, covered: sb.supporting_evidence_count, total: sb.supporting_evidence_count + sb.missing_evidence_count });
    } else if (eg) {
      rows.push({ label: m.title || m.mechanism_type, covered: (eg.supporting||[]).length, total: (eg.supporting||[]).length + (eg.missing||[]).length });
    }
  });

  if (!rows.length) return "";

  return section("Evidence Gap Analysis", "V2", "blue") +
    rows.map(r => {
      const pct = r.total > 0 ? Math.round(r.covered / r.total * 100) : (r.covered > 0 ? 100 : 0);
      return `<div class="gap-row">
        <div class="gap-label">${esc(r.label)}</div>
        <div class="gap-bar-wrap"><div class="gap-bar-fill" style="width:${pct}%"></div></div>
        <div class="gap-pct">${r.covered}/${r.total}</div>
        ${r.detail ? `<div style="font-size:.65rem;color:var(--text-muted);grid-column:1/-1">${esc(r.detail)}</div>` : ''}
      </div>`;
    }).join("") + `</div>`;
}

function renderSummary(mechanisms, hypotheses, validation) {
  const mechs = mechanisms || [];
  const hyps = hypotheses || [];
  const steps = (validation?.steps || []).slice(0, 3);
  const strong = mechs.filter(m => m.confidence >= 0.7 && m.category === "evidence_supported");
  const moderate = mechs.filter(m => m.confidence >= 0.45 && m.confidence < 0.7);
  const weak = mechs.filter(m => m.confidence < 0.45 || m.category === "hypothesized");

  return section("Executive Summary", "", "green") +
    `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px">` +
    `<div style="padding:8px;background:var(--green-light);border-radius:4px"><div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.5px;color:var(--green)">Strongly Supported</div><div style="font-size:.75rem;font-weight:600">${strong.length ? strong.map(m=>esc(m.title)).join(', ') : '—'}</div></div>` +
    `<div style="padding:8px;background:var(--amber-light);border-radius:4px"><div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.5px;color:var(--amber)">Moderately Supported</div><div style="font-size:.75rem;font-weight:600">${moderate.length ? moderate.map(m=>esc(m.title)).join(', ') : '—'}</div></div>` +
    `<div style="padding:8px;background:var(--red-light);border-radius:4px"><div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.5px;color:var(--red)">Weakly Supported</div><div style="font-size:.75rem;font-weight:600">${weak.length ? weak.map(m=>esc(m.title)).join(', ') : '—'}</div></div>` +
    `</div>` +
    (hyps.length ? `<div style="font-size:.78rem;margin:6px 0">功能方向: ${hyps.map(h => `${h.direction==='decrease'?'↓':'↑'} ${esc(h.title)}`).join(' · ')}</div>` : "") +
    (steps.length ? `<div style="font-size:.72rem;color:var(--text-muted);margin-top:6px">下一步验证: ${steps.map(s => `<strong>P${s.priority}</strong> ${esc(s.objective)}`).join(' → ')}</div>` : "") +
    `</div>`;
}

function renderReport(data) {
  const r = data.v2_report || data;
  stopLoading();
  els.loading.classList.add("hidden");

  if (!r || !r.physical_evidence) {
    els.error.textContent = 'Report data structure error: ' + JSON.stringify(Object.keys(data || {})).slice(0, 200);
    els.error.classList.remove("hidden");
    return;
  }

  lastPayload = data.v2_report ? data : null;

  const computed = (r.physical_evidence || []).filter(e => e.status === "computed");
  const contact = computed.find(e => e.measurement?.name === "contact_state_delta");
  const distance = computed.find(e => e.measurement?.name === "nearest_heavy_atom_distance_delta");
  const sasa = computed.find(e => e.measurement?.name === "residue_sasa_delta");

  const ligId = r.request?.ligand?.identifier || "";
  const refPath = r.request?.structure?.path || "";
  const mutPath = r.request?.mutant_structure?.path || "";
  const refUpId = r.request?.structure?.upload_id || "";
  const mutUpId = r.request?.mutant_structure?.upload_id || "";

  // Whitelist: only the exact value "calibrated" may render as calibrated.
  const calStatus = r.calibration_status;
  const calBadge = calStatus === "calibrated" ? "CALIBRATED"
    : calStatus === "heuristic" ? "⚠ 启发式（未校准）" : "⚠ 校准状态未知";

  let html = `
    <div class="rpt-header">
      <div>
        <div class="rpt-eyebrow">${esc(r.mode || 'analysis')} Report</div>
        <div class="rpt-title">${esc(r.request?.mutation?.notation || 'Analysis')}</div>
        <div class="rpt-subtitle">${esc(r.request?.ligand?.identifier || '')} · ${esc(r.report_id || '')}</div>
      </div>
      <div class="rpt-badge ${calStatus === "heuristic" ? "heuristic" : ""}">${calBadge}</div>
    </div>`;

  // Export row (only when a combined V3 payload exists)
  if (lastPayload) {
    html += `<div style="margin:10px 0">
      <button class="btn-ghost export-btn" data-format="json" style="width:auto;display:inline-block;margin-right:6px">导出 JSON</button>
      <button class="btn-ghost export-btn" data-format="csv" style="width:auto;display:inline-block;margin-right:6px">导出 CSV</button>
      <button class="btn-ghost export-btn" data-format="pymol" style="width:auto;display:inline-block">导出 PyMOL 脚本</button>
    </div>`;
  }

  // Protein identity + literature (V3)
  if (data.protein_identity) html += renderIdentity(data.protein_identity);
  if (data.v3_literature) html += renderLiterature(data.v3_literature);

  // V3 context + causal graph
  if (data.v3_context) html += renderContext(data.v3_context);
  if (data.v3_causal_graph) html += renderCausalGraph(data.v3_causal_graph);

  // Executive Summary
  html += renderSummary(r.structural_mechanisms, r.functional_hypotheses, r.validation_plan);

  // QC
  html += renderQC(r.structure_qc);

  // Metrics
  html += section("Physical Evidence", `${computed.length} computed`, "green") +
    `<div class="metrics">` +
    metricEl("计算证据", computed.length, "项") +
    metricEl("距离变化", distance ? num(distance.measurement?.value, "Å") : "—", "mutant − ref") +
    metricEl("接触变化", contact ? num(contact.measurement?.value) : "—", contact ? "1=新增/-1=丢失" : "单结构") +
    metricEl("SASA 变化", sasa ? num(sasa.measurement?.value, "Å²") : "—", sasa ? "mutant − ref" : "未比较") +
    `</div>` +
    `<div class="evidence-list">${r.physical_evidence.map(evidenceCard).join('')}</div>` +
    `<div style="margin-top:10px">
      <button class="btn-ghost struct-btn" data-type="reference" style="width:auto;display:inline-block;margin-right:6px">查看 WT 结构</button>
      ${mutPath || mutUpId ? `<button class="btn-ghost struct-btn" data-type="mutant" style="width:auto;display:inline-block">查看 Mutant 结构</button>` : ""}
    </div>` +
    `</div>`;

  // Mechanisms
  html += section("Structural Mechanisms", "", "yellow") +
    `<div class="evidence-list">${(r.structural_mechanisms||[]).map(m => evidenceCard(m)).join('')}</div></div>`;

  // Functional
  if ((r.functional_hypotheses||[]).length) {
    html += section("Functional Hypotheses", "", "blue") +
      `<div class="evidence-list">${r.functional_hypotheses.map(h => evidenceCard(h)).join('')}</div></div>`;
  }

  // Consistency
  if ((r.consistency_checks||[]).length) {
    html += section("Consistency", "", "purple") +
      `<div class="evidence-list">${r.consistency_checks.map(c => evidenceCard(c)).join('')}</div></div>`;
  }

  // Gap Analysis
  html += renderGapAnalysis(r.structural_mechanisms, r.missing_evidence);

  // Missing Evidence + Validation
  if ((r.missing_evidence||[]).length) {
    html += section("Missing Evidence", "", "yellow") +
      `<div class="evidence-list">${r.missing_evidence.map(e => evidenceCard(e)).join('')}</div></div>`;
  }
  if ((r.validation_plan?.steps||[]).length) {
    html += section("Validation Plan", "", "blue") +
      `<div class="evidence-list">${r.validation_plan.steps.map(s => evidenceCard(s)).join('')}</div></div>`;
  }

  // Localization (3D evidence anchoring)
  if (data.evidence_localization) html += renderLocalization(data.evidence_localization);

  // Limitations
  if ((r.limitations||[]).length) {
    html += section("Limitations", "必读", "red") +
      `<ul style="font-size:.75rem;color:var(--text-muted);padding-left:18px;margin:6px 0">${r.limitations.map(l => `<li>${esc(l)}</li>`).join('')}</ul></div>`;
  }

  // Calibration warning
  html += `<div class="cal-warning"><strong>⚠ 未校准启发式评分</strong>所有数值评分为未经实验校准的启发式权重。定性标签 (Strong/Moderate/Weak) 仅供排序参考，不可解释为概率。局部相互作用评分不是 ΔΔG。未提供突变体结构时，不生成任何结构变化。</div>`;

  els.report.innerHTML = html;
  els.report.classList.remove("hidden");

  // Wire structure viewer buttons
  els.report.querySelectorAll(".struct-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      viewerMode = btn.dataset.type;
      structureData.reference = refPath || refUpId ? { pdbText: null, path: refPath, uploadId: refUpId } : null;
      structureData.mutant = mutPath || mutUpId ? { pdbText: null, path: mutPath, uploadId: mutUpId } : null;
      $$(".viewer-tab").forEach(x => x.classList.toggle("active", x.dataset.mode === viewerMode));
      showStructurePanel();
    });
  });

  // Wire localization buttons
  const loc = data.evidence_localization;
  els.report.querySelectorAll(".loc-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!viewer) initViewer();
      const kind = btn.dataset.loc;
      if (kind === "mutation") {
        highlightState = { chain: loc.mutation_chain || "", resi: String(loc.mutation_residue_number), ligand: "", neighbors: [] };
      } else if (kind === "ligand") {
        highlightState = { chain: "", resi: "", ligand: loc.ligand || "", neighbors: [] };
      } else if (kind === "neighbors") {
        highlightState = { chain: "", resi: "", ligand: loc.ligand || "", neighbors: parseNeighborLabels(loc.neighborhood_4a) };
      }
      els.viewerPanel.classList.remove("hidden");
      showStructurePanel();
    });
  });

  // Wire export buttons
  els.report.querySelectorAll(".export-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const fmt = btn.dataset.format;
      const url = `/export/${encodeURIComponent(lastPayload.report_id)}?format=${fmt}`;
      const a = document.createElement("a");
      a.href = url;
      a.download = "";
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  });
}

// ---------------------------------------------------------------------------
// Analysis flows
// ---------------------------------------------------------------------------
async function runJsonRequest(payload, endpoint) {
  setLoading(true);
  try { renderReport(await api(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })); }
  catch (e) { showError(e.message); }
}

function runExample() {
  runJsonRequest(examplePayload, "/v3/analyze");
}
function runV3() {
  const payload = { ...examplePayload };
  delete payload.phenotype;
  runJsonRequest(payload, "/v3/analyze");
}
function runReverseExample() {
  runJsonRequest(reverseExamplePayload, "/reverse");
}

$("#run-example")?.addEventListener("click", runExample);
$("#run-v3-example")?.addEventListener("click", runV3);

// Real form submission: read the sidebar inputs and send multipart uploads.
els.form.addEventListener("submit", async e => {
  e.preventDefault();
  const refFile = $("#reference-file").files[0];
  if (!refFile) { showError("请先选择参考结构 (WT) 文件，或点击示例按钮。"); return; }
  setLoading(true);
  try {
    if (analysisMode === "reverse") {
      const fd = new FormData();
      fd.append("reference_file", refFile);
      fd.append("ligand", $("#ligand").value.trim());
      fd.append("phenotype", $("#phenotype").value);
      renderReport(await api("/reverse-upload", { method: "POST", body: fd }));
    } else {
      const fd = new FormData();
      fd.append("reference_file", refFile);
      const mutFile = $("#mutant-file").files[0];
      if (mutFile) fd.append("mutant_file", mutFile);
      fd.append("ligand", $("#ligand").value.trim());
      fd.append("mutation", $("#mutation").value.trim().toUpperCase());
      const chain = $("#chain").value.trim();
      if (chain) fd.append("chain", chain);
      fd.append("phenotype", $("#phenotype").value);
      renderReport(await api("/v3/analyze-upload", { method: "POST", body: fd }));
    }
  } catch (err) { showError(err.message); }
});

// Mode switching
$$(".mode-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    $$(".mode-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    analysisMode = tab.dataset.mode;
    const isRev = analysisMode === "reverse";
    $("#mutation-fields").style.opacity = isRev ? "0.4" : "1";
    $("#mutation-fields").style.pointerEvents = isRev ? "none" : "auto";
    $("#mutant-file-group").style.opacity = isRev ? "0.4" : "1";
    $("#mutant-file-group").style.pointerEvents = isRev ? "none" : "auto";
    $("#mutation").required = !isRev;
  });
});

// Health check
fetch("/health").then(r => {
  if (r.ok) $("#api-status").innerHTML = '● 就绪';
  else throw new Error();
}).catch(() => {
  $("#api-status").innerHTML = '● 离线';
  $("#api-status").style.color = 'var(--red)';
});
