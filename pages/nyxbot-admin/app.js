/* ============================================================================
   NyxBot 数据管理中心 — 核心逻辑
   通过 AstrBot Plugin Pages Bridge 与后端 CRUD API 交互
   支持中英文国际化（自主加载 i18n JSON，不依赖 bridge.t()）
   ============================================================================ */

// ----- 常量 -----
const PAGE_SIZE = 20;
const PAGE_PREFIX = "pages.nyxbot-admin";

// ----- Bridge 引用 -----
const bridge = window.AstrBotPluginPage;

// ----- 国际化（自主加载 JSON，确保语言切换后实时生效） -----
let i18nData = {};       // { "zh-CN": { ... }, "en": { ... } }
let currentLocale = "zh-CN";

/** 将 Dashboard 传来的 locale（如 "en-US", "zh-CN", "ru"）标准化为 i18n 数据 key */
function normalizeLocale(locale) {
  if (!locale) return "zh-CN";
  if (locale.startsWith("zh")) return "zh-CN";
  if (locale.startsWith("en")) return "en";
  if (locale.startsWith("ru")) return "ru";
  return "zh-CN";
}

/**
 * 获取当前 Page 的翻译文案，缺失时返回 fallback。
 * 使用自主加载的 i18n JSON，不依赖 bridge.t()（其 locale 编码在 JWT 中，切换后不更新）。
 */
function t(key, fallback) {
  const fullKey = `${PAGE_PREFIX}.${key}`;
  // 1. 优先当前语言
  const keys = fullKey.split(".");
  let node = i18nData[currentLocale];
  for (const k of keys) {
    if (node == null) break;
    node = node[k];
  }
  if (typeof node === "string") return node;
  // 2. 回退到备用语言（zh-CN）
  if (currentLocale !== "zh-CN") {
    node = i18nData["zh-CN"];
    for (const k of keys) {
      if (node == null) break;
      node = node[k];
    }
    if (typeof node === "string") return node;
  }
  // 3. 回退到 en
  if (currentLocale !== "en") {
    node = i18nData["en"];
    for (const k of keys) {
      if (node == null) break;
      node = node[k];
    }
    if (typeof node === "string") return node;
  }
  // 4. 最终回退
  return fallback !== undefined ? fallback : key;
}

/** 从 bridge.getI18n() 加载 i18n 数据（AstrBot 自动读取 .astrbot-plugin/i18n/*.json） */
function loadI18n() {
  i18nData = bridge.getI18n() || {};
}

// ----- 状态 -----
let currentModel = null;
let currentPage = 1;
let currentTotal = 0;
let modelCache = null;
let currentRows = [];
let pendingDeleteId = null;
let editingRecord = null;

// ----- DOM 引用 -----
const $ = (sel) => document.querySelector(sel);

const modelList = $("#model-list");
const modelFilter = $("#model-filter");
const currentModelTitle = $("#current-model-title");
const recordCount = $("#record-count");
const syncBtn = $("#sync-btn");
const createBtn = $("#create-btn");
const tableContainer = $("#table-container");
const pagination = $("#pagination");
const prevPage = $("#prev-page");
const nextPage = $("#next-page");
const pageInfo = $("#page-info");
const modalOverlay = $("#modal-overlay");
const modalTitle = $("#modal-title");
const formFields = $("#form-fields");
const modalSubmit = $("#modal-submit");
const confirmOverlay = $("#confirm-overlay");
const confirmDetail = $("#confirm-detail");
const confirmDeleteBtn = $("#confirm-delete");
const toast = $("#toast");

// ----- 模型分类 → i18n key 映射 -----
const MODEL_CATEGORY_KEYS = {
  "alias": "basic",
  "nodes": "basic",
  "state_translation": "translation",
  "night_wave": "game_content",
  "relics": "game_content",
  "relic_rewards": "game_content",
  "sentinels": "game_content",
  "upgrades": "game_content",
  "warframes": "game_content",
  "warframe_ability": "game_content",
  "weapons": "game_content",
  "reward_pool": "game_content",
  "reward": "game_content",
  "riven_tion": "riven",
  "riven_tion_alias": "riven",
  "riven_analyse_trend": "riven",
  "riven_items": "riven",
  "orders_items": "market",
  "ephemeras": "market",
  "lich_sister_weapons": "market",
  "notification_history": "notification",
  "mission_subscribe": "notification",
  "mission_subscribe_user": "notification",
  "mission_subscribe_user_check_type": "notification",
};

