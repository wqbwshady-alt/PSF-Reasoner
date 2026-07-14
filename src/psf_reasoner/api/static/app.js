const examplePayload = {
  structure: { path: "examples/data/1sdt.cif", format: "mmcif", model_index: 0 },
  mutant_structure: { path: "examples/data/1sdv.cif", format: "mmcif", model_index: 0 },
  ligand: { identifier: "MK1" },
  mutation: { notation: "V82A", chain: "A" },
  phenotype: { name: "drug_resistance", direction: "increase" },
  study_context: "HIV-1 蛋白酶 V82A 配対晶体结构示例"
};

const reverseExamplePayload = {
  structure: { path: "examples/data/1sdt.cif", format: "mmcif", model_index: 0 },
  ligand: { identifier: "MK1" },
  phenotype: { name: "drug_resistance", direction: "increase" },
  study_context: "HIV-1 蛋白酶 — 从耐药性表型反向推理结构机制"
};

const elements = {
  form: document.querySelector("#analysis-form"),
  example: document.querySelector("#run-example"),
  reverseExample: document.querySelector("#run-reverse-example"),
  status: document.querySelector("#api-status"),
  empty: document.querySelector("#empty-state"),
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  report: document.querySelector("#report"),
  submit: document.querySelector("#submit-analysis"),
  viewerPanel: document.querySelector("#viewer-panel"),
  viewer3d: document.querySelector("#viewer-3d"),
  viewerClose: document.querySelector("#viewer-close"),
  viewerTabs: document.querySelectorAll(".viewer-tab"),
};

// ---------------------------------------------------------------------------
// 3D 查看器
// ---------------------------------------------------------------------------

let viewer = null;
let referenceData = null;
let mutantData = null;
let viewerMode = "reference";

function initViewer() {
  if (viewer) return;
  try {
    viewer = $3Dmol.createViewer("viewer-3d", {
      backgroundColor: "white",
      antialias: true,
    });
  } catch (e) {
    console.error("3Dmol 初始化失败:", e);
    showError("3D 查看器初始化失败，请检查浏览器控制台。");
    return;
  }
}

async function loadStructureData(structurePath, uploadId) {
  const params = new URLSearchParams();
  if (uploadId) {
    params.set("upload_id", uploadId);
  } else {
    params.set("path", structurePath);
  }
  const response = await fetch(`/structure?${params.toString()}`);
  if (!response.ok) throw new Error(`无法加载结构文件: ${structurePath}`);
  return response.text();
}

async function showStructure(structurePathOnServer, mutationChain, mutationResNum, ligandId, uploadId) {
  elements.viewerPanel.classList.remove("hidden");
  initViewer();
  if (!viewer) return;

  try {
    viewer.removeAllSurfaces();
    viewer.removeAllModels();

    const pdbText = await loadStructureData(structurePathOnServer, uploadId);
    if (viewerMode === "reference") referenceData = pdbText;
    else mutantData = pdbText;

    viewer.addModel(pdbText, "pdb");

    viewer.setStyle({ chain: mutationChain || undefined }, { cartoon: { color: "spectrum" } });

    if (mutationResNum) {
      viewer.setStyle(
        { chain: mutationChain || undefined, resi: mutationResNum },
        { cartoon: { color: "#ff6b6b" }, stick: { radius: 0.35, color: "#ff6b6b" } }
      );
    }

    if (ligandId) {
      viewer.setStyle(
        { resn: ligandId.toUpperCase() },
        { stick: { radius: 0.25, color: "#4ecdc4" } }
      );
    }

    try {
      const model = viewer.getModel();
      if (model) {
        const ligandAtoms = model.selectedAtoms({ resn: ligandId.toUpperCase() });
        if (ligandAtoms && ligandAtoms.length > 0) {
          const nearby = model.selectedAtoms({
            resn: ligandId.toUpperCase(),
            byres: true,
            expand: 5,
          });
          if (nearby) {
            const nearbyResidues = new Set();
            for (const atom of nearby) {
              if (atom.resn !== ligandId.toUpperCase() && atom.resn !== "HOH") {
                nearbyResidues.add(`${atom.chain}:${atom.resi}`);
              }
            }
            for (const key of nearbyResidues) {
              const [chain, resi] = key.split(":");
              viewer.setStyle(
                { chain, resi },
                { stick: { radius: 0.15, color: "#ffe66d" }, cartoon: { color: "#ffe66d", opacity: 0.5 } }
              );
            }
          }
        }
      }
    } catch (e) {
      console.warn("接触残基高亮跳过:", e);
    }

    viewer.zoomTo();
    viewer.render();
    viewer.resize();
  } catch (e) {
    console.error("结构渲染失败:", e);
    showError("3D 结构渲染失败: " + e.message);
  }
}

