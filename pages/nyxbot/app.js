/* ============================================================================
   NyxBot 控制台 —— 首页 + 内嵌工作区
   子应用（数据管理台 / 渲染工作台）以 srcdoc 内联，各自独立文档；
   它们发出的 bridge 请求由本页中转给 dashboard（真 bridge 在本页里）。
   ============================================================================ */

const APP_META = {
  admin: { title: "数据管理台", status: "数据管理台 · 已就绪" },
  studio: { title: "渲染工作台", status: "渲染工作台 · 已就绪" },
};

const $ = (id) => document.getElementById(id);
const els = {
  home: $("home"),
  workspace: $("workspace"),
  frames: $("frames"),
  back: $("back"),
  title: $("ws-title"),
  status: $("status"),
};

const frames = new Map(); // key -> HTMLIFrameElement（懒创建，保留各自状态）

/** bridge-sdk 注入在脚本之后，必须惰性取。 */
const getBridge = () => window.AstrBotPluginPage || window.AstrBotPluginView;

function setStatus(text) {
  els.status.textContent = text;
}

/* ------------------------------------------------------------------ 中转 */

async function forward(action, endpoint, payload) {
  const bridge = getBridge();
  if (!bridge) throw new Error("页面 bridge 未就绪，请从 AstrBot 面板内打开本页");
  if (action === "api:post") return bridge.apiPost(endpoint, payload.body || {});
  return bridge.apiGet(endpoint, payload.params || {});
}

window.addEventListener("message", async (event) => {
  const data = event.data;
  if (!data || data.__nyx !== "req" || !event.source) return;
  try {
    const result = await forward(data.action, data.endpoint, data);
    event.source.postMessage({ __nyx: "res", id: data.id, ok: true, data: result }, "*");
  } catch (error) {
    event.source.postMessage(
      { __nyx: "res", id: data.id, ok: false, error: String((error && error.message) || error) },
      "*"
    );
  }
});

/* ------------------------------------------------------------------ 视图 */

function openApp(key) {
  const meta = APP_META[key];
  if (!meta) return;

  if (!frames.has(key)) {
    const apps = window.NYX_APPS || {};
    const doc = apps[key];
    if (!doc) {
      setStatus(`缺少内嵌页面：${key}（请先运行 tools/build_home_page.py）`);
      return;
    }
    const frame = document.createElement("iframe");
    frame.className = "frame";
    frame.title = meta.title;
    frame.setAttribute("sandbox", "allow-scripts allow-forms allow-downloads");
    frame.srcdoc = doc;
    els.frames.appendChild(frame);
    frames.set(key, frame);
  }

  for (const [name, frame] of frames) frame.classList.toggle("active", name === key);
  els.home.hidden = true;
  els.workspace.hidden = false;
  els.title.textContent = meta.title;
  setStatus(meta.status);
}

function goHome() {
  els.workspace.hidden = true;
  els.home.hidden = false;
  setStatus("就绪");
}

/* ------------------------------------------------------------------ 启动 */

function bind() {
  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("click", () => openApp(card.dataset.app));
  });
  els.back.addEventListener("click", goHome);
}

function boot() {
  bind();
  const apps = Object.keys(window.NYX_APPS || {});
  if (!apps.length) {
    setStatus("未找到内嵌应用：请运行 python tools/build_home_page.py");
  } else {
    setStatus(`就绪 · ${apps.length} 个工作区`);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