function getCategoryKey(modelName) {
  return MODEL_CATEGORY_KEYS[modelName] || "other";
}

// ============================================================================
// 初始化
// ============================================================================
async function init() {
  try {
    // 加载内联 i18n 数据（同步，无网络请求）
    loadI18n();

    const context = await bridge.ready();
    console.log("NyxBot Admin: bridge ready", context);

    // 从 Dashboard 上下文初始化语言
    currentLocale = normalizeLocale(context.locale);
    applyLocale(currentLocale);

    document.title = t("title", "NyxBot Data Manager");
    renderStaticTexts();

    // 1. 通过 bridge.onContext 监听 Dashboard 语言切换（文档推荐方式）
    bridge.onContext((ctx) => {
      console.log("NyxBot Admin: onContext", ctx.locale);
      if (ctx.locale) {
        currentLocale = normalizeLocale(ctx.locale);
        applyLocale(ctx.locale);
        // 自主 i18n，无需等待 bridge.t()，直接重渲染
        renderStaticTexts();
        if (modelCache) refreshModelList();
        if (currentModel) {
          refreshUITexts();
          if (currentRows.length > 0) renderTable(currentRows);
          else loadData();
        }
        if (modalOverlay.style.display === "flex") closeModal();
      }
    });

    // 2. 通过 postMessage 兜底监听
    window.addEventListener("message", (event) => {
      if (event.source !== window.parent) return;
      const { type } = (event.data || {});
      if (!type) return;

      if (
        (type === "setTheme" || type === "themeChanged" || type === "changeTheme")
        && (event.data.theme === "dark" || event.data.theme === "light")
      ) {
        applyTheme(event.data.theme);
      }
      if (
        (type === "setLocale" || type === "localeChanged" || type === "changeLocale")
        && event.data.locale
      ) {
        currentLocale = normalizeLocale(event.data.locale);
        applyLocale(event.data.locale);
        renderStaticTexts();
        if (modelCache) refreshModelList();
        if (currentModel) {
          refreshUITexts();
          if (currentRows.length > 0) renderTable(currentRows);
        }
      }
    });

    // 3. 通过 CSS prefers-color-scheme 跟随系统主题
    initSystemTheme();

    await loadModelList();
  } catch (err) {
    console.error("初始化失败:", err);
    showToast(t("toast.init_failed", "Init failed") + ": " + err.message, "error");
  }
}

/** 渲染页面中的静态文本（不随数据变化的部分） */
function renderStaticTexts() {
  // 侧边栏
  const subtitle = document.querySelector(".sidebar-subtitle");
  if (subtitle) subtitle.textContent = t("sidebar.subtitle", "Data Manager");
  modelFilter.placeholder = t("sidebar.filter_placeholder", "Filter models...");

  // 工具栏按钮
  syncBtn.textContent = t("toolbar.sync", "🔄 Sync");
  syncBtn.title = t("toolbar.sync_title", "Sync from data source");
  createBtn.textContent = t("toolbar.create", "➕ New Record");

  // 分页按钮
  prevPage.textContent = t("pagination.prev", "Previous");
  nextPage.textContent = t("pagination.next", "Next");

  // 确认对话框
  $("#confirm-title").textContent = t("confirm.title", "Confirm Delete");
  $("#confirm-message").textContent = t("confirm.message", "Are you sure?");
  confirmDeleteBtn.textContent = t("confirm.delete_btn", "Delete");
  $("#confirm-cancel").textContent = t("modal.cancel", "Cancel");
  $("#modal-cancel").textContent = t("modal.cancel", "Cancel");
  modalSubmit.textContent = t("modal.save", "Save");

  // 模型列表（如果已缓存）
  if (modelCache) refreshModelList();
}

/** 刷新动态 UI 文本（选择模型后） */
function refreshUITexts() {
  if (!currentModel) {
    currentModelTitle.textContent = t("toolbar.select_model", "Select a model");
    return;
  }
  currentModelTitle.textContent = t(`models.${currentModel}`, currentModel);
  recordCount.textContent = t("toolbar.records_count", "{n} records").replace("{n}", currentTotal);
}

