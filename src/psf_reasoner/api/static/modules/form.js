/* Analysis flows — example buttons, form submission, and mode switching. */

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

function initFormModule({ els, api, renderReport, setLoading, showError }) {
  let analysisMode = "bidirectional";

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

  document.querySelector("#run-example")?.addEventListener("click", runExample);
  document.querySelector("#run-v3-example")?.addEventListener("click", runV3);

  // Real form submission: read the sidebar inputs and send multipart uploads.
  els.form.addEventListener("submit", async e => {
    e.preventDefault();
    const refFile = document.querySelector("#reference-file").files[0];
    if (!refFile) { showError("请先选择参考结构 (WT) 文件，或点击示例按钮。"); return; }
    setLoading(true);
    try {
      if (analysisMode === "reverse") {
        const fd = new FormData();
        fd.append("reference_file", refFile);
        fd.append("ligand", document.querySelector("#ligand").value.trim());
        fd.append("phenotype", document.querySelector("#phenotype").value);
        renderReport(await api("/reverse-upload", { method: "POST", body: fd }));
      } else {
        const fd = new FormData();
        fd.append("reference_file", refFile);
        const mutFile = document.querySelector("#mutant-file").files[0];
        if (mutFile) fd.append("mutant_file", mutFile);
        fd.append("ligand", document.querySelector("#ligand").value.trim());
        fd.append("mutation", document.querySelector("#mutation").value.trim().toUpperCase());
        const chain = document.querySelector("#chain").value.trim();
        if (chain) fd.append("chain", chain);
        fd.append("phenotype", document.querySelector("#phenotype").value);
        renderReport(await api("/v3/analyze-upload", { method: "POST", body: fd }));
      }
    } catch (err) { showError(err.message); }
  });

  // Mode switching
  document.querySelectorAll(".mode-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      analysisMode = tab.dataset.mode;
      const isRev = analysisMode === "reverse";
      document.querySelector("#mutation-fields").style.opacity = isRev ? "0.4" : "1";
      document.querySelector("#mutation-fields").style.pointerEvents = isRev ? "none" : "auto";
      document.querySelector("#mutant-file-group").style.opacity = isRev ? "0.4" : "1";
      document.querySelector("#mutant-file-group").style.pointerEvents = isRev ? "none" : "auto";
      document.querySelector("#mutation").required = !isRev;
    });
  });
}

export { initFormModule };