function switchViewerMode(mode) {
  viewerMode = mode;
  elements.viewerTabs.forEach(tab => tab.classList.toggle("active", tab.dataset.mode === mode));
}

elements.viewerClose.addEventListener("click", () => {
  elements.viewerPanel.classList.add("hidden");
});

elements.viewerTabs.forEach(tab => {
  tab.addEventListener("click", () => {
    switchViewerMode(tab.dataset.mode);
  });
});

// ---------------------------------------------------------------------------
// UI 工具函数
// ---------------------------------------------------------------------------

function setLoading(active) {
  elements.loading.classList.toggle("hidden", !active);
  elements.empty.classList.add("hidden");
  elements.error.classList.add("hidden");
  elements.report.classList.add("hidden");
  elements.example.disabled = active;
  elements.submit.disabled = active;
}

function showError(message) {
  elements.loading.classList.add("hidden");
  elements.error.textContent = message;
  elements.error.classList.remove("hidden");
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "分析请求失败，请重试。");
  return body;
}

function number(value, unit = "") {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(3)}${unit ? ` ${unit}` : ""}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
}

function metric(label, value, detail) {
  return `<article class="metric"><span class="metric-label">${escapeHtml(label)}</span><strong class="metric-value">${escapeHtml(value)}</strong><small class="metric-detail">${escapeHtml(detail)}</small></article>`;
}

function claimCard(item, showMeasurement = true) {
  const tagClasses = {
    computed: "tag-computed", required: "tag-required", inferred: "tag-inferred",
    increase: "tag-increase", decrease: "tag-decrease", change: "tag-change", unchanged: "tag-unchanged"
  };
  const tag = item.status || item.direction || item.mechanism_type || item.function_type || "";
  const tagClass = tagClasses[tag] || "";
  const measurement = item.measurement;
  const value = showMeasurement && measurement
    ? `${measurement.name}: ${number(measurement.value, measurement.unit)}`
    : "";
  const confidence = item.confidence !== undefined
    ? `<span class="confidence-badge">${Math.round(item.confidence * 100)}%</span>`
    : "";
  const provenance = item.provenance
    ? `<div class="provenance">来源: ${item.provenance.map(p => escapeHtml(p.source)).join(", ")}</div>`
    : "";
  return `<article class="claim">
    <div class="claim-top"><strong>${escapeHtml(item.title)}</strong>${confidence}<span class="tag ${tagClass}">${escapeHtml(tag)}</span></div>
    <p>${escapeHtml(item.description)}</p>
    ${value ? `<div class="claim-meta">${escapeHtml(value)}</div>` : ""}
    ${item.limitations && item.limitations.length ? `<div class="claim-limits">局限性: ${escapeHtml(item.limitations.join("; "))}</div>` : ""}
    ${provenance}
  </article>`;
}

function renderPreparation(items) {
  return items.map(item => {
    const issues = item.issues.length
      ? item.issues.map(issue => `<div class="issue">${escapeHtml(issue.message)}</div>`).join("")
      : `<p>未发现问题。</p>`;
    return `<article class="preparation-card">
      <div class="claim-top"><strong>${escapeHtml(item.role)} 结构</strong><span class="tag">${escapeHtml(item.format)}</span></div>
      <p>${item.residue_count} 残基 · ${item.atom_count} 原子 · ${item.water_residue_count} 水分子</p>
      ${issues}
    </article>`;
  }).join("");
}