// ============================================================================
// Toast 通知
// ============================================================================
let toastTimer = null;

function showToast(message, type = "info") {
  if (toastTimer) clearTimeout(toastTimer);
  toast.textContent = message;
  toast.className = `toast toast-${type}`;
  toast.style.display = "block";
  toastTimer = setTimeout(() => { toast.style.display = "none"; }, 3000);
}

// ============================================================================
// 模型列表
// ============================================================================
async function loadModelList() {
  try {
    const data = await bridge.apiGet("models");
    modelCache = data.models || [];
    refreshModelList();
  } catch (err) {
    console.error("加载模型列表失败:", err);
    modelList.innerHTML = `<div class="loading-message">${escapeHtml(err.message)}</div>`;
  }
}

function refreshModelList() {
  if (!modelCache) return;
  const grouped = {};
  for (const m of modelCache) {
    const catKey = getCategoryKey(m.name);
    if (!grouped[catKey]) grouped[catKey] = [];
    grouped[catKey].push(m);
  }
  renderModelList(grouped);
}

function renderModelList(grouped) {
  const filterText = modelFilter.value.toLowerCase().trim();
  let html = "";

  for (const [catKey, models] of Object.entries(grouped)) {
    const filtered = filterText
      ? models.filter(m => t(`models.${m.name}`, m.name).toLowerCase().includes(filterText) || m.name.toLowerCase().includes(filterText))
      : models;

    if (filtered.length === 0) continue;

    const catLabel = t(`categories.${catKey}`, catKey);
    html += `<div class="model-category">${escapeHtml(catLabel)}</div>`;
    for (const m of filtered) {
      const isActive = currentModel === m.name;
      const displayName = t(`models.${m.name}`, m.name);
      html += `
        <div class="model-item${isActive ? " active" : ""}" data-model="${m.name}">
          <span class="model-name">${escapeHtml(displayName)}</span>
          ${m.has_sync ? '<span class="model-sync-badge" title="sync">↻</span>' : ""}
        </div>`;
    }
  }

  if (!html) {
    html = `<div class="loading-message">${t("sidebar.no_match", "No matching models")}</div>`;
  }

  modelList.innerHTML = html;

  modelList.querySelectorAll(".model-item").forEach(item => {
    item.addEventListener("click", () => selectModel(item.dataset.model));
  });

  // 更新静态文本（modelList 重新渲染后）
  refreshUITexts();
}

modelFilter.addEventListener("input", () => {
  if (modelCache) refreshModelList();
});

function selectModel(modelName) {
  currentModel = modelName;
  currentPage = 1;

  currentModelTitle.textContent = t(`models.${modelName}`, modelName);
  createBtn.disabled = false;

  const modelMeta = (modelCache || []).find(m => m.name === modelName);
  syncBtn.disabled = !modelMeta || !modelMeta.has_sync;
  syncBtn.classList.remove("syncing");

  refreshModelList();
  loadData();
}

// ============================================================================
// 数据加载与表格渲染
// ============================================================================
async function loadData() {
  if (!currentModel) return;

  tableContainer.innerHTML = `
    <div class="placeholder-message">
      <span class="loading-spinner"></span> ${t("table.loading", "Loading...")}
    </div>`;
  pagination.style.display = "none";

  try {
    const params = { page: currentPage, size: PAGE_SIZE };
    const data = await bridge.apiGet(`data/${currentModel}`, params);

    currentTotal = data.total || 0;
    recordCount.textContent = t("toolbar.records_count", "{n} records").replace("{n}", currentTotal);
    renderTable(data.items || []);
    renderPagination();
  } catch (err) {
    console.error("加载数据失败:", err);
    tableContainer.innerHTML = `
      <div class="placeholder-message" style="color: var(--danger);">
        ${t("table.load_failed", "Failed to load")}: ${escapeHtml(err.message)}
      </div>`;
  }
}

