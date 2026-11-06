/* ============================================================================
   遗物查询 · 渲染样板
   查询（GET search）→ 选择 → 渲染（POST render）→ 调版式 → 保存（POST layout）
   所有请求走 Plugin Page Bridge；直接打开页面时退回同源 fetch。
   ============================================================================ */

// 注意：bridge-sdk.js 由服务端注入在 app.js **之后**，模块加载时读不到，
// 必须在真正发请求时再取（并等 DOMContentLoaded 之后再启动）。
const API = "relic-studio";
const getBridge = () => window.AstrBotPluginPage || window.AstrBotPluginView;
const BLOCK_LABELS = { header: "页头", chips: "信息条", grid: "卡片网格", standing: "看板娘", footer: "页脚" };

const state = {
  items: [],
  selected: new Set(),
  layout: null,
  theme: "dark",
  renderToken: 0,
  timer: null,
};

const $ = (id) => document.getElementById(id);
const els = {
  status: $("status"),
  q: $("q"),
  search: $("search"),
  resultMeta: $("result-meta"),
  results: $("results"),
  previewMeta: $("preview-meta"),
  shot: $("shot"),
  placeholder: $("placeholder"),
  theme: $("theme"),
  columns: $("columns"),
  maxItems: $("maxItems"),
  rewardsPerCard: $("rewardsPerCard"),
  rewardLines: $("rewardLines"),
  showDucats: $("showDucats"),
  standingEnabled: $("standingEnabled"),
  standingSeasonal: $("standingSeasonal"),
  standingSize: $("standingSize"),
  footerEnabled: $("footerEnabled"),
  footerText: $("footerText"),
  globalSignature: $("globalSignature"),
  globalSignatureEnabled: $("globalSignatureEnabled"),
  globalStanding: $("globalStanding"),
  globalStandingSeasonal: $("globalStandingSeasonal"),
  saveBranding: $("saveBranding"),
  blocks: $("blocks"),
};

/* ------------------------------------------------------------------ 请求层 */

async function apiGet(endpoint, params) {
  const bridge = getBridge();
  if (bridge?.apiGet) return bridge.apiGet(`${API}/${endpoint}`, params);
  const url = new URL(`/api/plugin/astrbot_plugin_nyxbot/${API}/${endpoint}`, location.origin);
  Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error(res.status === 401 ? "未授权：请从面板内打开本页（直链没有 bridge 会话）" : `HTTP ${res.status}`);
  return res.json();
}

