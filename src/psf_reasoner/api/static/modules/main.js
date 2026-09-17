/* PSF-Reasoner v6 Client — honest, wired end-to-end workbench (module entry). */

import { api } from "./api.js";
import { initLoadingModule } from "./loading.js";
import { initViewerModule } from "./viewer.js";
import { initRenderModule } from "./render.js";
import { initFormModule } from "./form.js";

const $ = s => document.querySelector(s);

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

const loading = initLoadingModule({ els });
const viewer = initViewerModule({ els, showError: loading.showError });
const render = initRenderModule({ els, viewer, stopLoading: loading.stopLoading });
initFormModule({
  els,
  api,
  renderReport: render.renderReport,
  setLoading: loading.setLoading,
  showError: loading.showError,
});

// Health check
fetch("/health").then(r => {
  if (r.ok) $("#api-status").innerHTML = '● 就绪';
  else throw new Error();
}).catch(() => {
  $("#api-status").innerHTML = '● 离线';
  $("#api-status").style.color = 'var(--red)';
});