function renderTable(items) {
  currentRows = items;

  if (items.length === 0) {
    tableContainer.innerHTML = `<div class="placeholder-message">${t("table.no_data", "No data")}</div>`;
    return;
  }

  const columns = Object.keys(items[0]);
  const actionsLabel = t("table.actions", "Actions");
  const editLabel = t("modal.edit_btn", "Edit");
  const deleteLabel = t("modal.delete_btn", "Delete");

  let html = '<div class="table-wrapper"><table><thead><tr>';
  for (const col of columns) {
    html += `<th>${escapeHtml(col)}</th>`;
  }
  html += `<th style="width: 100px;">${escapeHtml(actionsLabel)}</th>`;
  html += '</tr></thead><tbody>';

  for (const row of items) {
    html += `<tr data-row-id="${escapeHtml(String(row.id))}">`;
    for (const col of columns) {
      const value = row[col];
      if (value === null || value === undefined) {
        html += '<td class="null-value">—</td>';
      } else {
        html += `<td title="${escapeHtml(String(value))}">${escapeHtml(String(value))}</td>`;
      }
    }
    html += `
      <td class="actions">
        <button class="btn-edit" data-id="${escapeHtml(String(row.id))}">${escapeHtml(editLabel)}</button>
        <button class="btn-delete" data-id="${escapeHtml(String(row.id))}">${escapeHtml(deleteLabel)}</button>
      </td>`;
    html += '</tr>';
  }

  html += '</tbody></table></div>';
  tableContainer.innerHTML = html;

  tableContainer.querySelectorAll(".btn-edit").forEach(btn => {
    btn.addEventListener("click", () => openEditModal(btn.dataset.id));
  });
  tableContainer.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", () => openDeleteConfirm(btn.dataset.id));
  });
}

// ============================================================================
// 分页
// ============================================================================
prevPage.addEventListener("click", () => {
  if (currentPage > 1) { currentPage--; loadData(); }
});

nextPage.addEventListener("click", () => {
  const totalPages = Math.ceil(currentTotal / PAGE_SIZE) || 1;
  if (currentPage < totalPages) { currentPage++; loadData(); }
});

function goToPage(page) {
  const totalPages = Math.ceil(currentTotal / PAGE_SIZE) || 1;
  if (page < 1 || page > totalPages || page === currentPage) return;
  currentPage = page;
  loadData();
}

function renderPagination() {
  const totalPages = Math.ceil(currentTotal / PAGE_SIZE) || 1;

  if (totalPages <= 1) {
    pagination.style.display = "none";
    return;
  }

  pagination.style.display = "flex";
  prevPage.disabled = currentPage <= 1;
  nextPage.disabled = currentPage >= totalPages;

  const range = 3;
  let start = Math.max(1, currentPage - range);
  let end = Math.min(totalPages, currentPage + range);

  while (end - start < range * 2 && (start > 1 || end < totalPages)) {
    if (start > 1) start--;
    else if (end < totalPages) end++;
    else break;
  }

  let html = "";
  if (start > 1) {
    html += `<button class="btn btn-page" data-page="1">1</button>`;
    if (start > 2) html += `<span class="page-ellipsis">…</span>`;
  }
  for (let p = start; p <= end; p++) {
    html += `<button class="btn btn-page${p === currentPage ? " active" : ""}" data-page="${p}">${p}</button>`;
  }
  if (end < totalPages) {
    if (end < totalPages - 1) html += `<span class="page-ellipsis">…</span>`;
    html += `<button class="btn btn-page" data-page="${totalPages}">${totalPages}</button>`;
  }

  pageInfo.innerHTML = html;
  pageInfo.querySelectorAll("button[data-page]").forEach(btn => {
    btn.addEventListener("click", () => goToPage(parseInt(btn.dataset.page)));
  });
}

// ============================================================================
// 创建 / 编辑 模态框
// ============================================================================
createBtn.addEventListener("click", () => {
  editingRecord = null;
  openFormModal(null);
});

function openEditModal(recordId) {
  editingRecord = recordId;
  openFormModal(recordId);
}

async function openFormModal(recordId) {
  modalTitle.textContent = recordId
    ? t("modal.edit_record", "Edit Record")
    : t("modal.new_record", "New Record");
  formFields.innerHTML = `<div style="text-align:center;padding:20px;"><span class="loading-spinner"></span> ${t("modal.load_form", "Loading form...")}</div>`;
  modalOverlay.style.display = "flex";

  try {
    if (recordId) {
      const record = currentRows.find(item => String(item.id) === String(recordId));
      if (record) {
        renderForm(record);
      } else {
        formFields.innerHTML = `<div style="text-align:center;padding:20px;color:var(--text-muted);">${t("modal.record_not_in_cache", "Record not found")}</div>`;
      }
    } else {
      renderForm(null);
    }
  } catch (err) {
    formFields.innerHTML = `<div style="color:var(--danger);text-align:center;padding:20px;">${escapeHtml(err.message)}</div>`;
  }
}

