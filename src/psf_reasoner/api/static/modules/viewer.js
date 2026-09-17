/* 3Dmol.js viewer — loading, highlighting, and structure panels. */

let viewer = null;
let viewerMode = "reference";
let structureData = { reference: null, mutant: null }; // { pdbText, path, uploadId }
let highlightState = { chain: "", resi: "", ligand: "", neighbors: [] };

function initViewerModule({ els, showError }) {
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
  document.querySelectorAll(".viewer-tab").forEach(t => t.addEventListener("click", () => {
    viewerMode = t.dataset.mode;
    document.querySelectorAll(".viewer-tab").forEach(x => x.classList.toggle("active", x === t));
    showStructurePanel();
  }));

  return {
    showStructurePanel,
    initViewer,
    parseNeighborLabels,
    setViewerMode: mode => { viewerMode = mode; },
    setStructureData: data => { structureData = data; },
    setHighlightState: state => { highlightState = state; },
    isViewerReady: () => viewer != null,
  };
}

export { initViewerModule };