async function apiPost(endpoint, body) {
  const bridge = getBridge();
  if (bridge?.apiPost) return bridge.apiPost(`${API}/${endpoint}`, body);
  const res = await fetch(`/api/plugin/astrbot_plugin_nyxbot/${API}/${endpoint}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(res.status === 401 ? "未授权：请从面板内打开本页（直链没有 bridge 会话）" : `HTTP ${res.status}`);
  return res.json();
}

function setStatus(text) {
  els.status.textContent = text;
}

/* ------------------------------------------------------------------ 查询 */

function renderResults() {
  els.results.innerHTML = "";
  for (const relic of state.items) {
    const li = document.createElement("li");
    li.className = state.selected.has(relic.uniqueName) ? "active" : "";
    li.innerHTML = `<span class="name">${escapeHtml(relic.name)}</span><span class="badge">${relic.rareCount || 0} 稀有</span>`;
    li.addEventListener("click", () => toggle(relic.uniqueName));
    els.results.appendChild(li);
  }
  const total = state.items.length;
  els.resultMeta.textContent = total ? `命中 ${total} 个遗物 · 已选 ${state.selected.size}` : "没有匹配的遗物";
}

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

async function doSearch() {
  const q = els.q.value.trim();
  setStatus(`查询「${q || "全部"}」…`);
  try {
    const data = await apiGet("search", { q, limit: 40 });
    state.items = data.items || [];
    // 保留仍然存在的选中项，其余丢弃
    const alive = new Set(state.items.map((item) => item.uniqueName));
    state.selected = new Set([...state.selected].filter((name) => alive.has(name)));
    renderResults();
    if (!state.selected.size && state.items.length) {
      state.items.slice(0, 6).forEach((item) => state.selected.add(item.uniqueName));
      renderResults();
    }
    setStatus(`查询完成 · ${state.items.length} 个遗物`);
    scheduleRender();
  } catch (err) {
    setStatus(`查询失败：${err.message}`);
  }
}

function toggle(uniqueName) {
  if (state.selected.has(uniqueName)) state.selected.delete(uniqueName);
  else state.selected.add(uniqueName);
  renderResults();
  scheduleRender();
}

/* ------------------------------------------------------------------ 版式 */

function blockOf(type) {
  return (state.layout?.blocks || []).find((block) => block.type === type);
}

function syncControlsFromLayout() {
  const grid = blockOf("grid")?.props || {};
  els.columns.value = grid.columns ?? 3;
  els.maxItems.value = grid.maxItems ?? 20;
  els.rewardsPerCard.value = grid.rewardsPerCard ?? 6;
  els.rewardLines.value = String(grid.rewardLines ?? 1);
  els.showDucats.checked = grid.showDucats !== false;

  const standing = blockOf("standing")?.props || {};
  els.standingEnabled.checked = standing.enabled !== false;
  els.standingSeasonal.checked = standing.seasonal !== false;
  els.standingSize.value = standing.size || "md";

  const footer = blockOf("footer")?.props || {};
  els.footerEnabled.checked = footer.enabled !== false;
  els.footerText.value = footer.text ?? "";

  updateValueLabels();
  renderBlockToggles();
}

function updateValueLabels() {
  $("columns-val").textContent = els.columns.value;
  $("maxItems-val").textContent = els.maxItems.value;
  $("rewardsPerCard-val").textContent = els.rewardsPerCard.value;
}

function renderBlockToggles() {
  els.blocks.innerHTML = "";
  const blocks = state.layout?.blocks || [];
  const enabled = new Set(blocks.filter((block) => block.props?.enabled !== false).map((block) => block.type));
  for (const [type, label] of Object.entries(BLOCK_LABELS)) {
    const wrapper = document.createElement("label");
    wrapper.innerHTML = `<input type="checkbox" ${enabled.has(type) ? "checked" : ""} /> ${label}`;
    wrapper.querySelector("input").addEventListener("change", (event) => {
      toggleBlock(type, event.target.checked);
    });
    els.blocks.appendChild(wrapper);
  }
}

/** 按固定顺序重建 blocks；参数从控件读，块开关写进 props.enabled。 */
function rebuildLayout() {
  const defaults = state.defaults || { blocks: [] };
  const previous = new Map((state.layout?.blocks || []).map((block) => [block.type, block]));
  const order = defaults.blocks.map((block) => block.type);

  const blocks = [];
  for (const type of order) {
    const existing = previous.get(type);
    if (!existing) continue;
    const next = { type, props: { ...existing.props } };
    if (type === "grid") {
      next.props.columns = Number(els.columns.value);
      next.props.maxItems = Number(els.maxItems.value);
      next.props.rewardsPerCard = Number(els.rewardsPerCard.value);
      next.props.rewardLines = Number(els.rewardLines.value);
      next.props.showDucats = els.showDucats.checked;
    } else if (type === "standing") {
      next.props.enabled = els.standingEnabled.checked;
      next.props.seasonal = els.standingSeasonal.checked;
      next.props.size = els.standingSize.value;
    } else if (type === "footer") {
      next.props.enabled = els.footerEnabled.checked;
      next.props.text = els.footerText.value.trim();
    }
    blocks.push(next);
  }
  state.layout = { ...state.layout, version: 2, blocks };
}

/** 开关某个块：保留块本身（顺序不变），只切 props.enabled。 */
function setBlockEnabled(type, on) {
  if (!state.layout) return;
  state.layout = {
    ...state.layout,
    blocks: (state.layout.blocks || []).map((block) =>
      block.type === type ? { ...block, props: { ...block.props, enabled: on } } : block
    ),
  };
  if (type === "standing") els.standingEnabled.checked = on;
  if (type === "footer") els.footerEnabled.checked = on;
  renderBlockToggles();
}

function toggleBlock(type, on) {
  setBlockEnabled(type, on);
  scheduleRender();
}

/* ------------------------------------------------------------------ 渲染 */

function scheduleRender() {
  clearTimeout(state.timer);
  state.timer = setTimeout(doRender, 350); // 防抖：拖滑块时不要每个像素都打后端
}

async function doRender() {
  if (!state.selected.size) {
    els.shot.hidden = true;
    els.placeholder.hidden = false;
    els.previewMeta.textContent = "尚未渲染（未选择遗物）";
    return;
  }
  rebuildLayout();
  const token = ++state.renderToken;
  els.previewMeta.textContent = "渲染中…";

  try {
    const data = await apiPost("render", {
      uniqueNames: [...state.selected],
      layout: state.layout,
      theme: state.theme,
    });
    if (token !== state.renderToken) return; // 有更新的请求，丢弃旧结果
    els.shot.src = data.image;
    els.shot.hidden = false;
    els.placeholder.hidden = true;
    els.previewMeta.textContent = `${data.width}×${data.height} · ${data.count} 个遗物 · ${data.ms} ms · ${(data.bytes / 1024).toFixed(0)} KB`;
    setStatus("渲染完成");
  } catch (err) {
    els.previewMeta.textContent = `渲染失败：${err.message}`;
    setStatus(`渲染失败：${err.message}`);
  }
}

/* ------------------------------------------------------------------ 动作 */

async function loadLayout() {
  const data = await apiGet("layout");
  state.layout = data.layout;
  state.defaults = data.defaults;
  syncControlsFromLayout();
}

async function loadBranding() {
  try {
    const data = await apiGet("branding");
    const branding = data.branding || {};
    const signature = branding.signature || {};
    const standing = branding.standing || {};
    els.globalSignature.value = signature.text || "";
    els.globalSignatureEnabled.checked = signature.enabled !== false;
    els.globalStanding.checked = standing.enabled !== false;
    els.globalStandingSeasonal.checked = standing.seasonal !== false;
    els.footerText.placeholder = signature.text || "Posted by: KingPrimes";
  } catch (err) {
    // 全局设置读不到不影响版式编辑，留空即可
    els.footerText.placeholder = "Posted by: KingPrimes";
  }
}

async function saveBranding() {
  try {
    const data = await apiPost("branding", {
      branding: {
        signature: {
          text: els.globalSignature.value.trim(),
          enabled: els.globalSignatureEnabled.checked,
        },
        standing: {
          enabled: els.globalStanding.checked,
          seasonal: els.globalStandingSeasonal.checked,
        },
      },
    });
    setStatus(`全局设置已保存 → ${data.path}`);
    els.footerText.placeholder = data.branding?.signature?.text || "Posted by: KingPrimes";
    scheduleRender();
  } catch (err) {
    setStatus(`全局设置保存失败：${err.message}`);
  }
}

async function saveLayout() {
  rebuildLayout();
  try {
    const data = await apiPost("layout", { layout: state.layout });
    state.layout = data.layout;
    syncControlsFromLayout();
    setStatus(`版式已保存 → ${data.saved}`);
  } catch (err) {
    setStatus(`保存失败：${err.message}`);
  }
}

async function resetLayout() {
  state.layout = JSON.parse(JSON.stringify(state.defaults));
  syncControlsFromLayout();
  setStatus("已恢复默认版式");
  scheduleRender();
}

function exportLayout() {
  const blob = new Blob([JSON.stringify(state.layout, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "relic_layout.json";
  link.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------------------------------------------ 绑定 */

function bind() {
  els.search.addEventListener("click", doSearch);
  els.q.addEventListener("keydown", (event) => {
    if (event.key === "Enter") doSearch();
  });

  $("select-all").addEventListener("click", () => {
    state.items.forEach((item) => state.selected.add(item.uniqueName));
    renderResults();
    scheduleRender();
  });
  $("select-none").addEventListener("click", () => {
    state.selected.clear();
    renderResults();
    scheduleRender();
  });

  els.theme.addEventListener("change", () => {
    state.theme = els.theme.value;
    scheduleRender();
  });

  for (const id of ["columns", "maxItems", "rewardsPerCard"]) {
    els[id].addEventListener("input", () => {
      updateValueLabels();
      scheduleRender();
    });
  }
  els.showDucats.addEventListener("change", scheduleRender);
  els.rewardLines.addEventListener("change", scheduleRender);

  els.standingEnabled.addEventListener("change", () => {
    setBlockEnabled("standing", els.standingEnabled.checked);
    scheduleRender();
  });
  els.standingSeasonal.addEventListener("change", scheduleRender);
  els.standingSize.addEventListener("change", scheduleRender);

  els.footerEnabled.addEventListener("change", () => {
    setBlockEnabled("footer", els.footerEnabled.checked);
    scheduleRender();
  });
  els.footerText.addEventListener("input", scheduleRender);
  els.saveBranding.addEventListener("click", saveBranding);

  $("render").addEventListener("click", doRender);
  $("save").addEventListener("click", saveLayout);
  $("reset").addEventListener("click", resetLayout);
  $("export").addEventListener("click", exportLayout);
}

async function boot() {
  bind();
  try {
    await loadLayout();
    setStatus("版式已加载");
  } catch (err) {
    setStatus(`版式加载失败：${err.message}`);
  }
  await loadBranding();
  await doSearch();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