function renderForm(record) {
  let fields = [];
  const ths = tableContainer.querySelectorAll("thead th");
  if (ths.length > 0) {
    ths.forEach(th => {
      const text = th.textContent.trim();
      const actionsLabel = t("table.actions", "Actions");
      if (text !== actionsLabel) fields.push(text);
    });
  }
  if (fields.length === 0 && record) fields = Object.keys(record);
  if (fields.length === 0 && currentRows.length > 0) fields = Object.keys(currentRows[0]);

  if (fields.length === 0) {
    formFields.innerHTML = `<div style="text-align:center;padding:20px;color:var(--text-muted);">${t("modal.cannot_determine_fields", "Cannot determine fields")}</div>`;
    return;
  }

  let html = "";
  for (const field of fields) {
    const value = record ? (record[field] ?? "") : "";
    // 使用 i18n 翻译标签，缺失时回退到原始字段名
    const label = t(`fields.${field}`, field);
    // 使用 i18n 翻译输入提示，优先精确匹配 → 回退 default
    const placeholder = t(`placeholders.${field}`, t("placeholders.default", ""));
    // ID 类字段设为只读（字段名为 "id" 或 "ids"）
    const isIdField = field === "id" || field === "ids";
    html += `
      <div class="form-group">
        <label for="field-${field}">${escapeHtml(label)}</label>
        <input
          type="text"
          id="field-${field}"
          name="${field}"
          value="${escapeHtml(String(value))}"
          placeholder="${escapeHtml(placeholder)}"
          ${isIdField ? "readonly" : ""}
        />
      </div>`;
  }
  formFields.innerHTML = html;
}

modalSubmit.addEventListener("click", async () => {
  const inputs = formFields.querySelectorAll("input, textarea");
  const data = {};
  let recordId = null;

  for (const input of inputs) {
    const name = input.name;
    const value = input.value.trim();
    // 通过原始字段名（非翻译后的 label）判断 ID 字段
    if (name === "id" || name === "ids") {
      recordId = value;
    } else {
      data[name] = value;
    }
  }

  // 新建时若填写了 ID，一并提交
  if (!editingRecord && recordId) {
    data.id = recordId;
  }

  try {
    if (editingRecord) {
      const raw = await bridge.apiPost(`data/${currentModel}/update`, { id: editingRecord, ...data });
      const result = unwrapResult(raw);
      if (result.ok) {
        showToast(t("toast.update_success", "Updated"), "success");
        closeModal();
        loadData();
      } else {
        showToast(t("toast.update_failed", "Update failed") + ": " + (result.error || t("toast.unknown_error", "Unknown")), "error");
      }
    } else {
      const raw = await bridge.apiPost(`data/${currentModel}/create`, data);
      const result = unwrapResult(raw);
      if (result.ok) {
        showToast(t("toast.create_success", "Created"), "success");
        closeModal();
        loadData();
      } else {
        showToast(t("toast.create_failed", "Create failed") + ": " + (result.error || t("toast.unknown_error", "Unknown")), "error");
      }
    }
  } catch (err) {
    showToast(t("toast.operation_failed", "Operation failed") + ": " + err.message, "error");
  }
});

function closeModal() {
  modalOverlay.style.display = "none";
  editingRecord = null;
}

$("#modal-close").addEventListener("click", closeModal);
$("#modal-cancel").addEventListener("click", closeModal);
modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) closeModal();
});

// ============================================================================
// 删除确认
// ============================================================================
function openDeleteConfirm(recordId) {
  pendingDeleteId = recordId;

  const row = tableContainer.querySelector(`[data-id="${recordId}"]`)?.closest("tr");
  if (row) {
    const cells = row.querySelectorAll("td");
    const details = [];
    const ths = tableContainer.querySelectorAll("thead th");
    cells.forEach((td, i) => {
      const actionsLabel = t("table.actions", "Actions");
      if (i < ths.length - 1) {
        const colName = ths[i]?.textContent?.trim() || `col${i}`;
        details.push(`${colName}: ${td.textContent?.trim()}`);
      }
    });
    confirmDetail.textContent = details.join(" | ");
  } else {
    confirmDetail.textContent = `ID: ${recordId}`;
  }

  confirmOverlay.style.display = "flex";
}

