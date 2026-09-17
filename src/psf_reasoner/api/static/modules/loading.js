/* Loading animation and error surface. */

const stages = [
  { stage: 'parse', status: '📖 解析蛋白结构...', pct: 10 },
  { stage: 'qc', status: '🔬 结构质量评估中...', pct: 25 },
  { stage: 'physical', status: '⚛️ 计算物理证据 (SASA·相互作用·口袋几何)...', pct: 45 },
  { stage: 'reason', status: '🧬 机制推理与因果图生成...', pct: 70 },
  { stage: 'synthesize', status: '🧪 合成报告与验证计划...', pct: 90 },
];

export function initLoadingModule({ els }) {
  let loadingTimer = null;

  function startLoading() {
    const bar = document.getElementById('bio-progress-bar');
    const status = document.getElementById('bio-status');
    const stageEls = document.querySelectorAll('.bio-stage');
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
    document.querySelectorAll('.bio-stage').forEach(s => s.classList.add('done'));
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

  return { setLoading, stopLoading, showError };
}
