/* ============================================================================
   NyxBot 数据管理 — 视图逻辑
   单一视图：数据管理（模型 CRUD / 同步）+ 插件设置（配置项在线修改）。
   数据来源：插件已注册的 Web API（models / data/<model> / config / i18n），
   全部通过 AstrBot Plugin View bridge 调用。

   语言：文案由后端 /i18n 提供（与 .astrbot-plugin/i18n/*.json 同源），按
   bridge 上下文里的 locale 选择；该语言没有文案文件时回退英文。
   ============================================================================ */

const PAGE_SIZE = 20;
const FALLBACK_LOCALE = "en";
const REQUEST_TIMEOUT = 15000;

/* ---------------------------------------------------------------- 兜底字典 */
// 仅在 /i18n 接口不可用时使用：模型与字段的中文名，保证表格不至于显示英文键名。
const MODEL_LABELS = {
  alias: "别名", nodes: "节点", arbitration_tier: "仲裁分级",
  state_translation: "状态翻译", night_wave: "午夜电波",
  relics: "遗物", relic_rewards: "遗物奖励", sentinels: "守护",
  upgrades: "振幅晶体", warframes: "战甲", warframe_ability: "战甲技能",
  weapons: "武器", reward_pool: "奖励池", reward: "具体奖励",
  riven_tion: "紫卡词条", riven_tion_alias: "紫卡词条别名",
  riven_analyse_trend: "紫卡分析趋势", riven_items: "紫卡物品",
  orders_items: "市场物品", ephemeras: "幻纹",
  lich_sister_weapons: "玄骸/姐妹武器", notification_history: "通知历史",
  mission_subscribe: "任务订阅", mission_subscribe_user: "订阅用户",
  mission_subscribe_user_check_type: "订阅检查类型",
};

const CATEGORY_LABELS = {
  basic: "基础数据", translation: "翻译数据", game_content: "游戏内容",
  riven: "Riven 数据", market: "Market 数据", notification: "通知与订阅", other: "其他",
};

const MODEL_CATEGORIES = {
  alias: "basic", nodes: "basic", arbitration_tier: "basic",
  state_translation: "translation",
  night_wave: "game_content", relics: "game_content", relic_rewards: "game_content",
  sentinels: "game_content", upgrades: "game_content", warframes: "game_content",
  warframe_ability: "game_content", weapons: "game_content",
  reward_pool: "game_content", reward: "game_content",
  riven_tion: "riven", riven_tion_alias: "riven",
  riven_analyse_trend: "riven", riven_items: "riven",
  orders_items: "market", ephemeras: "market", lich_sister_weapons: "market",
  notification_history: "notification", mission_subscribe: "notification",
  mission_subscribe_user: "notification",
  mission_subscribe_user_check_type: "notification",
};

/* 侧栏分组顺序固定：不随模型注册顺序变化，保证每次打开的阅读路径一致 */
const CATEGORY_ORDER = ["basic", "translation", "game_content", "riven", "market", "notification", "other"];

const FIELD_LABELS = {
  id: "ID", ids: "ID", cn: "中文名", en: "英文名", name: "名称",
  uniqueName: "唯一名称", unique_name: "唯一名称", description: "描述",
  type: "类型", rarity: "稀有度", tier: "等级", tag: "标签",
  url_name: "URL 名称", urlName: "URL 名称", slug: "标识符",
  effect: "词条名称", group: "分组", title: "标题",
  user_id: "用户 ID", user_name: "用户名", mission_type: "任务类型",
  rewardName: "奖励名称", ducats: "杜卡德", enName: "英文名",
  is_custom: "自定义", vaulted: "已入库",
};

/* ---------------------------------------------------------------- 状态 */
const state = {
  view: "data",
  // 数据管理
  models: [],
  model: null,
  page: 1,
  total: 0,
  rows: [],
  query: "",
  loading: false,
  busy: false,
  editing: null,
  pendingDelete: null,
  pendingConfirm: null,
  showPager: false,
  // 侧栏分组折叠：默认全部收起；搜索时全展开，searchClosed 记被手动收起的
  openGroups: new Set(),
  searchClosed: new Set(),
  // 插件设置
  configItems: [],
  configValues: {},
  configOriginal: {},
  configErrors: {},
  configLoaded: false,
  configLoading: false,
  configSaving: false,
  reloadKeys: [],
  // 多语言
  locale: FALLBACK_LOCALE,
  locales: [],
  i18n: {},
  i18nFallback: FALLBACK_LOCALE,
  rawLocale: "",
};

let toastTimer = null;
let searchTimer = null;
let requestSeq = 0;
let lastFocus = null;

/* ---------------------------------------------------------------- i18n */
function format(template, vars) {
  if (!vars) return template;
  return String(template).replace(/\{(\w+)\}/g, (match, key) =>
    (Object.prototype.hasOwnProperty.call(vars, key) ? String(vars[key]) : match)
  );
}

/** 按 a.b.c 取值；取不到返回 null。 */
function dig(source, path) {
  let node = source;
  for (const part of path.split(".")) {
    if (node == null || typeof node !== "object") return null;
    node = node[part];
  }
  return node;
}

function lookup(key) {
  const order = [state.locale, state.i18nFallback, "en"].filter(Boolean);
  for (const locale of order) {
    const dict = state.i18n[locale];
    if (!dict) continue;
    const value = dig(dict, key);
    if (typeof value === "string") return value;
  }
  return null;
}

/** 取文案；缺失时返回 key（便于发现漏翻）。 */
function t(key, vars) {
  const value = lookup(key);
  return value == null ? key : format(value, vars);
}

/** 取文案，缺失时用调用处的兜底（通常来自后端 schema）。 */
function tOr(key, fallback, vars) {
  const value = lookup(key);
  return value == null ? (fallback == null ? key : String(fallback)) : format(value, vars);
}

/** 把 AstrBot 的语言标识映射到我们实际有的文案；没有就回退英文。 */
function pickLocale(raw) {
  const supported = state.locales.length ? state.locales : [state.i18nFallback || FALLBACK_LOCALE];
  const normalized = String(raw || "").trim().replace(/_/g, "-").toLowerCase();
  if (!normalized) return state.i18nFallback || FALLBACK_LOCALE;

  const exact = supported.find((locale) => locale.toLowerCase() === normalized);
  if (exact) return exact;

  const language = normalized.split("-")[0];
  const sameLanguage = supported.find(
    (locale) => locale.toLowerCase().split("-")[0] === language
  );
  return sameLanguage || state.i18nFallback || FALLBACK_LOCALE;
}

function applyI18nDom(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  root.querySelectorAll("[data-i18n-aria]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAria));
  });
  root.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
}

/* 非中文界面下缺译时回退字段原名，避免中文漏进英文/俄文界面 */
const fallbackLabel = (name, fallback) =>
  state.locale === "zh-CN" ? (fallback || name) : name;

const modelLabel = (name) => tOr(`models.${name}`, fallbackLabel(name, MODEL_LABELS[name]));
const categoryLabel = (key) => tOr(`categories.${key}`, fallbackLabel(key, CATEGORY_LABELS[key]));
const fieldLabel = (name) => tOr(`fields.${name}`, fallbackLabel(name, FIELD_LABELS[name]));