confirmDeleteBtn.addEventListener("click", async () => {
  if (!pendingDeleteId) return;

  try {
    const raw = await bridge.apiPost(`data/${currentModel}/delete`, { id: pendingDeleteId });
    const result = unwrapResult(raw);
    if (result.ok) {
      showToast(t("toast.delete_success", "Deleted"), "success");
      closeConfirm();
      loadData();
    } else {
      showToast(t("toast.delete_failed", "Delete failed") + ": " + (result.error || t("toast.unknown_error", "Unknown")), "error");
    }
  } catch (err) {
    showToast(t("toast.delete_failed", "Delete failed") + ": " + err.message, "error");
  }
});

function closeConfirm() {
  confirmOverlay.style.display = "none";
  pendingDeleteId = null;
}

$("#confirm-close").addEventListener("click", closeConfirm);
$("#confirm-cancel").addEventListener("click", closeConfirm);
confirmOverlay.addEventListener("click", (e) => {
  if (e.target === confirmOverlay) closeConfirm();
});

// ============================================================================
// 数据同步
// ============================================================================
syncBtn.addEventListener("click", async () => {
  if (!currentModel) return;

  syncBtn.classList.add("syncing");
  syncBtn.disabled = true;
  const modelLabel = t(`models.${currentModel}`, currentModel);
  showToast(t("toolbar.syncing", "Syncing...").replace("{model}", modelLabel), "info");

  try {
    const raw = await bridge.apiPost(`data/${currentModel}/sync`);
    const result = unwrapResult(raw);
    if (result.ok) {
      showToast(result.message || t("toolbar.sync_success", "Sync completed").replace("{model}", modelLabel), "success");
      loadData();
    } else {
      showToast(t("toolbar.sync_failed", "Sync failed") + ": " + (result.error || t("toast.unknown_error", "Unknown")), "error");
    }
  } catch (err) {
    showToast(t("toolbar.sync_failed", "Sync failed") + ": " + err.message, "error");
  } finally {
    syncBtn.classList.remove("syncing");
    const modelMeta = (modelCache || []).find(m => m.name === currentModel);
    syncBtn.disabled = !modelMeta || !modelMeta.has_sync;
  }
});

// ============================================================================
// 通用 API 结果提取
// ============================================================================
function unwrapResult(raw) {
  if (!raw) return { ok: false, data: null, error: "No response" };
  if (typeof raw.success === "boolean") {
    return { ok: raw.success, data: raw.data || null, error: raw.error || null };
  }
  if (raw.data && typeof raw.data.success === "boolean") {
    return { ok: raw.data.success, data: raw.data.data || null, error: raw.data.error || null };
  }
  console.warn("未知 API 返回格式:", raw);
  return { ok: true, data: raw, error: null };
}

// ============================================================================
// 工具函数
// ============================================================================
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ============================================================================
// 主题 & 语言同步
// ============================================================================

/**
 * 应用主题到 <html data-theme>
 */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme || "dark");
}

/**
 * 应用语言到 <html lang>
 */
function applyLocale(locale) {
  document.documentElement.setAttribute("lang", locale || "zh-CN");
}

/**
 * 通过 CSS prefers-color-scheme 媒体查询跟随系统主题。
 * iframe 的 origin 为 null（AstrBot 通过 blob: URL 加载），
 * 无法访问 parent 的 localStorage，因此使用系统主题作为替代方案。
 * Dashboard 主题通常也跟随系统设置。
 */
function initSystemTheme() {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  applyTheme(mq.matches ? "dark" : "light");

  // 监听系统主题变化
  try {
    mq.addEventListener("change", (e) => {
      applyTheme(e.matches ? "dark" : "light");
    });
  } catch {
    // 旧浏览器兼容
    mq.addListener((e) => {
      applyTheme(e.matches ? "dark" : "light");
    });
  }
}

// ============================================================================
// 键盘快捷键
// ============================================================================
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (modalOverlay.style.display === "flex") closeModal();
    else if (confirmOverlay.style.display === "flex") closeConfirm();
  }
});

// ============================================================================
// 启动
// ============================================================================
init();
