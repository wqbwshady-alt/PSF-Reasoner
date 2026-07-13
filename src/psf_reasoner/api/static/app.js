const examplePayload = {
  structure: { path: "examples/data/1sdt.cif", format: "mmcif", model_index: 0 },
  mutant_structure: { path: "examples/data/1sdv.cif", format: "mmcif", model_index: 0 },
  ligand: { identifier: "MK1" },
  mutation: { notation: "V82A", chain: "A" },
  phenotype: { name: "drug_resistance", direction: "increase" },
  study_context: "HIV-1 protease V82A paired crystal-structure example"
};

const elements = {
  form: document.querySelector("#analysis-form"),
  example: document.querySelector("#run-example"),
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
// 3D Viewer
// ---------------------------------------------------------------------------

let viewer = null;
let referenceData = null;
let mutantData = null;
let viewerMode = "reference";

function initViewer() {
  if (viewer) return;
  viewer = $3Dmol.createViewer(elements.viewer3d, {
    backgroundColor: "white",
    antialias: true,
  });
  viewer.resize();
}

async function loadStructureData(structurePath) {
  const response = await fetch(`/structure/${encodeURIComponent(structurePath)}`);
  if (!response.ok) throw new Error(`Failed to load structure: ${structurePath}`);
  return response.text();
}

async function showStructure(structurePathOnServer, mutationChain, mutationResNum, ligandId) {
  initViewer();
  elements.viewerPanel.classList.remove("hidden");
  viewer.removeAllSurfaces();
  viewer.removeAllModels();

  const pdbText = await loadStructureData(structurePathOnServer);
  if (viewerMode === "reference") referenceData = pdbText;
  else mutantData = pdbText;

  viewer.addModel(pdbText, "pdb");

  // Protein cartoon
  viewer.setStyle({ chain: mutationChain || undefined }, { cartoon: { color: "spectrum" } });

  // Mutation site (red sphere on CA)
  if (mutationResNum) {
    viewer.setStyle(
      { chain: mutationChain || undefined, resi: mutationResNum },
      { cartoon: { color: "#ff6b6b" }, stick: { radius: 0.35, color: "#ff6b6b" } }
    );
  }

  // Ligand (teal sticks)
  if (ligandId) {
    viewer.setStyle(
      { resn: ligandId.toUpperCase() },
      { stick: { radius: 0.25, color: "#4ecdc4" } }
    );
  }

  // Contact residues within 5A of ligand (yellow highlight)
  const ligandAtoms = viewer.getModel().selectedAtoms({ resn: ligandId.toUpperCase() });
  if (ligandAtoms && ligandAtoms.length > 0) {
    const nearby = viewer.getModel().selectedAtoms({
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

  viewer.zoomTo();
  viewer.render();
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
// UI helpers
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
  if (!response.ok) throw new Error(body.detail || "Analysis could not be completed.");
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
    ? `<div class="provenance">Source: ${item.provenance.map(p => escapeHtml(p.source)).join(", ")}</div>`
    : "";
  return `<article class="claim">
    <div class="claim-top"><strong>${escapeHtml(item.title)}</strong>${confidence}<span class="tag ${tagClass}">${escapeHtml(tag)}</span></div>
    <p>${escapeHtml(item.description)}</p>
    ${value ? `<div class="claim-meta">${escapeHtml(value)}</div>` : ""}
    ${item.limitations && item.limitations.length ? `<div class="claim-limits">Limitations: ${escapeHtml(item.limitations.join("; "))}</div>` : ""}
    ${provenance}
  </article>`;
}

function renderPreparation(items) {
  return items.map(item => {
    const issues = item.issues.length
      ? item.issues.map(issue => `<div class="issue">${escapeHtml(issue.message)}</div>`).join("")
      : `<p>No preparation warnings.</p>`;
    return `<article class="preparation-card">
      <div class="claim-top"><strong>${escapeHtml(item.role)} structure</strong><span class="tag">${escapeHtml(item.format)}</span></div>
      <p>${item.residue_count} residues · ${item.atom_count} atoms · ${item.water_residue_count} waters</p>
      ${issues}
    </article>`;
  }).join("");
}

function renderReport(report) {
  const computed = report.physical_evidence.filter(item => item.status === "computed");
  const contact = computed.find(item => item.measurement?.name === "contact_state_delta");
  const distance = computed.find(item => item.measurement?.name === "nearest_heavy_atom_distance_delta");
  const sasa = computed.find(item => item.measurement?.name === "residue_sasa_delta");

  // Extract mutation info for viewer
  const mutationChain = report.request.mutation?.chain || "A";
  const mutationResNum = report.request.mutation?.residue_number || "82";
  const ligandId = report.request.ligand?.identifier || "";
  const refPath = report.request.structure?.path || "";
  const mutantPath = report.request.mutant_structure?.path || "";

  elements.report.innerHTML = `
    <div class="report-header">
      <div>
        <p class="eyebrow">${escapeHtml(report.mode)} report</p>
        <h2>${escapeHtml(report.request.mutation?.notation || "Phenotype analysis")}</h2>
        <p>${escapeHtml(report.request.ligand.identifier)} · ${escapeHtml(report.report_id)}</p>
      </div>
      <div class="confidence"><strong>${Math.round(report.confidence * 100)}%</strong><span>report confidence</span></div>
    </div>
    <div class="metrics">
      ${metric("Computed evidence", String(computed.length), "coordinate-derived")}
      ${metric("Distance delta", distance ? number(distance.measurement.value, "Å") : "—", distance ? "mutant minus reference" : "single structure")}
      ${metric("Contact delta", contact ? number(contact.measurement.value) : "—", contact ? "1 gained · -1 lost" : "single structure")}
      ${metric("SASA delta", sasa ? number(sasa.measurement.value, "Å²") : "—", sasa ? "mutant minus reference" : "not compared")}
    </div>
    <div class="viewer-buttons">
      ${refPath ? `<button class="viewer-btn" data-path="${escapeHtml(refPath)}" data-type="reference" data-chain="${escapeHtml(mutationChain)}" data-resnum="${escapeHtml(mutationResNum)}" data-ligand="${escapeHtml(ligandId)}">View Reference (WT)</button>` : ""}
      ${mutantPath ? `<button class="viewer-btn" data-path="${escapeHtml(mutantPath)}" data-type="mutant" data-chain="${escapeHtml(mutationChain)}" data-resnum="${escapeHtml(mutationResNum)}" data-ligand="${escapeHtml(ligandId)}">View Mutant</button>` : ""}
    </div>
    <section class="report-section"><h3>Structure preparation</h3><div class="preparation-grid">${renderPreparation(report.structure_preparation)}</div></section>
    <section class="report-section"><h3>Physical evidence</h3><div class="claim-list">${report.physical_evidence.map(item => claimCard(item)).join("")}</div></section>
    <section class="report-section"><h3>Structural mechanisms</h3><div class="claim-list">${report.structural_mechanisms.map(item => claimCard(item, false)).join("")}</div></section>
    <section class="report-section"><h3>Functional hypotheses</h3><div class="claim-list">${report.functional_hypotheses.map(item => claimCard(item, false)).join("") || "<p>No forward functional hypothesis was generated.</p>"}</div></section>
    ${report.reverse_candidates && report.reverse_candidates.length ? `<section class="report-section"><h3>Reverse candidates</h3><div class="claim-list">${report.reverse_candidates.map(item => claimCard(item, false)).join("")}</div></section>` : ""}
    ${report.consistency_checks && report.consistency_checks.length ? `<section class="report-section"><h3>Consistency checks</h3><div class="claim-list">${report.consistency_checks.map(item => claimCard(item, false)).join("")}</div></section>` : ""}
    <section class="report-section"><h3>Validation plan</h3><div class="claim-list">${report.validation_plan.steps.map(step => `<article class="claim"><div class="claim-top"><strong>${escapeHtml(step.objective)}</strong><span class="tag">P${step.priority}</span></div><p>${escapeHtml(step.method)}</p><div class="claim-meta">${escapeHtml(step.expected_result)}</div></article>`).join("")}</div></section>
  `;
  elements.report.classList.remove("hidden");

  // Wire viewer buttons
  elements.report.querySelectorAll(".viewer-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.dataset.path;
      const type = btn.dataset.type;
      const chain = btn.dataset.chain;
      const resnum = btn.dataset.resnum;
      const ligand = btn.dataset.ligand;
      switchViewerMode(type);
      try {
        setLoading(false);
        showStructure(path, chain, resnum, ligand);
      } catch (e) {
        showError(`Failed to load 3D structure: ${e.message}`);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Actions
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
    elements.example.disabled = false;
    elements.submit.disabled = false;
  }
}

elements.example.addEventListener("click", runExample);
elements.form.addEventListener("submit", async event => {
  event.preventDefault();
  setLoading(true);
  try {
    const formData = new FormData(elements.form);
    const report = await requestJson("/analyze-upload", { method: "POST", body: formData });
    renderReport(report);
  } catch (error) {
    showError(error.message);
  } finally {
    elements.example.disabled = false;
    elements.submit.disabled = false;
  }
});

fetch("/health")
  .then(response => {
    if (!response.ok) throw new Error();
    elements.status.textContent = "Local service online";
  })
  .catch(() => {
    elements.status.textContent = "Local service unavailable";
    elements.status.classList.add("offline");
  });