/* ---------------------------------------------------------------- DOM */
const $ = (id) => document.getElementById(id);
const el = {
  sidebar: $("sidebar"),
  scrim: $("scrim"),
  sidebarToggle: $("sidebar-toggle"),
  drawerClose: $("drawer-close"),
  sidebarSubtitle: $("sidebar-subtitle"),
  sidebarSystemLabel: $("sidebar-system-label"),
  settingsEntry: $("settings-entry"),
  modelFilter: $("model-filter"),
  modelList: $("model-list"),
  modelSummary: $("model-summary"),
  crumbRoot: $("crumb-root"),
  crumbModel: $("crumb-model"),
  modelTitle: $("current-model-title"),
  recordCount: $("record-count"),
  pageSummary: $("page-summary"),
  dataActions: $("data-actions"),
  settingsActions: $("settings-actions"),
  searchbar: $("searchbar"),
  refresh: $("refresh-btn"),
  sync: $("sync-btn"),
  create: $("create-btn"),
  configReset: $("config-reset"),
  configSave: $("config-save"),
  dataSearch: $("data-search"),
  searchClear: $("search-clear"),
  searchHint: $("search-hint"),
  notice: $("notice"),
  table: $("table-container"),
  settingsArea: $("settings-area"),
  settingsForm: $("settings-form"),
  pagination: $("pagination"),
  pageTotal: $("page-total"),
  pageInfo: $("page-info"),
  prev: $("prev-page"),
  next: $("next-page"),
  modalOverlay: $("modal-overlay"),
  modalTitle: $("modal-title"),
  formFields: $("form-fields"),
  formHint: $("form-hint"),
  modalSubmit: $("modal-submit"),
  confirmOverlay: $("confirm-overlay"),
  confirmTitle: $("confirm-title"),
  confirmMessage: $("confirm-message"),
  confirmDetail: $("confirm-detail"),
  confirmHint: $("confirm-hint"),
  confirmDelete: $("confirm-delete"),
  toast: $("toast"),
};

/* ---------------------------------------------------------------- 工具 */
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function icon(name) {
  return `<svg class="ico" aria-hidden="true"><use href="#i-${name}"/></svg>`;
}

function withTimeout(promise, ms = REQUEST_TIMEOUT) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(t("errors.timeout"))), ms)
    ),
  ]);
}

function showToast(message, type = "info") {
  const glyph = type === "success" ? "save" : type === "error" ? "alert" : "info";
  const tone = type === "error" ? "danger" : type === "warn" ? "warn" : type === "success" ? "success" : "info";
  el.toast.innerHTML = `${icon(glyph)}<span>${escapeHtml(message)}</span>`;
  el.toast.dataset.tone = tone;
  el.toast.setAttribute("role", tone === "danger" ? "alert" : "status");
  el.toast.hidden = false;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.toast.hidden = true; }, 3600);
}

function showNotice(message, kind = "error") {
  el.notice.dataset.tone = kind === "error" ? "danger" : kind === "warn" ? "warn" : "info";
  el.notice.innerHTML = `${icon(kind === "error" ? "alert" : kind === "warn" ? "alert" : "info")}<span>${escapeHtml(message)}</span>`;
  el.notice.hidden = false;
}

function clearNotice() {
  el.notice.hidden = true;
  el.notice.innerHTML = "";
}

/* ---------------------------------------------------------------- Bridge */
function getBridge() {
  return window.AstrBotPluginPage || window.AstrBotPluginView || null;
}

/** SDK 注入时机不确定（独立视图晚于脚本、内嵌视图是 shim），惰性等待。 */
function waitBridge(timeout = 4000) {
  return new Promise((resolve) => {
    const hit = getBridge();
    if (hit) return resolve(hit);
    const started = Date.now();
    const timer = setInterval(() => {
      const bridge = getBridge();
      if (bridge) {
        clearInterval(timer);
        resolve(bridge);
      } else if (Date.now() - started >= timeout) {
        clearInterval(timer);
        resolve(null);
      }
    }, 80);
  });
}

async function apiGet(endpoint, params = {}) {
  const bridge = await waitBridge();
  if (!bridge || typeof bridge.apiGet !== "function") {
    throw new Error(t("errors.no_bridge"));
  }
  return withTimeout(bridge.apiGet(endpoint, params));
}

async function apiPost(endpoint, body = {}) {
  const bridge = await waitBridge();
  if (!bridge || typeof bridge.apiPost !== "function") {
    throw new Error(t("errors.no_bridge"));
  }
  return withTimeout(bridge.apiPost(endpoint, body));
}

/** 后端返回 {success:bool} 或 {status:"ok",data:{...}}，统一成 {ok,error,message}。 */
function unwrapResult(raw) {
  if (!raw) return { ok: false, error: "empty response", message: "" };
  if (typeof raw.success === "boolean") {
    return { ok: raw.success, error: raw.error || "", message: raw.message || "" };
  }
  const inner = raw.data && typeof raw.data === "object" ? raw.data : raw;
  if (typeof inner.success === "boolean") {
    return { ok: inner.success, error: inner.error || "", message: inner.message || "" };
  }
  if (raw.status === "error") return { ok: false, error: raw.message || "error", message: "" };
  return { ok: true, error: "", message: inner.message || "" };
}

/* ---------------------------------------------------------------- 视图切换 */
function updateChrome() {
  const isSettings = state.view === "settings";

  el.searchbar.hidden = isSettings;
  el.table.hidden = isSettings;
  el.settingsArea.hidden = !isSettings;
  el.pagination.hidden = isSettings || !state.showPager;
  el.dataActions.hidden = isSettings;
  el.settingsActions.hidden = !isSettings;
  el.recordCount.hidden = isSettings;
  el.settingsEntry.setAttribute("aria-current", isSettings ? "true" : "false");
  el.modelList.querySelectorAll("[data-model]").forEach((node) => {
    const active = !isSettings && node.dataset.model === state.model;
    node.setAttribute("aria-current", active ? "true" : "false");
  });
  // 分组收起时仍能定位当前模型属于哪个模块
  const activeGroup = !isSettings && state.model ? groupOf(state.model) : "";
  el.modelList.querySelectorAll("[data-group]").forEach((node) => {
    node.dataset.active = String(node.dataset.group === activeGroup);
  });

  if (isSettings) {
    el.crumbRoot.textContent = t("settings.crumb");
    el.crumbModel.textContent = t("settings.title");
    el.modelTitle.textContent = t("settings.title");
    el.pageSummary.textContent = configDirtyKeys().length
      ? t("settings.dirty", { n: configDirtyKeys().length })
      : t("settings.lead", { n: state.configItems.length });
  } else {
    el.crumbRoot.textContent = t("crumb.root");
    el.crumbModel.textContent = state.model ? modelLabel(state.model) : "—";
    el.modelTitle.textContent = state.model ? modelLabel(state.model) : t("toolbar.select_model");
  }
}

function setView(view) {
  if (state.view === view) return;
  state.view = view;
  updateChrome();
  if (view !== "settings") return;
  // 每次进入都按 state 重绘：丢弃修改后再次进入时不会残留旧输入
  if (state.configLoaded) renderSettings();
  else loadConfig();
}

/** 有未保存的配置时，先确认再离开设置页。 */
function leaveSettingsGuard(action) {
  if (state.view !== "settings") {
    action();
    return;
  }
  const dirty = configDirtyKeys();
  if (!dirty.length) {
    action();
    return;
  }
  openConfirm({
    title: t("settings.unsaved_title"),
    message: t("settings.unsaved_message", { n: dirty.length }),
    confirmText: t("settings.unsaved_confirm"),
    tone: "danger",
    onConfirm: () => {
      state.configValues = { ...state.configOriginal };
      state.configErrors = {};
      closeModal("confirm");
      action();
    },
  });
}

