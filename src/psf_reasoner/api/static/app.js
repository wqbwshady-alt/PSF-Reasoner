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
  submit: document.querySelector("#submit-analysis")
};

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

function claimCard(item, showMeasurement = true) {
  const tag = item.status || item.direction || item.mechanism_type || item.function_type || "result";
  const measurement = item.measurement;
  const value = showMeasurement && measurement ? `${measurement.name}: ${number(measurement.value, measurement.unit)}` : "";
  return `<article class="claim">
    <div class="claim-top"><strong>${escapeHtml(item.title)}</strong><span class="tag ${tag}">${escapeHtml(tag)}</span></div>
    <p>${escapeHtml(item.description)}</p>
    ${value ? `<div class="claim-meta">${escapeHtml(value)}${measurement.reference_value !== null && measurement.reference_value !== undefined ? ` · ref ${escapeHtml(String(measurement.reference_value))}` : ""}</div>` : ""}
  </article>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
}

function metric(label, value, detail) {
  return `<article class="metric"><span class="metric-label">${escapeHtml(label)}</span><strong class="metric-value">${escapeHtml(value)}</strong><small class="metric-detail">${escapeHtml(detail)}</small></article>`;
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
  elements.report.innerHTML = `
    <div class="report-header">
      <div><p class="eyebrow">${escapeHtml(report.mode)} report</p><h2>${escapeHtml(report.request.mutation?.notation || "Phenotype analysis")}</h2><p>${escapeHtml(report.request.ligand.identifier)} · ${escapeHtml(report.report_id)}</p></div>
      <div class="confidence"><strong>${Math.round(report.confidence * 100)}%</strong><span>report confidence</span></div>
    </div>
    <div class="metrics">
      ${metric("Computed evidence", String(computed.length), "coordinate-derived")}
      ${metric("Distance delta", distance ? number(distance.measurement.value, "Å") : "—", distance ? "mutant minus reference" : "single structure")}
      ${metric("Contact delta", contact ? number(contact.measurement.value) : "—", contact ? "1 gained · -1 lost" : "single structure")}
      ${metric("SASA delta", sasa ? number(sasa.measurement.value, "Å²") : "—", sasa ? "mutant minus reference" : "not compared")}
    </div>
    <section class="report-section"><h3>Structure preparation</h3><div class="preparation-grid">${renderPreparation(report.structure_preparation)}</div></section>
    <section class="report-section"><h3>Physical evidence</h3><div class="claim-list">${report.physical_evidence.map(item => claimCard(item)).join("")}</div></section>
    <section class="report-section"><h3>Structural mechanisms</h3><div class="claim-list">${report.structural_mechanisms.map(item => claimCard(item, false)).join("")}</div></section>
    <section class="report-section"><h3>Functional hypotheses</h3><div class="claim-list">${report.functional_hypotheses.map(item => claimCard(item, false)).join("") || "<p>No forward functional hypothesis was generated.</p>"}</div></section>
    <section class="report-section"><h3>Validation plan</h3><div class="claim-list">${report.validation_plan.steps.map(step => `<article class="claim"><div class="claim-top"><strong>${escapeHtml(step.objective)}</strong><span class="tag">P${step.priority}</span></div><p>${escapeHtml(step.method)}</p><div class="claim-meta">${escapeHtml(step.expected_result)}</div></article>`).join("")}</div></section>
  `;
  elements.report.classList.remove("hidden");
}

async function runExample() {
  setLoading(true);
  try {
    renderReport(await requestJson("/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(examplePayload) }));
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

fetch("/health").then(response => {
  if (!response.ok) throw new Error();
  elements.status.textContent = "Local service online";
}).catch(() => {
  elements.status.textContent = "Local service unavailable";
  elements.status.classList.add("offline");
});