function renderReport(report) {
  elements.loading.classList.add("hidden");
  const computed = report.physical_evidence.filter(item => item.status === "computed");
  const contact = computed.find(item => item.measurement?.name === "contact_state_delta");
  const distance = computed.find(item => item.measurement?.name === "nearest_heavy_atom_distance_delta");
  const sasa = computed.find(item => item.measurement?.name === "residue_sasa_delta");

  const mutationChain = report.request.mutation?.chain || "A";
  const mutationResNum = report.request.mutation?.residue_number || "82";
  const ligandId = report.request.ligand?.identifier || "";
  const refPath = report.request.structure?.path || "";
  const mutantPath = report.request.mutant_structure?.path || "";
  const refUploadId = report.request.structure?.upload_id || "";
  const mutantUploadId = report.request.mutant_structure?.upload_id || "";

  elements.report.innerHTML = `
    <div class="report-header">
      <div>
        <p class="eyebrow">${escapeHtml(report.mode)} 报告</p>
        <h2>${escapeHtml(report.request.mutation?.notation || "表型分析")}</h2>
        <p>${escapeHtml(report.request.ligand.identifier)} · ${escapeHtml(report.report_id)}</p>
      </div>
      <div class="confidence"><strong>${Math.round(report.confidence * 100)}%</strong><span>综合置信度</span></div>
    </div>
    <div class="metrics">
      ${metric("计算证据", String(computed.length), "坐标推导")}
      ${metric("距离变化", distance ? number(distance.measurement.value, "Å") : "—", distance ? "突变体 − 参考" : "单结构")}
      ${metric("接触变化", contact ? number(contact.measurement.value) : "—", contact ? "1 新增 · -1 丢失" : "单结构")}
      ${metric("SASA 变化", sasa ? number(sasa.measurement.value, "Å²") : "—", sasa ? "突变体 − 参考" : "未比较")}
    </div>
    <div class="viewer-buttons">
      ${refPath ? `<button class="viewer-btn" data-path="${escapeHtml(refPath)}" data-upload-id="${escapeHtml(refUploadId)}" data-type="reference" data-chain="${escapeHtml(mutationChain)}" data-resnum="${escapeHtml(mutationResNum)}" data-ligand="${escapeHtml(ligandId)}">查看参考结构 (WT)</button>` : ""}
      ${mutantPath ? `<button class="viewer-btn" data-path="${escapeHtml(mutantPath)}" data-upload-id="${escapeHtml(mutantUploadId)}" data-type="mutant" data-chain="${escapeHtml(mutationChain)}" data-resnum="${escapeHtml(mutationResNum)}" data-ligand="${escapeHtml(ligandId)}">查看突变体</button>` : ""}
    </div>
    <section class="report-section"><h3>结构准备</h3><div class="preparation-grid">${renderPreparation(report.structure_preparation)}</div></section>
    <section class="report-section"><h3>物理证据</h3><div class="claim-list">${report.physical_evidence.map(item => claimCard(item)).join("")}</div></section>
    <section class="report-section"><h3>结构机制</h3><div class="claim-list">${report.structural_mechanisms.map(item => claimCard(item, false)).join("")}</div></section>
    <section class="report-section"><h3>功能假设</h3><div class="claim-list">${report.functional_hypotheses.map(item => claimCard(item, false)).join("") || "<p>未生成正向功能假设。</p>"}</div></section>
    ${report.reverse_candidates && report.reverse_candidates.length ? `<section class="report-section"><h3>反向候选</h3><div class="claim-list">${report.reverse_candidates.map(item => claimCard(item, false)).join("")}</div></section>` : ""}
    ${report.consistency_checks && report.consistency_checks.length ? `<section class="report-section"><h3>一致性检查</h3><div class="claim-list">${report.consistency_checks.map(item => claimCard(item, false)).join("")}</div></section>` : ""}
    <section class="report-section"><h3>验证计划</h3><div class="claim-list">${report.validation_plan.steps.map(step => `<article class="claim"><div class="claim-top"><strong>${escapeHtml(step.objective)}</strong><span class="tag">优先级 ${step.priority}</span></div><p>${escapeHtml(step.method)}</p><div class="claim-meta">${escapeHtml(step.expected_result)}</div></article>`).join("")}</div></section>
  `;
  elements.report.classList.remove("hidden");

  elements.report.querySelectorAll(".viewer-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.dataset.path;
      const uploadId = btn.dataset.uploadId || "";
      const type = btn.dataset.type;
      const chain = btn.dataset.chain;
      const resnum = btn.dataset.resnum;
      const ligand = btn.dataset.ligand;
      switchViewerMode(type);
      try {
        setLoading(false);
        showStructure(path, chain, resnum, ligand, uploadId);
      } catch (e) {
        showError(`加载 3D 结构失败: ${e.message}`);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// 模式切换
// ---------------------------------------------------------------------------

let analysisMode = "bidirectional";

document.querySelectorAll(".mode-option").forEach(opt => {
  opt.addEventListener("click", () => {
    document.querySelectorAll(".mode-option").forEach(o => o.classList.remove("active"));
    opt.classList.add("active");
    analysisMode = opt.dataset.mode;
    updateFormForMode();
  });
});

function updateFormForMode() {
  const mutFields = document.querySelector("#mutation-fields");
  const mutantFileGroup = document.querySelector("#mutant-file-group");
  const chainGroup = document.querySelector("#chain-group");
  const mutation = document.querySelector("#mutation");
  const chain = document.querySelector("#chain");
  const reference = document.querySelector("#reference-file");

  if (analysisMode === "reverse") {
    mutFields.style.opacity = "0.4";
    mutFields.style.pointerEvents = "none";
    if (mutantFileGroup) { mutantFileGroup.style.opacity = "0.4"; mutantFileGroup.style.pointerEvents = "none"; }
    mutation.required = false;
    chain.required = false;
    mutation.value = "";
    chain.value = "";
    reference.required = true;
  } else {
    mutFields.style.opacity = "1";
    mutFields.style.pointerEvents = "auto";
    if (mutantFileGroup) { mutantFileGroup.style.opacity = "1"; mutantFileGroup.style.pointerEvents = "auto"; }
    mutation.required = analysisMode !== "reverse";
    reference.required = true;
    if (!mutation.value) mutation.value = "V82A";
    if (!chain.value) chain.value = "A";
  }
}

// ---------------------------------------------------------------------------
// 操作
// ---------------------------------------------------------------------------

async function runExample() {
  setLoading(true);
  try {
    const report = await requestJson("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(examplePayload),
    });
    renderReport(report);
  } catch (error) {
    showError(error.message);
  } finally {
    elements.loading.classList.add("hidden");
    elements.example.disabled = false;
    elements.submit.disabled = false;
  }
}

async function runReverseExample() {
  setLoading(true);
  try {
    const report = await requestJson("/reverse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reverseExamplePayload),
    });
    renderReport(report);
  } catch (error) {
    showError(error.message);
  } finally {
    elements.loading.classList.add("hidden");
    elements.reverseExample.disabled = false;
    elements.submit.disabled = false;
  }
}

elements.example.addEventListener("click", runExample);
elements.reverseExample.addEventListener("click", runReverseExample);

elements.form.addEventListener("submit", async event => {
  event.preventDefault();
  setLoading(true);
  try {
    const formData = new FormData(elements.form);
    const endpoint = analysisMode === "reverse" ? "/reverse-upload" : "/analyze-upload";
    const report = await requestJson(endpoint, { method: "POST", body: formData });
    renderReport(report);
  } catch (error) {
    showError(error.message);
  } finally {
    elements.loading.classList.add("hidden");
    elements.example.disabled = false;
    elements.reverseExample.disabled = false;
    elements.submit.disabled = false;
  }
});

fetch("/health")
  .then(response => {
    if (!response.ok) throw new Error();
    elements.status.textContent = "服务已连接";
  })
  .catch(() => {
    elements.status.textContent = "服务未连接";
    elements.status.classList.add("offline");
  });