/* ---------------------------------------------------------------- 对话框 */
function focusables(scope) {
  return Array.from(
    scope.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((node) => node.offsetParent !== null);
}

function openModal(kind) {
  lastFocus = document.activeElement;
  const overlay = kind === "confirm" ? el.confirmOverlay : el.modalOverlay;
  overlay.hidden = false;
  const dialog = overlay.querySelector(".dialog");
  const inputs = focusables(dialog).filter(
    (node) => node.tagName === "INPUT" && !node.readOnly
  );
  const preferred = inputs[0] || null;
  const fallback = kind === "confirm"
    ? $("confirm-cancel")
    : (focusables(dialog)[0] || null);
  (preferred || fallback)?.focus();
}

function closeModal(kind) {
  const overlay = kind === "confirm" ? el.confirmOverlay : el.modalOverlay;
  if (overlay.hidden) return;
  overlay.hidden = true;
  if (kind === "confirm") {
    state.pendingConfirm = null;
  } else {
    state.editing = null;
  }
  if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  lastFocus = null;
}

function handleDialogKeys(event) {
  const overlay = !el.confirmOverlay.hidden
    ? el.confirmOverlay
    : (!el.modalOverlay.hidden ? el.modalOverlay : null);

  if (!overlay) {
    if (event.key === "Escape") closeSidebar();
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeModal(overlay === el.confirmOverlay ? "confirm" : "modal");
    return;
  }
  if (event.key !== "Tab") return;
  const list = focusables(overlay.querySelector(".dialog"));
  if (!list.length) return;
  const first = list[0];
  const last = list[list.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function openConfirm({ title, message, detail = "", hint = "", confirmText, tone = "danger", onConfirm }) {
  state.pendingConfirm = onConfirm;
  el.confirmTitle.textContent = title;
  el.confirmMessage.textContent = message;
  el.confirmDetail.innerHTML = detail;
  el.confirmDetail.hidden = !detail;
  el.confirmHint.textContent = hint;
  el.confirmDelete.textContent = confirmText;
  el.confirmDelete.dataset.variant = tone === "danger" ? "danger" : "primary";
  openModal("confirm");
}

/* ---------------------------------------------------------------- 数据：模型列表 */
async function loadModels(autoSelect = false) {
  el.modelList.innerHTML =
    `<div class="model-state"><span class="spinner"></span>${escapeHtml(t("sidebar.loading"))}</div>`;
  el.modelSummary.textContent = "—";
  try {
    const raw = await apiGet("models", {});
    const models = raw && Array.isArray(raw.models) ? raw.models : [];
    state.models = models;
    if (!models.length) {
      el.modelList.innerHTML = `<div class="model-state">${escapeHtml(t("state.no_models_title"))}</div>`;
      renderState({
        icon: "database",
        title: t("state.no_models_title"),
        desc: t("state.no_models_desc"),
        actions: [{ action: "retry-models", label: t("actions.reload"), primary: true }],
      });
      setToolbar();
      return;
    }
    el.modelSummary.textContent = t("summary.models", { n: models.length });
    renderModelList();
    clearNotice();
    if (autoSelect && !state.model) selectModel(models[0].name);
    else updateChrome();
  } catch (err) {
    el.modelList.innerHTML =
      `<div class="model-state">${escapeHtml(t("state.error_title"))}<br>${escapeHtml(err.message)}` +
      `<br><button class="btn" data-state-action="retry-models" type="button">${escapeHtml(t("actions.retry"))}</button></div>`;
    renderState({
      icon: "alert",
      tone: "danger",
      title: t("state.error_title"),
      desc: t("state.error_desc", { error: err.message }),
      actions: [{ action: "retry-models", label: t("actions.retry"), primary: true }],
    });
    setToolbar();
  }
}

function groupOf(name) {
  return MODEL_CATEGORIES[name] || "other";
}

function categoryRank(key) {
  const index = CATEGORY_ORDER.indexOf(key);
  return index < 0 ? CATEGORY_ORDER.length : index;
}

/** 分组是否展开：搜索时默认全开（仍可手动收起），否则只看用户展开过哪些。 */
function groupExpanded(key) {
  return el.modelFilter.value.trim()
    ? !state.searchClosed.has(key)
    : state.openGroups.has(key);
}

/**
 * 渲染侧栏模型列表：按功能模块分组，默认只露分组标题。
 * 分组标题是 disclosure 按钮（aria-expanded / aria-controls），
 * 收起状态下用 data-active 标出当前模型所在分组，避免丢失上下文。
 */
function renderModelList() {
  const filter = el.modelFilter.value.trim().toLowerCase();
  const filtering = Boolean(filter);
  const grouped = new Map();
  for (const model of state.models) {
    const key = groupOf(model.name);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(model);
  }

  let html = "";
  let matched = 0;
  for (const key of Array.from(grouped.keys()).sort((a, b) => categoryRank(a) - categoryRank(b))) {
    const models = filter
      ? grouped.get(key).filter((model) =>
          modelLabel(model.name).toLowerCase().includes(filter) ||
          model.name.toLowerCase().includes(filter))
      : grouped.get(key);
    if (!models.length) continue;
    matched += models.length;

    const expanded = groupExpanded(key);
    const active = state.view === "data" && models.some((model) => model.name === state.model);
    html += `<div class="model-group">` +
      `<button class="model-group-head" type="button" data-group="${escapeHtml(key)}"` +
        ` aria-expanded="${expanded}" aria-controls="model-group-${escapeHtml(key)}"` +
        (active ? ' data-active="true"' : "") + ">" +
        `<svg class="ico chevron" aria-hidden="true"><use href="#i-chevron-right"/></svg>` +
        `<span class="model-group-name">${escapeHtml(categoryLabel(key))}</span>` +
        `<span class="model-group-count">${models.length}</span>` +
      `</button>` +
      `<ul class="model-group-body" id="model-group-${escapeHtml(key)}" role="list"${expanded ? "" : " hidden"}>` +
      models.map((model) => {
        const isActive = model.name === state.model;
        return `<li><button class="model-item" type="button" data-model="${escapeHtml(model.name)}"` +
          (isActive ? ' aria-current="true"' : "") +
          `><span class="grow">${escapeHtml(modelLabel(model.name))}</span>` +
          (model.has_sync
            ? `<span class="sync-mark" title="${escapeHtml(t("toolbar.sync"))}" aria-label="${escapeHtml(t("toolbar.sync"))}">${icon("refresh")}</span>`
            : "") +
          "</button></li>";
      }).join("") +
      `</ul></div>`;
  }

  el.modelList.innerHTML = html ||
    `<div class="model-state">${escapeHtml(t("sidebar.no_match"))}</div>`;
  el.modelSummary.textContent = filtering
    ? t("summary.models_matched", { n: matched })
    : t("summary.models", { n: state.models.length });
}

/** 切换分组展开状态；键盘操作时把焦点还给刚才的分组标题（鼠标操作不抢焦点）。 */
function setGroupOpen(key, open, restoreFocus = true) {
  if (el.modelFilter.value.trim()) {
    if (open) state.searchClosed.delete(key);
    else state.searchClosed.add(key);
  } else if (open) {
    state.openGroups.add(key);
  } else {
    state.openGroups.delete(key);
  }
  renderModelList();
  if (!restoreFocus) return;
  const head = el.modelList.querySelector(`[data-group="${key}"]`);
  if (head) head.focus();
}

function selectModel(name) {
  if (!name || state.loading) return;
  state.model = name;
  state.page = 1;
  state.query = "";
  state.rows = [];
  el.dataSearch.value = "";
  el.searchClear.hidden = true;
  el.crumbModel.textContent = modelLabel(name);
  el.modelTitle.textContent = modelLabel(name);
  el.recordCount.textContent = "—";
  el.pageSummary.textContent = t("summary.loading");
  renderModelList();
  setToolbar();
  closeSidebar();
  loadData();
}

/* ---------------------------------------------------------------- 数据：加载 */
function setToolbar() {
  const meta = state.models.find((model) => model.name === state.model);
  const ready = Boolean(state.model) && !state.loading && !state.busy;
  el.refresh.disabled = !ready;
  el.create.disabled = !ready;
  el.sync.disabled = !ready || !meta || !meta.has_sync;
  el.dataSearch.disabled = !state.model;
  el.searchHint.textContent = state.model
    ? t("search.hint_active")
    : t("search.hint_idle");
}

async function loadData() {
  if (!state.model || state.loading) return;
  const token = ++requestSeq;
  state.loading = true;
  setToolbar();
  clearNotice();
  renderState({
    spinner: true,
    title: t("state.loading_title"),
    desc: t("state.loading_desc", { model: modelLabel(state.model), page: state.page }),
  });

  const params = { page: state.page, size: PAGE_SIZE };
  if (state.query) params.q = state.query;

  try {
    const raw = await apiGet(`data/${state.model}`, params);
    if (token !== requestSeq) return; // 旧响应直接丢弃
    const rows = raw && Array.isArray(raw.items) ? raw.items : [];
    state.rows = rows;
    state.total = Number(raw && raw.total) || 0;
    el.recordCount.textContent = t("summary.records", { n: state.total });
    el.pageSummary.textContent = state.query
      ? t("summary.search", { q: state.query, size: PAGE_SIZE })
      : (rows.length
        ? t("summary.page", { size: PAGE_SIZE, pages: totalPages() })
        : t("summary.empty"));

    if (!rows.length) {
      const syncable = Boolean(state.models.find((m) => m.name === state.model)?.has_sync);
      const actions = state.query
        ? [{ action: "clear-search", label: t("actions.clear_search") }]
        : [
            ...(syncable ? [{ action: "sync", label: t("actions.sync"), primary: true }] : []),
            { action: "create", label: t("actions.create"), primary: !syncable },
          ];
      renderState({
        icon: state.query ? "search" : "database",
        tone: state.query ? "accent" : "",
        title: state.query ? t("state.no_match_title") : t("state.empty_title"),
        desc: state.query
          ? t("state.no_match_desc", { q: state.query })
          : t("state.empty_desc", { model: modelLabel(state.model) }) +
            (syncable ? t("state.empty_sync_hint") : t("state.empty_manual_hint")),
        actions,
      });
    } else {
      renderTable(rows);
      renderPagination();
    }
  } catch (err) {
    if (token !== requestSeq) return;
    state.rows = [];
    state.total = 0;
    el.recordCount.textContent = "—";
    el.pageSummary.textContent = t("summary.failed");
    renderState({
      icon: "alert",
      tone: "danger",
      title: t("state.error_title"),
      desc: t("state.error_desc", { error: err.message }),
      actions: [{ action: "retry", label: t("actions.retry"), primary: true }],
    });
    showNotice(t("notice.load_failed", { error: err.message }), "error");
  } finally {
    if (token === requestSeq) {
      state.loading = false;
      setToolbar();
    }
  }
}

function totalPages() {
  return Math.max(1, Math.ceil(state.total / PAGE_SIZE));
}

function renderTable(rows) {
  const columns = Object.keys(rows[0]);
  let html = '<table>' +
    `<caption class="sr-only">${escapeHtml(modelLabel(state.model))}</caption><thead><tr>`;
  for (const column of columns) {
    html += `<th scope="col" title="${escapeHtml(column)}">${escapeHtml(fieldLabel(column))}</th>`;
  }
  // 填充列：吃掉剩余宽度，数据列按内容收紧、操作列贴右
  html += `<th scope="col" class="col-fill" aria-hidden="true"></th>`;
  html += `<th scope="col" class="col-actions">${escapeHtml(t("table.actions"))}</th></tr></thead><tbody>`;

  for (const row of rows) {
    const id = escapeHtml(String(row.id ?? ""));
    html += `<tr data-row-id="${id}">`;
    for (const column of columns) {
      const value = row[column];
      const empty = value === null || value === undefined || value === "";
      const classes = [
        column === "id" || column === "ids" ? "col-id" : "",
        empty ? "is-null" : "",
      ].filter(Boolean).join(" ");
      const attr = classes ? ` class="${classes}"` : "";
      html += empty
        ? `<td${attr}>—</td>`
        : `<td${attr} title="${escapeHtml(String(value))}">${escapeHtml(String(value))}</td>`;
    }
    html += '<td class="col-fill" aria-hidden="true"></td>';
    html += `<td class="col-actions">
      <button class="row-btn" type="button" data-action="edit" data-id="${id}">${escapeHtml(t("modal.edit_btn"))}</button>
      <button class="row-btn" data-tone="danger" type="button" data-action="delete" data-id="${id}">${escapeHtml(t("modal.delete_btn"))}</button>
    </td></tr>`;
  }
  html += "</tbody></table>";
  el.table.innerHTML = html;
}

function renderPagination() {
  const pages = totalPages();
  if (pages <= 1 && !state.query) {
    state.showPager = false;
    updateChrome();
    return;
  }
  state.showPager = true;
  el.pageTotal.textContent = `${t("summary.records", { n: state.total })} · ${state.page} / ${pages}`;
  el.prev.disabled = state.page <= 1;
  el.next.disabled = state.page >= pages;

  const range = 2;
  const start = Math.max(1, state.page - range);
  const end = Math.min(pages, state.page + range);
  let html = "";
  if (start > 1) {
    html += `<button class="page-btn" type="button" data-page="1">1</button>`;
    if (start > 2) html += '<span class="page-gap" aria-hidden="true">…</span>';
  }
  for (let page = start; page <= end; page++) {
    html += `<button class="page-btn" type="button" data-page="${page}"` +
      (page === state.page ? ' aria-current="page"' : "") + `>${page}</button>`;
  }
  if (end < pages) {
    if (end < pages - 1) html += '<span class="page-gap" aria-hidden="true">…</span>';
    html += `<button class="page-btn" type="button" data-page="${pages}">${pages}</button>`;
  }
  el.pageInfo.innerHTML = html;
  updateChrome();
}

/** 数据区状态：加载中 / 空 / 失败 / 未选择，均带明确文案与可执行动作。 */
function renderState({ icon: glyph, tone = "", title, desc, actions = [], spinner = false }) {
  const buttons = actions.map((action) =>
    `<button class="btn"${action.primary ? ' data-variant="primary"' : ""} type="button" data-state-action="${action.action}">${escapeHtml(action.label)}</button>`
  ).join("");
  el.table.innerHTML = `
    <div class="state">
      ${spinner
        ? '<span class="spinner"></span>'
        : `<span class="state-icon"${tone ? ` data-tone="${tone}"` : ""}>${icon(glyph || "database")}</span>`}
      <p class="state-title">${escapeHtml(title)}</p>
      ${desc ? `<p class="state-desc">${escapeHtml(desc)}</p>` : ""}
      ${buttons ? `<div class="state-actions">${buttons}</div>` : ""}
    </div>`;
  state.showPager = false;
  updateChrome();
}

function goToPage(page) {
  const pages = totalPages();
  if (state.loading || page < 1 || page > pages || page === state.page) return;
  state.page = page;
  loadData();
}

/* ---------------------------------------------------------------- 表单 */
function currentColumns() {
  return state.rows.length ? Object.keys(state.rows[0]) : [];
}

function openForm(recordId) {
  const record = recordId
    ? state.rows.find((row) => String(row.id) === String(recordId))
    : null;
  if (recordId && !record) {
    showToast(t("modal.record_not_in_cache"), "error");
    return;
  }
  state.editing = recordId;
  el.modalTitle.textContent = recordId ? t("modal.edit_record") : t("modal.new_record");
  el.formHint.textContent = recordId ? t("form.edit_hint") : t("form.create_hint");
  renderForm(record);
  openModal("modal");
}

function renderForm(record) {
  const fields = currentColumns();
  if (!fields.length) {
    el.formFields.innerHTML = `<p class="form-note">${escapeHtml(t("form.no_fields"))}</p>`;
    el.modalSubmit.disabled = true;
    return;
  }
  el.modalSubmit.disabled = false;
  let html = `<p class="form-note">${escapeHtml(t("form.fields_note", { model: modelLabel(state.model), n: fields.length }))}</p><div class="field-grid">`;
  for (const field of fields) {
    const isId = field === "id" || field === "ids";
    const value = record ? (record[field] ?? "") : "";
    const wide = String(value).length > 60 ? " wide" : "";
    const placeholder = isId ? t("placeholders.id") : tOr(`placeholders.${field}`, t("placeholders.default"));
    html += `<div class="field${wide}">
      <label class="field-label" for="f-${escapeHtml(field)}">${escapeHtml(fieldLabel(field))}${isId ? `<small>${escapeHtml(t("modal.id_readonly"))}</small>` : ""}</label>
      <input class="input" type="text" id="f-${escapeHtml(field)}" name="${escapeHtml(field)}"
        value="${escapeHtml(String(value))}" placeholder="${escapeHtml(placeholder)}"
        ${isId ? "readonly" : ""} />
    </div>`;
  }
  el.formFields.innerHTML = html + "</div>";
}

async function submitForm() {
  if (state.busy || !state.model || el.modalSubmit.disabled) return;
  const data = {};
  let newId = "";
  for (const input of el.formFields.querySelectorAll("input[name]")) {
    const value = input.value.trim();
    if (input.name === "id" || input.name === "ids") {
      if (!state.editing && value) newId = value;
    } else {
      data[input.name] = value;
    }
  }
  if (!state.editing && newId) data.id = newId;

  state.busy = true;
  setToolbar();
  const original = el.modalSubmit.textContent;
  el.modalSubmit.disabled = true;
  el.modalSubmit.innerHTML = `<span class="spinner"></span>${escapeHtml(t("modal.save"))}`;
  try {
    const endpoint = state.editing
      ? `data/${state.model}/update`
      : `data/${state.model}/create`;
    const body = state.editing ? { id: state.editing, ...data } : data;
    const result = unwrapResult(await apiPost(endpoint, body));
    if (!result.ok) throw new Error(result.error || t("toast.operation_failed"));
    showToast(state.editing ? t("toast.update_success") : t("toast.create_success"), "success");
    closeModal("modal");
    await loadData();
  } catch (err) {
    showToast(`${state.editing ? t("toast.update_failed") : t("toast.create_failed")}: ${err.message}`, "error");
  } finally {
    state.busy = false;
    el.modalSubmit.disabled = false;
    el.modalSubmit.textContent = original;
    setToolbar();
  }
}

/* ---------------------------------------------------------------- 删除 */
function openDeleteConfirm(recordId) {
  state.pendingDelete = recordId;
  const row = state.rows.find((item) => String(item.id) === String(recordId));
  const parts = [];
  if (row) {
    for (const key of ["id", "name", "cn", "en", "uniqueName", "url_name", "title"]) {
      if (row[key] === null || row[key] === undefined || String(row[key]) === "") continue;
      parts.push(`${fieldLabel(key)}：${String(row[key]).slice(0, 60)}`);
      if (parts.length >= 3) break;
    }
  }
  openConfirm({
    title: t("confirm.title"),
    message: t("confirm.message"),
    detail: parts.length
      ? parts.map((part) => `<div>${escapeHtml(part)}</div>`).join("")
      : `<div>ID：${escapeHtml(recordId)}</div>`,
    hint: "",
    confirmText: t("confirm.delete_btn"),
    tone: "danger",
    onConfirm: confirmDelete,
  });
}

async function confirmDelete() {
  if (state.busy || !state.pendingDelete || !state.model) return;
  state.busy = true;
  const button = el.confirmDelete;
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span>${escapeHtml(t("confirm.delete_btn"))}`;
  try {
    const result = unwrapResult(
      await apiPost(`data/${state.model}/delete`, { id: state.pendingDelete })
    );
    if (!result.ok) throw new Error(result.error || t("toast.delete_failed"));
    showToast(t("toast.delete_success"), "success");
    state.pendingDelete = null;
    closeModal("confirm");
    await loadData();
  } catch (err) {
    showToast(`${t("toast.delete_failed")}: ${err.message}`, "error");
  } finally {
    state.busy = false;
    button.disabled = false;
    button.textContent = t("confirm.delete_btn");
    setToolbar();
  }
}

/* ---------------------------------------------------------------- 同步 */
async function syncCurrentModel() {
  const meta = state.models.find((model) => model.name === state.model);
  if (state.busy || !state.model || !meta || !meta.has_sync) return;
  state.busy = true;
  setToolbar();
  const original = el.sync.textContent;
  el.sync.disabled = true;
  el.sync.innerHTML = `<span class="spinner"></span>${escapeHtml(t("toolbar.sync"))}`;
  showToast(t("toast.syncing", { model: modelLabel(state.model) }), "info");
  try {
    const result = unwrapResult(await apiPost(`data/${state.model}/sync`));
    if (!result.ok) throw new Error(result.error || t("toast.operation_failed"));
    showToast(result.message || t("toast.synced", { model: modelLabel(state.model) }), "success");
    await loadData();
  } catch (err) {
    showToast(t("toast.sync_failed", { error: err.message }), "error");
  } finally {
    state.busy = false;
    el.sync.textContent = original;
    setToolbar();
  }
}

/* ---------------------------------------------------------------- 侧栏抽屉 */
const mobileQuery = window.matchMedia("(max-width: 960px)");

/** 同步抽屉的可交互状态：窄屏收起时 inert，回到桌面宽度时复位。 */
function syncSidebarMode() {
  const mobile = mobileQuery.matches;
  if (!mobile) {
    el.sidebar.classList.remove("is-open");
    el.scrim.hidden = true;
    el.sidebarToggle.setAttribute("aria-expanded", "false");
  }
  el.sidebar.inert = mobile && !el.sidebar.classList.contains("is-open");
}

function openSidebar() {
  el.sidebar.classList.add("is-open");
  el.scrim.hidden = false;
  el.sidebarToggle.setAttribute("aria-expanded", "true");
  syncSidebarMode();
}
function closeSidebar() {
  el.sidebar.classList.remove("is-open");
  el.scrim.hidden = true;
  el.sidebarToggle.setAttribute("aria-expanded", "false");
  syncSidebarMode();
}

/* ================================================================ 插件设置 */
function configDirtyKeys() {
  return state.configItems
    .filter((item) => state.configValues[item.key] !== state.configOriginal[item.key])
    .map((item) => item.key);
}

function normalizeConfigValues(items, values) {
  const normalized = {};
  for (const item of items) {
    const raw = values ? values[item.key] : null;
    if (item.type === "bool") {
      normalized[item.key] = raw === true || raw === "true" || raw === 1 || raw === "1";
    } else {
      normalized[item.key] = raw === null || raw === undefined ? "" : String(raw);
    }
  }
  return normalized;
}

async function loadConfig() {
  if (state.configLoading) return;
  state.configLoading = true;
  el.settingsForm.innerHTML =
    `<div class="state"><span class="spinner"></span>` +
    `<p class="state-title">${escapeHtml(t("state.loading_title"))}</p></div>`;
  try {
    const raw = await apiGet("config");
    const items = raw && Array.isArray(raw.items) ? raw.items : [];
    if (!items.length) {
      el.settingsForm.innerHTML =
        `<div class="state"><span class="state-icon">${icon("gear")}</span>` +
        `<p class="state-title">${escapeHtml(t("state.no_models_title"))}</p>` +
        `<p class="state-desc">${escapeHtml(t("state.no_models_desc"))}</p></div>`;
      return;
    }
    state.configItems = items;
    state.configValues = normalizeConfigValues(items, raw.values);
    state.configOriginal = { ...state.configValues };    state.configErrors = {};
    state.configLoaded = true;
    renderSettings();
    updateChrome();
  } catch (err) {
    el.settingsForm.innerHTML =
      `<div class="state"><span class="state-icon" data-tone="danger">${icon("alert")}</span>` +
      `<p class="state-title">${escapeHtml(t("state.error_title"))}</p>` +
      `<p class="state-desc">${escapeHtml(t("state.error_desc", { error: err.message }))}</p>` +
      `<div class="state-actions"><button class="btn" data-variant="primary" type="button" data-state-action="retry-config">${escapeHtml(t("actions.retry"))}</button></div></div>`;
  } finally {
    state.configLoading = false;
  }
}

function groupConfigItems() {
  const order = [];
  const grouped = new Map();
  for (const item of state.configItems) {
    const key = item.group || "other";
    if (!grouped.has(key)) {
      grouped.set(key, []);
      order.push(key);
    }
    grouped.get(key).push(item);
  }
  return order.map((key) => ({ key, items: grouped.get(key) }));
}

function optionLabel(value) {
  return tOr(`settings.options.${value}`, value);
}

function renderConfigControl(item, value, id) {
  if (item.type === "bool") {
    return `<button class="switch" type="button" role="switch" id="${id}" data-key="${escapeHtml(item.key)}"
      aria-checked="${value ? "true" : "false"}" aria-label="${escapeHtml(tOr(`settings.items.${item.key}.label`, item.label))}"></button>`;
  }

  const options = Array.isArray(item.options) ? item.options : [];
  if (options.length) {
    const longOptions = options.some((option) => String(option).length > 16);
    if (longOptions) {
      const opts = options.map((option) =>
        `<option value="${escapeHtml(option)}"${String(value) === String(option) ? " selected" : ""}>${escapeHtml(optionLabel(option))}</option>`
      ).join("");
      return `<select class="input" id="${id}" data-key="${escapeHtml(item.key)}">${opts}</select>`;
    }
    const choices = options.map((option) => {
      const checked = String(value) === String(option) ? " checked" : "";
      return `<label class="choice"><input type="radio" name="${id}" value="${escapeHtml(option)}" data-key="${escapeHtml(item.key)}"${checked} /><span>${escapeHtml(optionLabel(option))}</span></label>`;
    }).join("");
    return `<div class="choice-group" role="radiogroup" aria-labelledby="${id}-label">${choices}</div>`;
  }

  if (item.type === "int" || item.type === "float") {
    const min = item.min === null || item.min === undefined ? "" : ` min="${item.min}"`;
    const max = item.max === null || item.max === undefined ? "" : ` max="${item.max}"`;
    const step = item.type === "float" ? ' step="0.1"' : ' step="1"';
    return `<input class="input" type="number" inputmode="numeric" id="${id}" data-key="${escapeHtml(item.key)}"
      value="${escapeHtml(String(value))}"${min}${max}${step} />`;
  }

  return `<input class="input" type="text" id="${id}" data-key="${escapeHtml(item.key)}"
    value="${escapeHtml(String(value))}" autocomplete="off" />`;
}

function renderConfigFoot(item) {
  const def = item.default;
  const isEnum = Array.isArray(item.options) && item.options.length > 0;
  // 枚举/开关的当前值已经显示在控件上，不再重复“默认：xxx”
  if (item.type === "bool" || isEnum) return "";
  if (def === null || def === undefined || def === "") return "";
  const changed = String(state.configValues[item.key]) !== String(def);
  return `<span class="settings-default">${escapeHtml(t("settings.default_value", { value: def }))}` +
    (changed
      ? `<button type="button" data-reset-key="${escapeHtml(item.key)}">${escapeHtml(t("settings.use_default"))}</button>`
      : "") +
    "</span>";
}

function renderConfigRow(item) {
  const value = state.configValues[item.key];
  const error = state.configErrors[item.key];
  const id = `cfg-${item.key}`;
  const label = tOr(`settings.items.${item.key}.label`, item.label);
  const hint = tOr(`settings.items.${item.key}.hint`, item.hint);

  return `<div class="settings-row${error ? " has-error" : ""}" data-key="${escapeHtml(item.key)}">
    <div class="settings-label">
      <label for="${id}" id="${id}-label">
        <span>${escapeHtml(label)}</span>
        ${item.requires_reload ? `<span class="badge" data-tone="warn">${escapeHtml(t("settings.reload_badge"))}</span>` : ""}
      </label>
      ${hint ? `<p class="settings-hint">${escapeHtml(hint)}</p>` : ""}
      ${error ? `<p class="settings-error" role="alert">${icon("alert")}${escapeHtml(errorText(error))}</p>` : ""}
    </div>
    <div class="settings-control">
      ${renderConfigControl(item, value, id)}
      <div class="settings-foot">${renderConfigFoot(item)}</div>
    </div>
  </div>`;
}

function errorText(code) {
  if (!code) return "";
  const [kind, arg] = String(code).split(":");
  if (kind === "min" || kind === "max") {
    return t(`settings.errors.${kind}`, { min: arg, max: arg });
  }
  const known = ["required", "invalid_number", "invalid_option", "too_long", "unknown_key", "invalid_bool"];
  return t(`settings.errors.${known.includes(kind) ? kind : "generic"}`);
}

function renderSettings() {
  const groups = groupConfigItems();
  el.settingsForm.innerHTML = groups.map((group) => `
    <section class="settings-group" aria-labelledby="group-${group.key}">
      <header class="settings-group-head">
        <h3 id="group-${group.key}">${escapeHtml(tOr(`settings.groups.${group.key}`, group.key))}</h3>
      </header>
      ${group.items.map(renderConfigRow).join("")}
    </section>`).join("");
  updateConfigButtons();
}

function updateConfigButtons() {
  const dirty = configDirtyKeys();
  el.configSave.disabled = state.configSaving || dirty.length === 0;
  el.configSave.querySelector("span").textContent = state.configSaving
    ? t("settings.saving")
    : t("settings.save");
  if (state.view === "settings") {
    el.pageSummary.textContent = state.configSaving
      ? t("settings.saving")
      : dirty.length
        ? t("settings.dirty", { n: dirty.length })
        : t("settings.lead", { n: state.configItems.length });
  }
}

function validateConfigItem(item, value) {
  if (item.type === "bool") return null;
  const text = String(value ?? "");

  if (item.type === "int" || item.type === "float") {
    if (!text.trim()) return "required";
    const number = Number(text);
    if (!Number.isFinite(number)) return "invalid_number";
    if (item.type === "int" && !Number.isInteger(number)) return "invalid_number";
    if (item.min !== null && item.min !== undefined && number < item.min) return `min:${item.min}`;
    if (item.max !== null && item.max !== undefined && number > item.max) return `max:${item.max}`;
    return null;
  }

  const options = Array.isArray(item.options) ? item.options : [];
  if (options.length && !options.includes(text)) return "invalid_option";
  if (text.length > 2048) return "too_long";
  return null;
}

function collectConfigPayload() {
  const payload = {};
  const errors = {};
  for (const item of state.configItems) {
    const value = state.configValues[item.key];
    const error = validateConfigItem(item, value);
    if (error) {
      errors[item.key] = error;
      continue;
    }
    if (item.type === "bool") payload[item.key] = Boolean(value);
    else if (item.type === "int" || item.type === "float") payload[item.key] = Number(value);
    else payload[item.key] = String(value);
  }
  return { payload, errors };
}

async function saveConfig() {
  if (state.configSaving) return;
  const { payload, errors } = collectConfigPayload();
  if (Object.keys(errors).length) {
    state.configErrors = errors;
    renderSettings();
    const first = el.settingsForm.querySelector(".settings-row.has-error");
    first?.querySelector("input, select, .switch")?.focus();
    showToast(t("settings.save_failed"), "error");
    return;
  }

  state.configSaving = true;
  state.configErrors = {};
  updateConfigButtons();
  try {
    const raw = await apiPost("config/update", { values: payload });
    if (raw && raw.errors && Object.keys(raw.errors).length) {
      state.configErrors = raw.errors;
      renderSettings();
      showToast(t("settings.save_failed"), "error");
      return;
    }
    const result = unwrapResult(raw);
    if (!result.ok) throw new Error(result.error || t("toast.operation_failed"));

    const values = raw && raw.values ? raw.values : payload;
    state.configValues = normalizeConfigValues(state.configItems, values);
    state.configOriginal = { ...state.configValues };
    state.reloadKeys = Array.isArray(raw.reload_keys) ? raw.reload_keys : [];
    renderSettings();

    if (state.reloadKeys.length) {
      const names = state.reloadKeys.map((key) => {
        const item = state.configItems.find((entry) => entry.key === key);
        return item ? tOr(`settings.items.${key}.label`, item.label) : key;
      });
      showNotice(t("settings.reload_notice", { keys: names.join(" · ") }), "warn");
    } else {
      clearNotice();
    }
    showToast(t("toast.config_saved"), "success");
  } catch (err) {
    if (err && err.errors) {
      state.configErrors = err.errors;
      renderSettings();
      showToast(t("settings.save_failed"), "error");
    } else {
      showToast(t("toast.config_failed", { error: err.message }), "error");
    }
  } finally {
    state.configSaving = false;
    updateConfigButtons();
  }
}

function resetConfig() {
  if (state.configSaving || !state.configItems.length) return;
  openConfirm({
    title: t("settings.reset_confirm_title"),
    message: t("settings.reset_confirm_message", { n: state.configItems.length }),
    confirmText: t("settings.reset_confirm_btn"),
    tone: "primary",
    onConfirm: () => {
      for (const item of state.configItems) {
        state.configValues[item.key] = item.type === "bool"
          ? Boolean(item.default)
          : (item.default === null || item.default === undefined ? "" : String(item.default));
      }
      state.configErrors = {};
      renderSettings();
      closeModal("confirm");
    },
  });
}

/* ---------------------------------------------------------------- 事件 */
function bindEvents() {
  /* 侧栏 */
  el.modelFilter.addEventListener("input", () => {
    // 关键词变化时重置「手动收起」，让命中分组重新全开
    state.searchClosed.clear();
    if (state.models.length) renderModelList();
  });

  el.modelList.addEventListener("click", (event) => {
    const head = event.target.closest("[data-group]");
    if (head) {
      // detail === 0：键盘触发的 click（Enter / Space），重渲染后需要归还焦点
      setGroupOpen(head.dataset.group, head.getAttribute("aria-expanded") !== "true", event.detail === 0);
      return;
    }
    const item = event.target.closest("[data-model]");
    if (item) {
      leaveSettingsGuard(() => {
        setView("data");
        selectModel(item.dataset.model);
      });
      return;
    }
    if (event.target.closest('[data-state-action="retry-models"]')) loadModels(true);
  });

  /* 分组标题键盘操作：← 收起、→ 展开（disclosure 模式） */
  el.modelList.addEventListener("keydown", (event) => {
    const head = event.target.closest("[data-group]");
    if (!head || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) return;
    event.preventDefault();
    setGroupOpen(head.dataset.group, event.key === "ArrowRight");
  });

  el.settingsEntry.addEventListener("click", () => {
    if (state.view === "settings") {
      closeSidebar();
      return;
    }
    setView("settings");
    closeSidebar();
  });

  /* 数据区 */
  el.table.addEventListener("click", (event) => {
    const stateButton = event.target.closest("[data-state-action]");
    if (stateButton) {
      const action = stateButton.dataset.stateAction;
      if (action === "retry-models") loadModels(true);
      else if (action === "sync") syncCurrentModel();
      else if (action === "retry") loadData();
      else if (action === "create") openForm(null);
      else if (action === "clear-search") {
        el.dataSearch.value = "";
        el.searchClear.hidden = true;
        state.query = "";
        state.page = 1;
        loadData();
      }
      return;
    }
    const rowButton = event.target.closest("[data-action]");
    if (!rowButton) return;
    if (rowButton.dataset.action === "edit") openForm(rowButton.dataset.id);
    else if (rowButton.dataset.action === "delete") openDeleteConfirm(rowButton.dataset.id);
  });

  el.refresh.addEventListener("click", () => { if (!state.loading) loadData(); });
  el.sync.addEventListener("click", syncCurrentModel);
  el.create.addEventListener("click", () => { if (!el.create.disabled) openForm(null); });

  el.dataSearch.addEventListener("input", () => {
    el.searchClear.hidden = !el.dataSearch.value;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const query = el.dataSearch.value.trim();
      if (query === state.query) return;
      state.query = query;
      state.page = 1;
      loadData();
    }, 350);
  });
  el.dataSearch.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    clearTimeout(searchTimer);
    const query = el.dataSearch.value.trim();
    if (query === state.query && !state.loading) return;
    state.query = query;
    state.page = 1;
    loadData();
  });
  el.searchClear.addEventListener("click", () => {
    el.dataSearch.value = "";
    el.searchClear.hidden = true;
    if (!state.query) return;
    state.query = "";
    state.page = 1;
    loadData();
  });

  el.prev.addEventListener("click", () => goToPage(state.page - 1));
  el.next.addEventListener("click", () => goToPage(state.page + 1));
  el.pageInfo.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (button) goToPage(Number(button.dataset.page));
  });

  /* 设置表单：输入 / 单选 / 开关 / 恢复默认 */
  el.settingsForm.addEventListener("input", (event) => {
    const field = event.target.closest("[data-key]");
    if (!field || field.classList.contains("switch")) return;
    const key = field.dataset.key;
    state.configValues[key] = field.value;
    if (state.configErrors[key]) {
      delete state.configErrors[key];
      field.closest(".settings-row")?.classList.remove("has-error");
      field.closest(".settings-row")?.querySelector(".settings-error")?.remove();
    }
    updateConfigButtons();
  });

  el.settingsForm.addEventListener("change", (event) => {
    const field = event.target.closest("[data-key]");
    if (!field) return;
    state.configValues[field.dataset.key] = field.value;
    updateConfigButtons();
    updateConfigFoot(field.dataset.key);
  });

  el.settingsForm.addEventListener("click", (event) => {
    const toggle = event.target.closest(".switch");
    if (toggle) {
      const key = toggle.dataset.key;
      state.configValues[key] = !state.configValues[key];
      toggle.setAttribute("aria-checked", String(state.configValues[key]));
      updateConfigButtons();
      return;
    }
    const reset = event.target.closest("[data-reset-key]");
    if (reset) {
      const key = reset.dataset.resetKey;
      const item = state.configItems.find((entry) => entry.key === key);
      if (!item) return;
      state.configValues[key] = item.type === "bool"
        ? Boolean(item.default)
        : (item.default === null || item.default === undefined ? "" : String(item.default));
      renderSettings();
      return;
    }
    const retry = event.target.closest('[data-state-action="retry-config"]');
    if (retry) loadConfig();
  });

  el.configSave.addEventListener("click", saveConfig);
  el.configReset.addEventListener("click", resetConfig);

  /* 对话框 */
  el.modalSubmit.addEventListener("click", submitForm);
  $("modal-cancel").addEventListener("click", () => closeModal("modal"));
  $("modal-close").addEventListener("click", () => closeModal("modal"));
  el.modalOverlay.addEventListener("click", (event) => {
    if (event.target === el.modalOverlay) closeModal("modal");
  });

  el.confirmDelete.addEventListener("click", () => {
    const action = state.pendingConfirm;
    if (typeof action === "function") action();
  });
  $("confirm-cancel").addEventListener("click", () => closeModal("confirm"));
  $("confirm-close").addEventListener("click", () => closeModal("confirm"));
  el.confirmOverlay.addEventListener("click", (event) => {
    if (event.target === el.confirmOverlay) closeModal("confirm");
  });

  /* 抽屉 */
  el.sidebarToggle.addEventListener("click", () => {
    if (el.sidebar.classList.contains("is-open")) closeSidebar();
    else openSidebar();
  });
  el.drawerClose.addEventListener("click", closeSidebar);
  el.scrim.addEventListener("click", closeSidebar);
  if (typeof mobileQuery.addEventListener === "function") {
    mobileQuery.addEventListener("change", syncSidebarMode);
  }

  document.addEventListener("keydown", handleDialogKeys);
}

function updateConfigFoot(key) {
  const row = el.settingsForm.querySelector(`.settings-row[data-key="${key}"]`);
  const item = state.configItems.find((entry) => entry.key === key);
  if (!row || !item) return;
  const foot = row.querySelector(".settings-foot");
  if (foot) foot.innerHTML = renderConfigFoot(item);
}

/* ---------------------------------------------------------------- 语言 */
async function loadI18n() {
  let payload = null;
  try {
    payload = await apiGet("i18n");
  } catch (err) {
    console.warn("读取语言文案失败，回退 bridge i18n", err);
  }

  if (payload && payload.pages && typeof payload.pages === "object") {
    state.i18n = payload.pages;
    state.locales = Array.isArray(payload.locales) ? payload.locales : Object.keys(payload.pages);
    state.i18nFallback = payload.fallback || FALLBACK_LOCALE;
  } else {
    const bridge = getBridge();
    const injected = bridge && typeof bridge.getI18n === "function" ? bridge.getI18n() : null;
    if (injected && typeof injected === "object") {
      const keys = Object.keys(injected);
      const looksLocaleMap = keys.length > 0 && keys.every((key) => /^[a-z]{2}(-[A-Za-z]{2,4})?$/.test(key));
      state.i18n = looksLocaleMap ? injected : {};
      state.locales = looksLocaleMap ? keys : [];
      state.i18nFallback = state.locales.includes("en") ? "en" : (state.locales[0] || FALLBACK_LOCALE);
    }
  }

  state.locale = pickLocale(state.rawLocale);
  document.documentElement.lang = state.locale;
}

/** 语言 / 主题变化时刷新页面文案与配色。 */
function applyContext(ctx) {
  if (!ctx) return;
  if (typeof ctx.isDark === "boolean") {
    document.documentElement.setAttribute("data-theme", ctx.isDark ? "dark" : "light");
  }
  const locale = ctx.locale || (typeof getBridge()?.getLocale === "function" ? getBridge().getLocale() : "");
  if (!locale || locale === state.rawLocale) return;
  state.rawLocale = locale;
  const next = pickLocale(locale);
  if (next === state.locale) return;
  state.locale = next;
  document.documentElement.lang = next;
  applyStaticTexts();
  renderModelList();
  if (state.view === "settings" && state.configLoaded) renderSettings();
  if (state.rows.length && state.view === "data") renderTable(state.rows);
  updateChrome();
}

function watchContext() {
  const bridge = getBridge();
  if (!bridge || typeof bridge.onContext !== "function") return;
  bridge.onContext((ctx) => applyContext(ctx));
}

/* ---------------------------------------------------------------- 静态文案 */
function applyStaticTexts() {
  document.title = t("title");
  applyI18nDom();

  el.sidebarSubtitle.textContent = t("sidebar.subtitle");
  el.sidebarSystemLabel.textContent = t("sidebar.system");
  el.modelFilter.placeholder = t("sidebar.filter_placeholder");
  el.modelFilter.setAttribute("aria-label", t("sidebar.filter_placeholder"));
  el.dataSearch.placeholder = t("table.search_placeholder");
  el.dataSearch.setAttribute("aria-label", t("table.search_placeholder"));
  el.refresh.querySelector("span").textContent = t("toolbar.refresh");
  el.sync.querySelector("span").textContent = t("toolbar.sync");
  el.create.querySelector("span").textContent = t("toolbar.create");
  el.configReset.querySelector("span").textContent = t("settings.reset");
  el.configSave.querySelector("span").textContent = t("settings.save");
  el.prev.setAttribute("aria-label", t("pagination.prev"));
  el.next.setAttribute("aria-label", t("pagination.next"));
  $("modal-cancel").textContent = t("modal.cancel");
  $("modal-submit").textContent = t("modal.save");
  $("confirm-cancel").textContent = t("modal.cancel");
  el.confirmDelete.textContent = t("confirm.delete_btn");
  el.searchHint.textContent = state.model ? t("search.hint_active") : t("search.hint_idle");
  if (!state.model) el.pageSummary.textContent = t("toolbar.select_model");
  if (state.models.length) el.modelSummary.textContent = t("summary.models", { n: state.models.length });
}

/* ---------------------------------------------------------------- 启动 */
async function init() {
  bindEvents();

  const bridge = getBridge();
  const ctx = bridge && typeof bridge.getContext === "function" ? bridge.getContext() : null;
  if (ctx) {
    // 上下文没给语言时退到浏览器语言，再不行才是英文
    state.rawLocale = ctx.locale || navigator.language || "";
    if (typeof ctx.isDark === "boolean") {
      document.documentElement.setAttribute("data-theme", ctx.isDark ? "dark" : "light");
    }
  } else {
    state.rawLocale = navigator.language || "";
  }

  await loadI18n();
  applyStaticTexts();
  watchContext();
  setToolbar();
  updateChrome();
  syncSidebarMode();
  await loadModels(true);
}

init();
