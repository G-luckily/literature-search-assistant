const state = {
  plan: null,
  papers: [],
  visiblePapers: [],
  selectedKeys: new Set(),
  savedPapers: [],
  history: [],
  archiveItems: [],
  archiveDetail: null,
  archiveSelectedId: "",
  reportPath: "",
  config: null,
  sourceMeta: {},
  activePage: "search",
  workflowLabel: "待命",
  workflowDetail: "等待执行检索。",
  outputView: "ask",
  workspaceSnapshot: null,
  workspaceRestored: false,
  theme: document.documentElement.dataset.theme || "dark",
  intentSidebarCollapsed: false,
  selectedMockTaskId: "",
};

const THEME_STORAGE_KEY = "litassist.theme.v1";
const SAVED_PAPERS_STORAGE_KEY = "litassist.savedPapers.v1";
const HISTORY_STORAGE_KEY = "litassist.history.v1";
const WORKSPACE_SNAPSHOT_STORAGE_KEY = "litassist.workspaceSnapshot.v1";

const MOCK_HISTORY = [
  { id: "ai-zotero", title: "AI 辅助文献检索与 Zotero 协同管理", prompt: "我想研究 AI 辅助文献检索与 Zotero 协同管理，重点关注近五年的工具实践、知识组织和研究工作流。" },
  { id: "youth-ai", title: "青年群体与人工智能使用经验", prompt: "我想研究青年群体与人工智能使用经验，关注教育、就业和社会参与。" },
  { id: "emotion-capital", title: "公考青年的情感资本困境", prompt: "我想研究公考青年的情感资本困境，需要做文献检索回顾。" },
  { id: "social-policy-ai", title: "人工智能与社会政策治理", prompt: "研究人工智能与社会政策治理的最新文献，包括风险治理、公共服务和算法责任。" },
  { id: "knowledge-workflow", title: "知识管理工具与研究工作流", prompt: "我想比较 Zotero、Notion 与 AI 工具在学术研究工作流中的协同方式。" },
  { id: "lit-review-method", title: "系统综述方法与智能检索策略", prompt: "我想研究系统综述方法与智能检索策略，重点关注检索式生成和证据筛选。" },
];

const els = {
  workspaceOverview: document.querySelector("#workspace-overview"),
  pageViews: [...document.querySelectorAll(".page-view")],
  themeToggle: document.querySelector("#theme-toggle"),
  intentSidebar: document.querySelector("#intent-sidebar"),
  intentSidebarToggle: document.querySelector("#intent-sidebar-toggle"),
  newResearchButton: document.querySelector("#new-research-button"),
  intentHistoryList: document.querySelector("#intent-history-list"),
  need: document.querySelector("#need"),
  zhKeywords: document.querySelector("#zh-keywords"),
  enKeywords: document.querySelector("#en-keywords"),
  limit: document.querySelector("#limit"),
  fromYear: document.querySelector("#from-year"),
  preferRecent: document.querySelector("#prefer-recent"),
  searchSettingsSummary: document.querySelector("#search-settings-summary"),
  status: document.querySelector("#status"),
  planButton: document.querySelector("#plan-button"),
  searchButton: document.querySelector("#search-button"),
  dryRunButton: document.querySelector("#dry-run-button"),
  applyImport: document.querySelector("#apply-import"),
  useLlm: document.querySelector("#use-llm"),
  llmEnabled: document.querySelector("#llm-enabled"),
  llmProvider: document.querySelector("#llm-provider"),
  llmModel: document.querySelector("#llm-model"),
  llmEndpoint: document.querySelector("#llm-endpoint"),
  llmApiKey: document.querySelector("#llm-api-key"),
  llmClearKey: document.querySelector("#llm-clear-key"),
  llmTimeout: document.querySelector("#llm-timeout"),
  saveLlmConfig: document.querySelector("#save-llm-config"),
  llmConfigStatus: document.querySelector("#llm-config-status"),
  sourceStatus: document.querySelector("#source-status"),
  sourceConfigSummary: document.querySelector("#source-config-summary"),
  modelConfigSummary: document.querySelector("#model-config-summary"),
  semanticScholarApiKey: document.querySelector("#semantic-scholar-api-key"),
  googleScholarApiKey: document.querySelector("#google-scholar-api-key"),
  webOfScienceApiKey: document.querySelector("#web-of-science-api-key"),
  saveSourceConfig: document.querySelector("#save-source-config"),
  sourceConfigStatus: document.querySelector("#source-config-status"),
  filterText: document.querySelector("#filter-text"),
  sortBy: document.querySelector("#sort-by"),
  pdfOnly: null,
  selectVisible: document.querySelector("#select-visible"),
  clearSelection: document.querySelector("#clear-selection"),
  saveSelected: document.querySelector("#save-selected"),
  savedFilterText: document.querySelector("#saved-filter-text"),
  savedAuthorFilter: document.querySelector("#saved-author-filter"),
  clearSaved: document.querySelector("#clear-saved"),
  keywordOutput: document.querySelector("#keyword-output"),
  planDetailOutput: document.querySelector("#plan-detail-output"),
  errorOutput: document.querySelector("#error-output"),
  papersEmpty: document.querySelector("#papers-empty"),
  papers: document.querySelector("#papers"),
  savedPapers: document.querySelector("#saved-papers"),
  savedEmpty: document.querySelector("#saved-empty"),
  savedCount: document.querySelector("#saved-count"),
  savedImportedCount: document.querySelector("#saved-imported-count"),
  savedPendingCount: document.querySelector("#saved-pending-count"),
  savedYearFilter: document.querySelector("#saved-year-filter"),
  savedSourceFilter: document.querySelector("#saved-source-filter"),
  savedTagFilter: document.querySelector("#saved-tag-filter"),
  savedImportedFilter: document.querySelector("#saved-imported-filter"),
  historyFilterText: document.querySelector("#history-filter-text"),
  clearHistory: document.querySelector("#clear-history"),
  historyList: document.querySelector("#history-list"),
  historyEmpty: document.querySelector("#history-empty"),
  historyCount: document.querySelector("#history-count"),
  archiveDetail: document.querySelector("#archive-detail"),
  paperTemplate: document.querySelector("#paper-template"),
  selectedSourceCount: document.querySelector("#selected-source-count"),
  reportLink: document.querySelector("#report-link"),
  selectionCount: document.querySelector("#selection-count"),
  resultsCount: document.querySelector("#results-count"),
  outputTabs: document.querySelector("#output-tabs"),
  outputTabPlan: document.querySelector("#output-tab-plan"),
  outputTabSearch: document.querySelector("#output-tab-search"),
  flowPaneAsk: document.querySelector("#flow-pane-ask"),
  flowPanePlan: document.querySelector("#flow-pane-plan"),
  flowPaneSearch: document.querySelector("#flow-pane-search"),
  flowPlanAction: document.querySelector("#flow-plan-action"),
  flowSearchAction: document.querySelector("#flow-search-action"),
  topNavLinks: [...document.querySelectorAll(".topbar-link[data-page]")],
  sidebarNavLinks: [...document.querySelectorAll(".sidebar-link[data-page]")],
};

const sourceInputs = [...document.querySelectorAll('input[name="source"]')];

els.themeToggle.addEventListener("click", () => toggleTheme());
els.intentSidebarToggle.addEventListener("click", () => toggleIntentSidebar());
els.newResearchButton.addEventListener("click", () => startNewResearch());
els.planButton.addEventListener("click", () => runPlan());
els.searchButton.addEventListener("click", () => runSearch());
els.dryRunButton.addEventListener("click", () => importZotero());
els.saveLlmConfig.addEventListener("click", () => saveLlmConfig());
els.saveSourceConfig.addEventListener("click", () => saveSourceConfig());
els.llmProvider.addEventListener("change", () => {
  applyProviderDefaults();
  updateDashboard();
});
els.llmEnabled.addEventListener("change", () => updateDashboard());
els.need.addEventListener("input", () => persistWorkspaceSnapshot());
els.need.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    runSearch();
  }
});

els.applyImport.addEventListener("change", () => persistWorkspaceSnapshot());
els.filterText.addEventListener("input", () => applyResultControls());
els.sortBy.addEventListener("change", () => applyResultControls());
els.selectVisible.addEventListener("click", () => selectVisiblePapers());
els.clearSelection.addEventListener("click", () => clearSelection());
els.saveSelected.addEventListener("click", () => saveSelectedPapers());
els.savedFilterText.addEventListener("input", () => renderSavedPapers());
els.savedAuthorFilter.addEventListener("input", () => renderSavedPapers());
els.savedYearFilter.addEventListener("input", () => renderSavedPapers());
els.savedSourceFilter.addEventListener("input", () => renderSavedPapers());
els.savedTagFilter.addEventListener("input", () => renderSavedPapers());
els.savedImportedFilter.addEventListener("change", () => renderSavedPapers());
els.clearSaved.addEventListener("click", () => clearSavedPapers());
els.historyFilterText.addEventListener("input", () => renderHistory());
els.clearHistory.addEventListener("click", () => loadArchive(true));
els.outputTabPlan.addEventListener("click", () => setFlowStep("plan"));
els.outputTabSearch.addEventListener("click", () => setFlowStep("search"));
els.flowPlanAction.addEventListener("click", () => runPlan());
els.flowSearchAction.addEventListener("click", () => runSearch());
for (const input of sourceInputs) {
  input.addEventListener("change", () => {
    renderSourceBadges();
    updateDashboard();
    persistWorkspaceSnapshot();
  });
}

for (const link of [...els.topNavLinks, ...els.sidebarNavLinks]) {
  link.addEventListener("click", (event) => handleNavigation(event, link));
}

initializeTheme();
loadWorkspaceMemory();
setActivePage(resolveInitialPage(), false);
loadConfig();
loadArchive();
updateDashboard();
renderSavedPapers();
renderHistory();
renderMockHistory();
updateSearchSettingsSummary();
setFlowStep("ask");

window.addEventListener("hashchange", () => setActivePage(resolveInitialPage(), false));

function initializeTheme() {
  const forcedTheme = new URLSearchParams(location.search).get("theme");
  if (forcedTheme === "light" || forcedTheme === "dark") {
    applyTheme(forcedTheme, false);
    return;
  }
  try {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === "light" || storedTheme === "dark") {
      applyTheme(storedTheme, false);
      return;
    }
  } catch {}
  applyTheme(resolveSystemTheme(), false);
}

function toggleTheme() {
  applyTheme(state.theme === "light" ? "dark" : "light");
}

function toggleIntentSidebar() {
  state.intentSidebarCollapsed = !state.intentSidebarCollapsed;
  document.body.dataset.sidebar = state.intentSidebarCollapsed ? "collapsed" : "expanded";
  els.intentSidebarToggle.setAttribute(
    "aria-expanded",
    state.intentSidebarCollapsed ? "false" : "true",
  );
}

function renderMockHistory() {
  els.intentHistoryList.innerHTML = "";
  for (const task of MOCK_HISTORY) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `intent-history-item ${task.id === state.selectedMockTaskId ? "active" : ""}`;
    button.textContent = task.title;
    button.title = task.title;
    button.addEventListener("click", () => {
      state.selectedMockTaskId = task.id;
      window.onSelectTask(task.id);
      renderMockHistory();
    });
    els.intentHistoryList.append(button);
  }
}

window.onSelectTask = function onSelectTask(taskId) {
  const task = MOCK_HISTORY.find((item) => item.id === taskId);
  if (!task) return;
  els.need.value = task.prompt;
  state.selectedMockTaskId = taskId;
  setActivePage("search");
  setStatus("已载入历史检索意图。");
  persistWorkspaceSnapshot();
};

function startNewResearch() {
  els.need.value = "";
  els.zhKeywords.value = "";
  els.enKeywords.value = "";
  els.fromYear.value = "";
  els.limit.value = "8";
  els.preferRecent.checked = true;
  els.useLlm.checked = false;
  state.selectedMockTaskId = "";
  state.plan = null;
  state.papers = [];
  state.visiblePapers = [];
  state.sourceMeta = {};
  state.reportPath = "";
  state.selectedKeys = new Set();
  clearErrors();
  els.keywordOutput.innerHTML = "";
  els.planDetailOutput.innerHTML = "";
  updateReportLink("");
  applyResultControls();
  setFlowStep("ask");
  setStatus("已新建文献课题。");
  renderMockHistory();
  persistWorkspaceSnapshot();
  setActivePage("search");
}

function applyTheme(theme, persist = true) {
  const normalized = theme === "light" ? "light" : "dark";
  state.theme = normalized;
  document.documentElement.dataset.theme = normalized;
  if (persist) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, normalized);
    } catch {}
  }
  const nextMode = normalized === "dark" ? "日间模式" : "夜间模式";
  const buttonLabel = normalized === "dark" ? "日间" : "夜间";
  els.themeToggle.textContent = buttonLabel;
  els.themeToggle.setAttribute("aria-label", `切换到${nextMode}`);
  els.themeToggle.setAttribute("title", `切换到${nextMode}`);
}

function resolveSystemTheme() {
  try {
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  } catch {
    return "dark";
  }
}

function handleNavigation(event, link) {
  event.preventDefault();
  const page = link.dataset.page;
  if (!page) return;
  setActivePage(page);
}

function resolveInitialPage() {
  const hash = location.hash.replace(/^#/, "");
  if (["search", "collection", "archive", "settings"].includes(hash)) return hash;
  return "search";
}

function setActivePage(page, updateHash = true) {
  const normalized = ["search", "collection", "archive", "settings"].includes(page)
    ? page
    : "search";

  state.activePage = normalized;
  document.body.dataset.page = normalized;

  for (const view of els.pageViews) {
    const isActive = view.id === `${normalized}-page`;
    view.classList.toggle("active", isActive);
    view.hidden = !isActive;
  }

  activateLink(els.topNavLinks, normalized);
  activateLink(els.sidebarNavLinks, normalized);

  if (normalized === "search") {
    setFlowStep(state.papers.length ? "search" : state.plan ? "plan" : "ask");
  }

  if (updateHash) {
    history.replaceState(null, "", `#${normalized}`);
  }
}

function setFlowStep(step) {
  const hasPlan = Boolean(state.plan);
  const hasResults = state.papers.length > 0;
  let normalized = step;
  if (normalized === "search" && !hasResults) normalized = hasPlan ? "plan" : "ask";
  if (normalized === "plan" && !hasPlan) normalized = hasResults ? "search" : "ask";
  if (!["ask", "plan", "search"].includes(normalized)) normalized = "ask";

  if (els.outputTabs) {
    els.outputTabs.hidden = !(hasPlan || hasResults);
  }
  if (els.outputTabPlan) {
    const active = normalized === "plan";
    els.outputTabPlan.classList.toggle("active", active);
    els.outputTabPlan.setAttribute("aria-selected", active ? "true" : "false");
    els.outputTabPlan.disabled = !hasPlan;
  }
  if (els.outputTabSearch) {
    const active = normalized === "search";
    els.outputTabSearch.classList.toggle("active", active);
    els.outputTabSearch.setAttribute("aria-selected", active ? "true" : "false");
    els.outputTabSearch.disabled = !hasResults;
  }

  els.flowPaneAsk.hidden = normalized !== "ask";
  els.flowPanePlan.hidden = normalized !== "plan";
  els.flowPaneSearch.hidden = normalized !== "search";
  state.outputView = normalized;
  document.body.dataset.output = normalized;
  if (state.workspaceRestored) {
    persistWorkspaceSnapshot();
  }
}

function updateSearchSettingsSummary() {
  if (!els.searchSettingsSummary) return;
  const zhCount = splitKeywords(els.zhKeywords.value).length;
  const enCount = splitKeywords(els.enKeywords.value).length;
  const keywordCount = zhCount + enCount;
  const fromYear = els.fromYear.value.trim();
  const limit = els.limit.value.trim() || "8";
  const parts = [
    keywordCount ? `${keywordCount} 组关键词` : "关键词待补充",
    fromYear ? `${fromYear} 起` : "年份待设置",
    `每源 ${limit} 条`,
  ];
  if (els.useLlm.checked) parts.push("AI 优化已启用");
  els.searchSettingsSummary.textContent = parts.join(" / ");
}

function activateLink(links, targetId) {
  if (!links.length) return;
  for (const link of links) {
    const isActive = link.dataset.page === targetId;
    link.classList.toggle("active", isActive);
    link.setAttribute("aria-current", isActive ? "page" : "false");
  }
}

function payloadBase() {
  return {
    need: els.need.value.trim(),
    zhKeywords: splitKeywords(els.zhKeywords.value),
    enKeywords: splitKeywords(els.enKeywords.value),
    useLlm: els.useLlm.checked,
  };
}

function splitKeywords(value) {
  return value
    .split(/[,，;；\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function selectedSources() {
  return sourceInputs.filter((input) => input.checked).map((input) => input.value);
}

async function runPlan() {
  clearErrors();
  setWorkflowStatus("规划中", "正在生成关键词矩阵与检索式。");
  setFlowStep("plan");
  setBusy(true, "正在生成检索计划。");
  try {
    const data = await postJson("/api/plan", payloadBase());
    state.plan = data.plan;
    renderPlan(data.plan);
    setFlowStep("plan");
    persistWorkspaceSnapshot();
    setStatus("检索计划已生成。");
    setWorkflowStatus("方案就绪", "研究问题已经拆解为可执行检索步骤。");
    addHistoryEntry("生成检索方案", {
      need: payloadBase().need,
      sources: selectedSources(),
      planner: data.plan?.planner || "rule",
    });
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function runSearch() {
  const payload = {
    ...payloadBase(),
    sources: selectedSources(),
    limit: Number(els.limit.value || 8),
    fromYear: els.fromYear.value ? Number(els.fromYear.value) : null,
    preferRecent: els.preferRecent.checked,
  };
  clearErrors();
  setWorkflowStatus("检索中", "正在调用已选数据库并整理候选结果。");
  setFlowStep("search");
  setBusy(true, "正在检索，开放 API 可能需要几十秒。");
  try {
    const data = await postJson("/api/search", payload);
    state.plan = data.plan;
    state.papers = data.papers || [];
    state.sourceMeta = data.sourceMeta || {};
    state.selectedKeys = new Set();
    state.reportPath = data.reportPath || "";
    renderPlan(data.plan);
    renderErrors(data.errors || {});
    renderSourceSummary(data.errors || {}, state.sourceMeta);
    updateReportLink(data.reportUrl);
    applyResultControls();
    setFlowStep("search");
    persistWorkspaceSnapshot();
    await loadArchive();
    const semanticNote = semanticStatusNote(state.sourceMeta.semantic_scholar);
    setStatus(
      `检索完成：${state.papers.length} 篇候选文献${payload.fromYear ? `，${payload.fromYear} 年以来` : ""}。${semanticNote ? ` ${semanticNote}` : ""}`,
    );
    setWorkflowStatus(
      Object.keys(data.errors || {}).length ? "部分完成" : "已完成",
      Object.keys(data.errors || {}).length
        ? "部分数据源返回错误，已保留成功结果。"
        : "检索、去重与排序已完成。",
    );
    addHistoryEntry("执行高级检索", {
      need: payload.need,
      sources: payload.sources,
      papers: state.papers.length,
      hasError: Object.keys(data.errors || {}).length > 0,
    });
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function importZotero() {
  const selectedPapers = state.papers.filter((paper) =>
    state.selectedKeys.has(paperKey(paper)),
  );
  if (!selectedPapers.length) {
    setStatus("没有选中文献。");
    return;
  }
  const apply = els.applyImport.checked;
  setWorkflowStatus(apply ? "同步中" : "预演中", apply ? "正在写入 Zotero。" : "正在执行 Zotero 预演。");
  setBusy(true, apply ? "正在写入 Zotero。" : "正在执行 Zotero 预演。");
  try {
    const data = await postJson("/api/import-zotero", {
      papers: selectedPapers,
      limit: selectedPapers.length,
      apply,
    });
    const result = data.result || {};
    setStatus(
      `Zotero：已创建 ${result.created || 0}，已跳过 ${result.skipped || 0}，错误 ${(result.errors || []).length}`,
    );
    setWorkflowStatus(
      apply ? "已同步" : "预演中",
      apply ? "Zotero 同步完成。" : "已完成 Zotero 预演检查。",
    );
    if (result.errors && result.errors.length) {
      showError(result.errors.join("\n"));
    }
    addHistoryEntry(apply ? "写入 Zotero" : "预演导入 Zotero", {
      selected: selectedPapers.length,
      created: result.created || 0,
      skipped: result.skipped || 0,
      errors: (result.errors || []).length,
      applied: apply,
    });
    if (apply) {
      for (const paper of selectedPapers) {
        paper.imported = true;
        paper.zoteroImported = true;
      }
      persistWorkspaceMemory();
      renderPapers(state.visiblePapers);
      renderSavedPapers();
    }
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "读取配置失败。");
    }
    state.config = data;
    renderConfig(data);
    restoreWorkspaceSnapshot();
  } catch (error) {
    setConfigStatus(`配置读取失败：${error.message}`);
    setSourceConfigStatus(`配置读取失败：${error.message}`);
    renderSourceBadges();
    updateDashboard();
    restoreWorkspaceSnapshot();
  }
}

function renderConfig(config) {
  const general = config.general || {};
  els.fromYear.value = general.fromYear || "";
  els.preferRecent.checked = general.preferRecent !== false;
  const llm = config.llm || {};
  els.llmEnabled.checked = Boolean(llm.enabled);
  els.useLlm.checked = Boolean(llm.enabled);
  els.llmProvider.value = llm.provider || "deepseek";
  els.llmModel.value = llm.model || defaultModel(els.llmProvider.value);
  els.llmEndpoint.value = llm.endpoint || defaultEndpoint(els.llmProvider.value);
  els.llmTimeout.value = llm.requestTimeoutSeconds || 45;
  els.llmApiKey.value = "";
  els.llmClearKey.checked = false;
  renderSourceConfig(config);
  setConfigStatus(
    `${providerLabel(els.llmProvider.value)} · ${llm.hasApiKey ? "接口密钥已配置" : "接口密钥未配置"}`,
  );
  updateSearchSettingsSummary();
  updateDashboard();
}

function renderSourceConfig(config) {
  const sources = config.sources || {};
  els.semanticScholarApiKey.value = "";
  els.googleScholarApiKey.value = "";
  els.webOfScienceApiKey.value = "";
  renderSourceBadges();
  setSourceConfigStatus(sourceConfigText());
}

async function saveLlmConfig() {
  setWorkflowStatus("保存中", "正在保存大模型配置。");
  setBusy(true, "正在保存大模型配置。");
  setConfigStatus("正在保存配置。");
  try {
    const data = await postJson("/api/config/llm", {
      enabled: els.llmEnabled.checked,
      provider: els.llmProvider.value,
      model: els.llmModel.value.trim(),
      endpoint: els.llmEndpoint.value.trim(),
      apiKey: els.llmApiKey.value.trim(),
      clearApiKey: els.llmClearKey.checked,
      requestTimeoutSeconds: Number(els.llmTimeout.value || 45),
    });
    state.config = data;
    renderConfig(data);
    setStatus("大模型配置已保存。");
    setWorkflowStatus("已配置", "大模型规划器配置已更新。");
  } catch (error) {
    setConfigStatus(`保存失败：${error.message}`);
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveSourceConfig() {
  setWorkflowStatus("保存中", "正在保存数据源配置。");
  setBusy(true, "正在保存数据源配置。");
  setSourceConfigStatus("正在保存配置。");
  try {
    const data = await postJson("/api/config/sources", {
      fromYear: els.fromYear.value ? Number(els.fromYear.value) : null,
      preferRecent: els.preferRecent.checked,
      semanticScholarApiKey: els.semanticScholarApiKey.value.trim(),
      googleScholarApiKey: els.googleScholarApiKey.value.trim(),
      webOfScienceApiKey: els.webOfScienceApiKey.value.trim(),
    });
    state.config = data;
    renderConfig(data);
    setStatus("常用接口配置已保存。");
    setWorkflowStatus("已配置", "数据源 API Key 已更新。");
  } catch (error) {
    setSourceConfigStatus(`保存失败：${error.message}`);
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

function applyProviderDefaults() {
  const provider = els.llmProvider.value;
  if (!els.llmModel.value || isKnownDefaultModel(els.llmModel.value)) {
    els.llmModel.value = defaultModel(provider);
  }
  if (!els.llmEndpoint.value || isKnownDefaultEndpoint(els.llmEndpoint.value)) {
    els.llmEndpoint.value = defaultEndpoint(provider);
  }
}

function isKnownDefaultModel(value) {
  return ["deepseek-chat", "gpt-4.1-mini"].includes(value);
}

function isKnownDefaultEndpoint(value) {
  return [
    "https://api.deepseek.com/v1",
    "https://api.openai.com/v1/responses",
  ].includes(value);
}

function defaultModel(provider) {
  if (provider === "openai") return "gpt-4.1-mini";
  return "deepseek-chat";
}

function defaultEndpoint(provider) {
  if (provider === "openai") return "https://api.openai.com/v1/responses";
  return "https://api.deepseek.com/v1";
}

function providerLabel(provider) {
  return provider === "openai" ? "OpenAI" : "DeepSeek";
}

function setConfigStatus(message) {
  els.llmConfigStatus.textContent = message;
}

function setSourceConfigStatus(message) {
  els.sourceConfigStatus.textContent = message;
}

function sourceConfigText() {
  const sources = state.config?.sources || {};
  return [
    semanticConfigText(sources.semantic_scholar),
    sourceReadyText("google_scholar", "Google Scholar", sources),
    sourceReadyText("web_of_science", "Web of Science", sources),
  ].join(" · ");
}

function semanticConfigText(status) {
  if (!status) return "Semantic Scholar 未配置";
  const base = status.configured
    ? "Semantic Scholar 已配置"
    : "Semantic Scholar 未配置";
  const remaining = status.remainingThisMonth ?? "?";
  const total = status.monthlySearchBudget ?? "?";
  const cacheDays = status.cacheTtlDays ?? 30;
  const mode =
    status.budgetStatus === "cache_only"
      ? "缓存模式"
      : status.budgetStatus === "warning"
        ? "预警"
        : "正常";
  return `${base} (${remaining}/${total}, ${mode}, 缓存${cacheDays}天)`;
}

function sourceReadyText(key, label, sources) {
  const status = sources[key];
  if (!status?.requiresKey) return `${label} 可用`;
  return `${label} ${status.configured ? "已配置" : "未配置"}`;
}

async function postJson(url, payload) {
  if (!payload.need && ["/api/plan", "/api/search"].includes(url)) {
    throw new Error("请先填写研究需求。");
  }
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败。");
  }
  return data;
}

function renderPlan(plan) {
  if (!plan) return;
  renderKeywordOutput(plan);
  renderPlanDetails(plan);
  updatePlannerMode(plan);
}

function renderKeywordOutput(plan) {
  els.keywordOutput.innerHTML = "";
  const sections = [
    plannerGroup(plan),
    keywordGroup("中文关键词", plan.zh_keywords || []),
    keywordGroup("英文关键词", plan.en_keywords || []),
    queryGroup(plan.queries || {}),
  ];
  for (const section of sections) {
    if (section) els.keywordOutput.append(section);
  }
}

function plannerGroup(plan) {
  const box = document.createElement("section");
  box.className = "keyword-group";
  box.innerHTML = `<h4>规划方式</h4><p>${escapeHtml(plan.planner === "llm" ? "大模型结构化拆解" : "规则拆解")}</p>`;
  return box;
}

function keywordGroup(title, keywords) {
  const box = document.createElement("section");
  box.className = "keyword-group";
  box.innerHTML = `<h4>${escapeHtml(title)}</h4>`;
  const chips = document.createElement("div");
  chips.className = "chips";
  if (!keywords.length) {
    const empty = document.createElement("p");
    empty.className = "empty-copy";
    empty.textContent = "暂无关键词。";
    box.append(empty);
    return box;
  }
  for (const keyword of keywords) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = keyword;
    chips.append(chip);
  }
  box.append(chips);
  return box;
}

function queryGroup(queries) {
  const box = document.createElement("section");
  box.className = "keyword-group";
  box.innerHTML = "<h4>分库检索式</h4>";
  const list = document.createElement("div");
  list.className = "query-list";
  const entries = Object.entries(queries);
  if (!entries.length) {
    const item = document.createElement("div");
    item.className = "query-item";
    item.innerHTML = "<strong>暂无</strong><code>当前还没有生成检索式。</code>";
    list.append(item);
  } else {
    for (const [source, query] of entries) {
      const item = document.createElement("div");
      item.className = "query-item";
      item.innerHTML = `<strong>${escapeHtml(sourceLabel(source))}</strong><code>${escapeHtml(query)}</code>`;
      list.append(item);
    }
  }
  box.append(list);
  return box;
}

function renderPlanDetails(plan) {
  els.planDetailOutput.innerHTML = "";
  const fragments = [
    detailList("研究问题", plan.research_questions || []),
    conceptList(plan.core_concepts || []),
    detailList("纳入标准", plan.inclusion_criteria || []),
    detailList("排除标准", plan.exclusion_criteria || []),
    detailList("检索策略说明", plan.search_strategy || []),
  ];
  for (const fragment of fragments) {
    if (fragment) els.planDetailOutput.append(fragment);
  }
}

function detailList(title, items) {
  if (!items.length) return null;
  const box = document.createElement("section");
  box.className = "detail-box";
  box.innerHTML = `<h4>${escapeHtml(title)}</h4>`;
  const list = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    list.append(li);
  }
  box.append(list);
  return box;
}

function conceptList(concepts) {
  if (!concepts.length) return null;
  const box = document.createElement("section");
  box.className = "detail-box";
  box.innerHTML = "<h4>核心概念</h4>";
  const list = document.createElement("ul");
  for (const concept of concepts) {
    const parts = [
      concept.label_zh || "",
      concept.label_en || "",
      (concept.synonyms_zh || []).join("，"),
      (concept.synonyms_en || []).join(", "),
    ].filter(Boolean);
    const li = document.createElement("li");
    li.textContent = parts.join(" / ");
    list.append(li);
  }
  box.append(list);
  return box;
}

// Removed legacy execution steps and insight functions to reduce code density and complexity as they are not needed for the new multi-page structure.

function primaryConceptLabel(concept) {
  return concept.label_zh || concept.label_en || "核心概念";
}

function updatePlannerMode(plan) {
  if (!els.plannerMode) return;
  if (!plan) {
    els.plannerMode.textContent = "等待生成方案";
    return;
  }
  els.plannerMode.textContent =
    plan.planner === "llm" ? "大模型规划器已启用" : "规则规划器已启用";
}

function renderErrors(errors) {
  clearErrors();
  const entries = Object.entries(errors);
  if (!entries.length) return;
  els.errorOutput.hidden = false;
  els.errorOutput.innerHTML = entries
    .map(([source, error]) => `<p><strong>${escapeHtml(sourceLabel(source))}</strong>: ${escapeHtml(error)}</p>`)
    .join("");
}

function renderSourceSummary(errors = {}, sourceMeta = {}) {
  renderSourceBadges(errors, sourceMeta);
}

function renderSourceBadges(errors = {}, sourceMeta = {}) {
  const sources = state.config?.sources || {};
  const selected = new Set(selectedSources());
  const counts = countSources();
  const keys = [
    "openalex",
    "crossref",
    "semantic_scholar",
    "google_scholar",
    "web_of_science",
  ];
  els.sourceStatus.innerHTML = "";
  for (const key of keys) {
    const meta = sources[key] || {};
    const liveMeta = sourceMeta[key] || {};
    const badge = document.createElement("span");
    const configured = meta.configured !== false;
    const hasError = Boolean(errors[key]);
    const budgetStatus = liveMeta.budgetStatus || meta.budgetStatus || "ok";
    const budgetClass =
      key === "semantic_scholar" && budgetStatus === "cache_only"
        ? "cache-only"
        : key === "semantic_scholar" && budgetStatus === "warning"
          ? "warning"
          : "";
    badge.className = `source-badge ${selected.has(key) ? "selected" : ""} ${configured ? "ready" : "needs-key"} ${hasError ? "source-error" : ""} ${budgetClass}`;
    const label = meta.label || sourceLabel(key);
    const count = counts[key] || 0;
    let suffix = count ? `${count} 条` : selected.has(key) ? "待检索" : "未选";
    if (hasError) suffix = "出错";
    if (meta.requiresKey && !meta.configured) suffix = "需密钥";
    if (key === "semantic_scholar" && liveMeta.usedCache) suffix = "缓存命中";
    if (key === "semantic_scholar" && budgetStatus === "warning") suffix = "预警";
    if (key === "semantic_scholar" && budgetStatus === "cache_only") suffix = "缓存模式";
    badge.textContent = `${label} · ${suffix}`;
    els.sourceStatus.append(badge);
  }
  updateDashboard();
}

function countSources() {
  const counts = {};
  for (const paper of state.papers) {
    for (const source of paper.sources || [paper.source]) {
      if (!source) continue;
      counts[source] = (counts[source] || 0) + 1;
    }
  }
  return counts;
}

function clearErrors() {
  els.errorOutput.hidden = true;
  els.errorOutput.innerHTML = "";
}

function renderPapers(papers) {
  els.papers.innerHTML = "";
  els.papersEmpty.hidden = papers.length !== 0;
  if (!papers.length) {
    updateSelectionUi();
    return;
  }

  papers.forEach((paper, index) => {
    const key = paperKey(paper);
    const node = els.paperTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.paperKey = key;

    const checkbox = node.querySelector(".paper-checkbox");
    checkbox.checked = state.selectedKeys.has(key);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedKeys.add(key);
      } else {
        state.selectedKeys.delete(key);
      }
      updateSelectionUi();
    });

    node.querySelector(".paper-rank-badge").textContent = index === 0 ? "最佳" : "候选";
    node.querySelector(".paper-source-label").textContent = paperDomainLabel(paper);
    node.querySelector(".paper-title").textContent = paper.title || "未命名文献";
    node.querySelector(".paper-authors").textContent =
      (paper.authors || []).slice(0, 8).join(", ") || "作者信息待补";
    node.querySelector(".paper-summary").textContent = trimText(
      paper.abstract || "暂无摘要。",
      420,
    );

    const metrics = node.querySelector(".paper-metrics-bar");
    addPaperMetric(metrics, "年份", paper.year || "暂无");
    addPaperMetric(metrics, "引用", paper.cited_by_count ?? "暂无");
    addPaperMetric(metrics, "OA", paper.oa_status || "未知");
    addPaperMetric(
      metrics,
      "得分",
      formatScore(paper.relevance_score ?? paper.score ?? null),
    );

    const sources = (paper.sources || [paper.source]).filter(Boolean).map(sourceLabel);
    node.querySelector(".paper-meta-info").textContent = [
      paper.venue || "期刊/会议待补",
      paper.year || "年份",
      sources.join(" · "),
    ]
      .filter(Boolean)
      .join(" · ");

    const links = node.querySelector(".paper-link-group");
    addLink(links, "详情", paper.url);
    addLink(links, "PDF", paper.pdf_url);
    if (paper.doi) addLink(links, "DOI", `https://doi.org/${paper.doi}`);

    const favoriteButton = node.querySelector(".paper-favorite-btn");
    const saved = isSavedPaper(paper);
    favoriteButton.textContent = saved ? "已收藏" : "收藏";
    favoriteButton.classList.toggle("active", saved);
    favoriteButton.addEventListener("click", () => toggleSavePaper(paper));

    els.papers.append(node);
  });

  updateSelectionUi();
}

function paperDomainLabel(paper) {
  const venue = trimText((paper.venue || "Literature Pool").toUpperCase(), 22);
  const year = paper.year || "年份未注明";
  return `${venue} ${year}`;
}

function addPaperMetric(parent, label, value) {
  const chip = document.createElement("span");
  chip.className = "paper-metric";
  chip.textContent = `${label} ${value}`;
  parent.append(chip);
}

function applyResultControls() {
  const text = els.filterText.value.trim().toLowerCase();
  const pdfOnly = Boolean(els.pdfOnly?.checked);
  const sortBy = els.sortBy.value;
  let papers = [...state.papers];
  if (text) {
    papers = papers.filter((paper) =>
      [
        paper.title || "",
        (paper.authors || []).join(" "),
        paper.abstract || "",
        paper.venue || "",
        paper.doi || "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(text),
    );
  }
  if (pdfOnly) {
    papers = papers.filter((paper) => Boolean(paper.pdf_url));
  }
  papers.sort((left, right) => sortPapers(left, right, sortBy));
  state.visiblePapers = papers;
  renderPapers(papers);
  updateDashboard();
}

function sortPapers(left, right, sortBy) {
  if (sortBy === "recent") {
    return (
      (right.year || 0) - (left.year || 0) ||
      (right.relevance_score ?? right.score ?? 0) -
        (left.relevance_score ?? left.score ?? 0)
    );
  }
  if (sortBy === "year") {
    return (right.year || 0) - (left.year || 0);
  }
  if (sortBy === "citations") {
    return (right.cited_by_count || 0) - (left.cited_by_count || 0);
  }
  return (right.relevance_score ?? right.score ?? 0) - (left.relevance_score ?? left.score ?? 0);
}

function selectVisiblePapers() {
  for (const paper of state.visiblePapers) {
    state.selectedKeys.add(paperKey(paper));
  }
  renderPapers(state.visiblePapers);
}

function clearSelection() {
  state.selectedKeys.clear();
  renderPapers(state.visiblePapers);
}

function updateSelectionUi() {
  const selected = state.selectedKeys.size;
  els.selectionCount.textContent = `已选 ${selected} 篇`;
  els.dryRunButton.disabled = selected === 0;
  els.selectVisible.disabled = state.visiblePapers.length === 0;
  els.clearSelection.disabled = selected === 0;
  els.saveSelected.disabled = selected === 0;
  updateDashboard();
}

function updateDashboard() {
  const sourceCount = selectedSources().length;
  const visibleCount = state.visiblePapers.length;
  const totalCount = state.papers.length;
  const selectedSourceLabels = selectedSources().map(sourceLabel);

  if (els.selectedSourceCount) {
    els.selectedSourceCount.textContent = `已选 ${sourceCount} 个`;
  }
  if (els.sourceConfigSummary) {
    els.sourceConfigSummary.textContent = selectedSourceLabels.length
      ? selectedSourceLabels.join(" / ")
      : "未选择数据源";
  }
  if (els.plannerMode) {
    els.plannerMode.textContent = state.workflowLabel || "等待生成方案";
  }
  if (els.modelConfigSummary) {
    const model = els.llmModel.value.trim() || defaultModel(els.llmProvider.value);
    els.modelConfigSummary.textContent = els.llmEnabled.checked
      ? `${providerLabel(els.llmProvider.value)} / ${model}`
      : "规则规划器 / 手动模式";
  }

  if (els.resultsCount) {
    els.resultsCount.textContent = totalCount
      ? visibleCount !== totalCount
        ? `${visibleCount} / ${totalCount} 条记录`
        : `${totalCount} 条记录`
      : "0 条记录";
  }
}

function setWorkflowStatus(label, detail) {
  state.workflowLabel = label;
  state.workflowDetail = detail;
  updateDashboard();
}

function loadWorkspaceMemory() {
  try {
    const savedRaw = localStorage.getItem(SAVED_PAPERS_STORAGE_KEY);
    const historyRaw = localStorage.getItem(HISTORY_STORAGE_KEY);
    const workspaceRaw = localStorage.getItem(WORKSPACE_SNAPSHOT_STORAGE_KEY);
    state.savedPapers = savedRaw ? JSON.parse(savedRaw) : [];
    state.history = historyRaw ? JSON.parse(historyRaw) : [];
    state.workspaceSnapshot = workspaceRaw ? JSON.parse(workspaceRaw) : null;
  } catch {
    state.savedPapers = [];
    state.history = [];
    state.workspaceSnapshot = null;
  }
}

function persistWorkspaceMemory() {
  try {
    localStorage.setItem(SAVED_PAPERS_STORAGE_KEY, JSON.stringify(state.savedPapers));
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(state.history));
  } catch {}
  persistWorkspaceSnapshot();
}

function persistWorkspaceSnapshot() {
  if (!state.workspaceRestored) return;
  const snapshot = {
    need: els.need.value.trim(),
    zhKeywords: els.zhKeywords.value,
    enKeywords: els.enKeywords.value,
    limit: els.limit.value,
    fromYear: els.fromYear.value,
    preferRecent: els.preferRecent.checked,
    useLlm: els.useLlm.checked,
    applyImport: els.applyImport.checked,
    sources: selectedSources(),
    plan: state.plan,
    papers: state.papers,
    sourceMeta: state.sourceMeta,
    reportPath: state.reportPath,
    reportUrl: els.reportLink?.hidden ? "" : els.reportLink?.getAttribute("href") || "",
    outputView: state.outputView,
    status: els.status.textContent || "",
  };
  state.workspaceSnapshot = snapshot;
  try {
    localStorage.setItem(WORKSPACE_SNAPSHOT_STORAGE_KEY, JSON.stringify(snapshot));
  } catch {}
}

function restoreWorkspaceSnapshot() {
  if (state.workspaceRestored) return;
  state.workspaceRestored = true;
  const snapshot = state.workspaceSnapshot;
  if (!snapshot || typeof snapshot !== "object") return;

  if (typeof snapshot.need === "string") els.need.value = snapshot.need;
  if (typeof snapshot.zhKeywords === "string") els.zhKeywords.value = snapshot.zhKeywords;
  if (typeof snapshot.enKeywords === "string") els.enKeywords.value = snapshot.enKeywords;
  if (typeof snapshot.limit !== "undefined" && snapshot.limit !== null) {
    els.limit.value = snapshot.limit;
  }
  if (typeof snapshot.fromYear !== "undefined" && snapshot.fromYear !== null) {
    els.fromYear.value = snapshot.fromYear;
  }
  if (typeof snapshot.preferRecent !== "undefined") {
    els.preferRecent.checked = Boolean(snapshot.preferRecent);
  }
  if (typeof snapshot.useLlm !== "undefined") {
    els.useLlm.checked = Boolean(snapshot.useLlm);
  }
  if (typeof snapshot.applyImport !== "undefined") {
    els.applyImport.checked = Boolean(snapshot.applyImport);
  }
  if (Array.isArray(snapshot.sources)) {
    const selected = new Set(snapshot.sources);
    for (const input of sourceInputs) {
      input.checked = selected.has(input.value);
    }
  }

  state.plan = snapshot.plan || null;
  state.papers = Array.isArray(snapshot.papers) ? snapshot.papers : [];
  state.sourceMeta = snapshot.sourceMeta || {};
  state.reportPath = snapshot.reportPath || "";
  state.selectedKeys = new Set();

  renderSourceBadges();
  updateSearchSettingsSummary();
  clearErrors();
  els.keywordOutput.innerHTML = "";
  els.planDetailOutput.innerHTML = "";
  if (state.plan) {
    renderPlan(state.plan);
  }
  updateReportLink(snapshot.reportUrl || "");
  applyResultControls();
  if (snapshot.status) {
    setStatus(snapshot.status);
  }
  setFlowStep(snapshot.outputView || (state.papers.length ? "search" : state.plan ? "plan" : "ask"));
}

function isSavedPaper(paper) {
  const key = paperKey(paper);
  return state.savedPapers.some((item) => paperKey(item) === key);
}

function toggleSavePaper(paper) {
  const key = paperKey(paper);
  const index = state.savedPapers.findIndex((item) => paperKey(item) === key);
  if (index >= 0) {
    state.savedPapers.splice(index, 1);
    setStatus("已从收藏中移除文献。");
  } else {
    state.savedPapers.unshift(paper);
    setStatus("已加入文献收藏。");
    addHistoryEntry("收藏文献", {
      title: paper.title || "未命名文献",
      year: paper.year || "未知",
    });
  }
  persistWorkspaceMemory();
  renderPapers(state.visiblePapers);
  renderSavedPapers();
}

function saveSelectedPapers() {
  const selectedPapers = state.papers.filter((paper) =>
    state.selectedKeys.has(paperKey(paper)),
  );
  if (!selectedPapers.length) {
    setStatus("没有选中文献，无法收藏。");
    return;
  }
  let added = 0;
  for (const paper of selectedPapers) {
    if (isSavedPaper(paper)) continue;
    state.savedPapers.unshift(paper);
    added += 1;
  }
  persistWorkspaceMemory();
  renderPapers(state.visiblePapers);
  renderSavedPapers();
  setStatus(`已收藏 ${added} 篇文献。`);
  addHistoryEntry("批量收藏文献", {
    selected: selectedPapers.length,
    added,
  });
}

function clearSavedPapers() {
  if (!state.savedPapers.length) {
    setStatus("收藏池当前为空。");
    return;
  }
  const removed = state.savedPapers.length;
  state.savedPapers = [];
  persistWorkspaceMemory();
  renderPapers(state.visiblePapers);
  renderSavedPapers();
  addHistoryEntry("清空收藏池", { removed });
  setStatus("已清空收藏文献。");
}

function renderSavedPapers() {
  const query = els.savedFilterText.value.trim().toLowerCase();
  const authorQuery = els.savedAuthorFilter.value.trim().toLowerCase();
  const yearFilter = els.savedYearFilter.value.trim();
  const sourceFilter = els.savedSourceFilter.value.trim().toLowerCase();
  const tagFilter = els.savedTagFilter.value.trim().toLowerCase();
  const importedOnly = els.savedImportedFilter.checked;
  let papers = [...state.savedPapers];
  if (query) {
    papers = papers.filter((paper) =>
      [paper.title || "", paper.abstract || "", paper.venue || "", paper.doi || "", paper.url || ""]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }
  if (authorQuery) {
    papers = papers.filter((paper) =>
      (paper.authors || []).join(" ").toLowerCase().includes(authorQuery),
    );
  }
  if (yearFilter) {
    papers = papers.filter((paper) => String(paper.year || "").includes(yearFilter));
  }
  if (sourceFilter) {
    papers = papers.filter((paper) => {
      const sources = (paper.sources || [paper.source]).filter(Boolean).map(sourceLabel).join(" ");
      return sources.toLowerCase().includes(sourceFilter);
    });
  }
  if (tagFilter) {
    papers = papers.filter((paper) =>
      paperTags(paper).join(" ").toLowerCase().includes(tagFilter),
    );
  }
  if (importedOnly) {
    papers = papers.filter((paper) => paperImported(paper));
  }

  els.savedPapers.innerHTML = "";
  els.savedEmpty.hidden = papers.length !== 0;
  els.savedCount.textContent = state.savedPapers.length;
  els.clearSaved.disabled = state.savedPapers.length === 0;
  const importedCount = state.savedPapers.filter((paper) => paperImported(paper)).length;
  els.savedImportedCount.textContent = importedCount;
  els.savedPendingCount.textContent = Math.max(state.savedPapers.length - importedCount, 0);

  for (const paper of papers) {
    els.savedPapers.append(createSavedPaperCard(paper));
  }
}

function paperImported(paper) {
  return Boolean(paper.imported || paper.zoteroImported || paper.zoteroKey);
}

function paperTags(paper) {
  const tags = [];
  if (Array.isArray(paper.userTags)) tags.push(...paper.userTags);
  if (Array.isArray(paper.tags)) {
    for (const tag of paper.tags) {
      if (!tag) continue;
      if (String(tag).startsWith("source:")) continue;
      tags.push(tag);
    }
  }
  return [...new Set(tags.map((tag) => String(tag).trim()).filter(Boolean))];
}

function createSavedPaperCard(paper) {
  const article = document.createElement("article");
  article.className = "saved-paper-card";
  const imported = paperImported(paper);
  const tags = paperTags(paper);
  const sources = (paper.sources || [paper.source]).filter(Boolean).map(sourceLabel);
  const linkHref = paper.url || (paper.doi ? `https://doi.org/${paper.doi}` : "");

  article.innerHTML = `
    <div class="saved-paper-top">
      <div class="saved-paper-badges">
        <span class="saved-paper-badge">${escapeHtml(sources.join(" / ") || "来源待补")}</span>
        <span class="saved-paper-badge ${imported ? "imported" : "pending"}">${imported ? "已同步 Zotero" : "未同步 Zotero"}</span>
      </div>
      <span class="saved-paper-year">${escapeHtml(String(paper.year || "年份未知"))}</span>
    </div>
    <h3 class="saved-paper-title">${escapeHtml(paper.title || "未命名文献")}</h3>
    <p class="saved-paper-authors">${escapeHtml((paper.authors || []).slice(0, 10).join(", ") || "作者信息待补")}</p>
    <p class="saved-paper-abstract">${escapeHtml(trimText(paper.abstract || "暂无摘要。", 360))}</p>
    <div class="saved-paper-tags">
      ${
        tags.length
          ? tags
              .map((tag) => `<span class="saved-paper-tag">${escapeHtml(tag)}</span>`)
              .join("")
          : '<span class="saved-paper-tag muted">暂无标签</span>'
      }
    </div>
    <div class="saved-paper-meta">
      <span>${escapeHtml(paper.venue || "期刊/会议待补")}</span>
      <span>${escapeHtml(`引用 ${paper.cited_by_count ?? "暂无"}`)}</span>
      <span>${escapeHtml(`DOI ${paper.doi || "暂无"}`)}</span>
    </div>
    <div class="saved-paper-links"></div>
    <div class="saved-paper-actions">
      ${
        linkHref
          ? `<a class="saved-paper-action-link" href="${escapeHtml(linkHref)}" target="_blank" rel="noreferrer">查看详情</a>`
          : ""
      }
      <button type="button" data-saved-action="tag">${tags.length ? "编辑标签" : "添加标签"}</button>
      <button type="button" data-saved-action="import">${imported ? "重新同步 Zotero" : "导入 Zotero"}</button>
      <button type="button" data-saved-action="remove" class="danger">取消收藏</button>
    </div>
  `;

  const links = article.querySelector(".saved-paper-links");
  addLink(links, "原文链接", paper.url);
  addLink(links, "PDF", paper.pdf_url);
  if (paper.doi) addLink(links, "DOI", `https://doi.org/${paper.doi}`);
  if (!links.childElementCount) links.remove();

  article.querySelector('[data-saved-action="tag"]').addEventListener("click", () => {
    editSavedPaperTags(paper);
  });
  article.querySelector('[data-saved-action="import"]').addEventListener("click", () => {
    importSavedPaper(paper);
  });
  article.querySelector('[data-saved-action="remove"]').addEventListener("click", () => {
    toggleSavePaper(paper);
  });

  return article;
}

function editSavedPaperTags(paper) {
  const current = Array.isArray(paper.userTags) ? paper.userTags.join(", ") : "";
  const value = window.prompt("请输入标签，使用逗号分隔。", current);
  if (value === null) return;
  paper.userTags = splitKeywords(value);
  persistWorkspaceMemory();
  renderSavedPapers();
  renderPapers(state.visiblePapers);
  setStatus("已更新文献标签。");
}

async function importSavedPaper(paper) {
  setBusy(true, "正在写入 Zotero。");
  try {
    const data = await postJson("/api/import-zotero", {
      papers: [paper],
      limit: 1,
      apply: true,
    });
    const result = data.result || {};
    paper.imported = true;
    paper.zoteroImported = true;
    persistWorkspaceMemory();
    renderSavedPapers();
    renderPapers(state.visiblePapers);
    addHistoryEntry("收藏页导入 Zotero", {
      title: paper.title || "未命名文献",
      created: result.created || 0,
      skipped: result.skipped || 0,
      errors: (result.errors || []).length,
    });
    if (result.errors && result.errors.length) {
      showError(result.errors.join("\n"));
    } else {
      setStatus(`已同步到 Zotero：创建 ${result.created || 0}，跳过 ${result.skipped || 0}。`);
    }
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

function addHistoryEntry(action, payload = {}) {
  const entry = {
    id: `${Date.now()}-${Math.floor(Math.random() * 10000)}`,
    action,
    payload,
    time: new Date().toISOString(),
  };
  state.history.unshift(entry);
  state.history = state.history.slice(0, 80);
  persistWorkspaceMemory();
  renderHistory();
}

function renderHistory() {
  els.historyList.innerHTML = "";
  const query = els.historyFilterText.value.trim().toLowerCase();
  const entries = query
    ? state.archiveItems.filter((item) => {
        const blob = [
          item.title,
          item.need,
          formatHistoryValue(item.zhKeywords),
          formatHistoryValue(item.enKeywords),
          formatHistoryValue(item.sources),
        ]
          .join(" ")
          .toLowerCase();
        return blob.includes(query);
      })
    : state.archiveItems;

  els.historyEmpty.hidden = entries.length !== 0;
  els.historyCount.textContent = `共 ${entries.length} 个任务`;

  for (const item of entries) {
    const node = document.createElement("article");
    node.className = `archive-task-card ${item.id === state.archiveSelectedId ? "active" : ""}`;
    const keywordSummary = [
      ...(item.zhKeywords || []).slice(0, 3),
      ...(item.enKeywords || []).slice(0, 2),
    ].join(" / ") || "暂无关键词";
    node.innerHTML = `
      <div class="archive-task-top">
        <div>
          <h4>${escapeHtml(item.title || item.need || "未命名任务")}</h4>
          <p class="history-item-meta">${escapeHtml(trimText(item.need || "暂无研究问题。", 96))}</p>
        </div>
        <span class="archive-status-badge ${archiveStatusClass(item.status)}">${escapeHtml(item.status || "已归档")}</span>
      </div>
      <div class="archive-task-meta">
        <span>${escapeHtml(formatHistoryTime(item.createdAt))}</span>
        <span>${escapeHtml(formatSources(item.sources))}</span>
        <span>${escapeHtml(`${item.paperCount || 0} 篇结果`)}</span>
      </div>
      <p class="archive-task-keywords">${escapeHtml(keywordSummary)}</p>
    `;
    node.tabIndex = 0;
    node.addEventListener("click", () => loadArchiveDetail(item.id));
    node.addEventListener("keydown", (event) => {
      if (!["Enter", " "].includes(event.key)) return;
      event.preventDefault();
      loadArchiveDetail(item.id);
    });
    els.historyList.append(node);
  }

  renderArchiveDetail();
}

async function loadArchive(showToast = false) {
  try {
    const response = await fetch("/api/archive");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "读取历史归档失败。");
    }
    state.archiveItems = Array.isArray(data.items) ? data.items : [];
    if (!state.archiveItems.some((item) => item.id === state.archiveSelectedId)) {
      state.archiveSelectedId = state.archiveItems[0]?.id || "";
      state.archiveDetail = null;
    }
    renderHistory();
    if (state.archiveSelectedId) {
      await loadArchiveDetail(state.archiveSelectedId, { silent: true });
    } else {
      renderArchiveDetail();
    }
    if (showToast) setStatus("历史归档已刷新。");
  } catch (error) {
    state.archiveItems = [];
    state.archiveSelectedId = "";
    state.archiveDetail = null;
    renderHistory();
    renderArchiveDetail();
    if (showToast || state.activePage === "archive") {
      setStatus(`读取历史归档失败：${error.message}`);
    }
  }
}

async function loadArchiveDetail(runId, { silent = false } = {}) {
  if (!runId) {
    state.archiveSelectedId = "";
    state.archiveDetail = null;
    renderHistory();
    renderArchiveDetail();
    return;
  }
  state.archiveSelectedId = runId;
  renderHistory();
  try {
    const response = await fetch(`/api/archive/${encodeURIComponent(runId)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "读取归档详情失败。");
    }
    state.archiveDetail = data.item || null;
    renderArchiveDetail();
  } catch (error) {
    state.archiveDetail = null;
    renderArchiveDetail();
    if (!silent) {
      setStatus(`读取归档详情失败：${error.message}`);
    }
  }
}

function renderArchiveDetail() {
  if (!state.archiveDetail) {
    els.archiveDetail.innerHTML = `
      <div class="empty-placeholder compact-empty">
        <h3>选择一个历史任务</h3>
        <p>右侧会展示当时的需求配置、检索条件、方案和结果摘要。</p>
      </div>
    `;
    return;
  }
  const entry = state.archiveDetail;
  const plan = entry.plan || {};
  const papers = Array.isArray(entry.papers) ? entry.papers : [];
  const sourceMeta = entry.sourceMeta || {};
  const sourceMetaHtml = Object.entries(sourceMeta)
    .map(([key, meta]) => {
      const fragments = [
        sourceLabel(key),
        meta.usedCache ? "缓存命中" : "",
        meta.budgetStatus ? `状态 ${meta.budgetStatus}` : "",
        meta.remainingThisMonth ?? "" ? `剩余 ${meta.remainingThisMonth}` : "",
      ].filter(Boolean);
      return `<li>${escapeHtml(fragments.join(" · "))}</li>`;
    })
    .join("");
  const previewHtml = papers.length
    ? papers
        .slice(0, 5)
        .map(
          (paper) => `
            <article class="archive-paper-preview">
              <h5>${escapeHtml(paper.title || "未命名文献")}</h5>
              <p>${escapeHtml((paper.authors || []).slice(0, 6).join(", ") || "作者信息待补")}</p>
              <span>${escapeHtml(`${paper.year || "年份未知"} · ${(paper.venue || "来源待补")}`)}</span>
            </article>
          `,
        )
        .join("")
    : '<p class="history-item-meta">暂无结果摘要。</p>';

  els.archiveDetail.innerHTML = `
    <div class="archive-detail-head">
      <div>
        <p class="eyebrow">任务详情</p>
        <h3>${escapeHtml(entry.title || entry.need || "未命名任务")}</h3>
        <p class="archive-detail-need">${escapeHtml(entry.need || "暂无研究问题。")}</p>
      </div>
      <span class="archive-status-badge ${archiveStatusClass(entry.status)}">${escapeHtml(entry.status || "已归档")}</span>
    </div>
    <div class="archive-detail-meta">
      <span>${escapeHtml(formatHistoryTime(entry.createdAt))}</span>
      <span>${escapeHtml(formatSources(entry.sources))}</span>
      <span>${escapeHtml(`${papers.length} 篇候选文献`)}</span>
      <span>${escapeHtml(`当前收藏命中 ${papers.filter((paper) => isSavedPaper(paper)).length} 篇`)}</span>
    </div>
    <div class="archive-actions">
      <button type="button" data-history-action="open">重新打开</button>
      <button type="button" data-history-action="replay">复用配置</button>
      <button type="button" data-history-action="search">重新检索</button>
      <button type="button" data-history-action="delete" class="danger">删除归档</button>
      ${
        entry.reportUrl
          ? `<a class="saved-paper-action-link" href="${escapeHtml(entry.reportUrl)}" target="_blank" rel="noreferrer">查看报告</a>`
          : ""
      }
    </div>
    <div class="archive-detail-grid">
      <section class="archive-detail-section">
        <h4>需求配置</h4>
        <p>${escapeHtml(entry.need || "暂无研究问题。")}</p>
        <div class="archive-chip-row">
          ${keywordChipsHtml(plan.zh_keywords || entry.zhKeywords || [], "中文")}
          ${keywordChipsHtml(plan.en_keywords || entry.enKeywords || [], "英文")}
        </div>
      </section>
      <section class="archive-detail-section">
        <h4>检索条件</h4>
        <ul class="archive-detail-list">
          <li>起始年份：${escapeHtml(formatArchiveField(entry.fromYear))}</li>
          <li>每源条数：${escapeHtml(formatArchiveField(entry.limit))}</li>
          <li>优先最新/高被引：${escapeHtml(formatArchiveBoolean(entry.preferRecent))}</li>
          <li>AI 优化检索词：${escapeHtml(formatArchiveBoolean(entry.useLlm))}</li>
        </ul>
      </section>
      <section class="archive-detail-section">
        <h4>检索方案</h4>
        <ul class="archive-detail-list">
          ${archiveListItems(plan.search_strategy)}
          ${!Array.isArray(plan.search_strategy) || !plan.search_strategy.length ? "<li>暂无方案说明。</li>" : ""}
        </ul>
      </section>
      <section class="archive-detail-section">
        <h4>来源与模型</h4>
        <ul class="archive-detail-list">
          <li>规划方式：${escapeHtml(plan.planner === "llm" ? "大模型规划器" : "规则规划器")}</li>
          <li>数据源：${escapeHtml(formatSources(entry.sources))}</li>
          ${sourceMetaHtml || "<li>暂无来源元数据。</li>"}
        </ul>
      </section>
      <section class="archive-detail-section full-width">
        <h4>结果摘要</h4>
        <div class="archive-paper-preview-list">${previewHtml}</div>
      </section>
    </div>
  `;

  for (const button of els.archiveDetail.querySelectorAll("[data-history-action]")) {
    button.addEventListener("click", () => handleHistoryAction(entry, button.dataset.historyAction));
  }
}

async function handleHistoryAction(entry, action) {
  if (action === "open") {
    openArchiveTask(entry);
    return;
  }
  if (action === "delete") {
    await deleteArchiveTask(entry);
    return;
  }
  if (action === "replay") {
    applyHistoryPayload(archiveConfigPayload(entry));
    setActivePage("search");
    setStatus("已复用历史配置到检索工作区。");
    return;
  }
  if (action === "search") {
    applyHistoryPayload(archiveConfigPayload(entry));
    setActivePage("search");
    await runSearch();
  }
}

function openArchiveTask(entry) {
  applyHistoryPayload(archiveConfigPayload(entry));
  state.plan = entry.plan || null;
  state.papers = Array.isArray(entry.papers) ? entry.papers : [];
  state.sourceMeta = entry.sourceMeta || {};
  state.reportPath = entry.reportPath || entry.reportUrl || "";
  state.selectedKeys = new Set();
  renderPlan(state.plan);
  renderErrors(entry.errors || {});
  renderSourceSummary(entry.errors || {}, state.sourceMeta);
  updateReportLink(entry.reportUrl || "");
  applyResultControls();
  setFlowStep(state.papers.length ? "search" : state.plan ? "plan" : "ask");
  setWorkflowStatus(entry.status || "已归档", "已从历史归档恢复该任务。");
  persistWorkspaceSnapshot();
  setActivePage("search");
  setStatus("已重新打开历史任务。");
}

async function deleteArchiveTask(entry) {
  try {
    const data = await postJson("/api/archive/delete", { runId: entry.id });
    if (!data.ok) throw new Error("删除失败。");
    if (state.archiveSelectedId === entry.id) {
      state.archiveSelectedId = "";
      state.archiveDetail = null;
    }
    await loadArchive();
    setStatus("已删除该条历史归档。");
  } catch (error) {
    setStatus(`删除归档失败：${error.message}`);
  }
}

function archiveConfigPayload(entry = {}) {
  const plan = entry.plan || {};
  return {
    need: plan.need || entry.need || "",
    zhKeywords: plan.zh_keywords || entry.zhKeywords || [],
    enKeywords: plan.en_keywords || entry.enKeywords || [],
    limit: entry.limit,
    fromYear: entry.fromYear,
    preferRecent: entry.preferRecent,
    useLlm: entry.useLlm,
    sources: entry.sources || Object.keys(plan.queries || {}),
  };
}

function applyHistoryPayload(payload = {}) {
  const zhKeywords = payload.zhKeywords ?? payload.zh_keywords;
  const enKeywords = payload.enKeywords ?? payload.en_keywords;
  if (typeof payload.need === "string") els.need.value = payload.need;
  if (Array.isArray(zhKeywords)) {
    els.zhKeywords.value = zhKeywords.join(", ");
  } else if (typeof zhKeywords === "string") {
    els.zhKeywords.value = zhKeywords;
  }
  if (Array.isArray(enKeywords)) {
    els.enKeywords.value = enKeywords.join(", ");
  } else if (typeof enKeywords === "string") {
    els.enKeywords.value = enKeywords;
  }
  if (typeof payload.limit !== "undefined" && payload.limit !== null) els.limit.value = payload.limit;
  if (typeof payload.fromYear !== "undefined" && payload.fromYear !== null) els.fromYear.value = payload.fromYear;
  if (typeof payload.preferRecent !== "undefined") els.preferRecent.checked = Boolean(payload.preferRecent);
  if (typeof payload.useLlm !== "undefined") els.useLlm.checked = Boolean(payload.useLlm);
  if (payload.sources) {
    const selectedSources = new Set(Array.isArray(payload.sources) ? payload.sources : []);
    for (const input of sourceInputs) {
      input.checked = selectedSources.has(input.value);
    }
    renderSourceBadges();
  }
  updateSearchSettingsSummary();
  updateDashboard();
  persistWorkspaceSnapshot();
}

function formatSources(sources) {
  if (!Array.isArray(sources) || !sources.length) return "暂无来源";
  return sources.map(sourceLabel).join(" / ");
}

function archiveStatusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized.includes("成功") || normalized.includes("完成") || normalized.includes("归档")) {
    return "success";
  }
  if (normalized.includes("失败")) return "failed";
  if (normalized.includes("中断")) return "warning";
  if (normalized.includes("进行")) return "running";
  return "neutral";
}

function keywordChipsHtml(keywords, label) {
  if (!Array.isArray(keywords) || !keywords.length) {
    return `<div class="archive-chip-group"><strong>${escapeHtml(label)}</strong><span class="saved-paper-tag muted">暂无</span></div>`;
  }
  return `
    <div class="archive-chip-group">
      <strong>${escapeHtml(label)}</strong>
      ${keywords
        .slice(0, 6)
        .map((keyword) => `<span class="saved-paper-tag">${escapeHtml(keyword)}</span>`)
        .join("")}
    </div>
  `;
}

function formatArchiveField(value) {
  if (value === null || value === undefined || value === "") return "暂无数据";
  return String(value);
}

function formatArchiveBoolean(value) {
  if (value === null || value === undefined || value === "") return "暂无数据";
  return value ? "是" : "否";
}

function archiveListItems(items) {
  if (!Array.isArray(items) || !items.length) return "";
  return items
    .slice(0, 5)
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

function formatHistoryValue(value) {
  if (Array.isArray(value)) return value.join("、") || "空";
  if (value === null || value === undefined || value === "") return "空";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function historySummary(payload) {
  const keys = Object.keys(payload || {});
  if (!keys.length) return "无附加参数";
  return keys
    .slice(0, 4)
    .map((key) => {
      const value = payload[key];
      if (Array.isArray(value)) return `${key}: ${value.join("、") || "空"}`;
      return `${key}: ${value}`;
    })
    .join("；");
}

function formatHistoryTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function paperKey(paper) {
  if (paper.doi) return `doi:${paper.doi.toLowerCase()}`;
  return `title:${paper.title || ""}:${paper.year || ""}`.toLowerCase();
}

function formatScore(score) {
  if (score === null || score === undefined || Number.isNaN(Number(score))) return "暂无";
  return Number(score).toFixed(2);
}

function semanticStatusNote(meta) {
  if (!meta) return "";
  if (meta.warningMessage) return meta.warningMessage;
  if (meta.usedCache) return "Semantic Scholar 使用了本地缓存结果。";
  return "";
}

function addLink(parent, label, href) {
  if (!href) return;
  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = label;
  parent.append(link);
}

function updateReportLink(href) {
  if (!els.reportLink) return;
  if (!href) {
    els.reportLink.hidden = true;
    els.reportLink.removeAttribute("href");
    return;
  }
  els.reportLink.hidden = false;
  els.reportLink.href = href;
}

function sourceLabel(key) {
  return state.config?.sources?.[key]?.label || {
    openalex: "OpenAlex",
    crossref: "Crossref",
    semantic_scholar: "Semantic Scholar",
    google_scholar: "Google Scholar",
    web_of_science: "Web of Science",
  }[key] || key;
}

function setBusy(isBusy, message = "") {
  els.planButton.disabled = isBusy;
  els.searchButton.disabled = isBusy;
  els.dryRunButton.disabled = isBusy || state.selectedKeys.size === 0;
  els.saveLlmConfig.disabled = isBusy;
  els.saveSourceConfig.disabled = isBusy;
  if (message) setStatus(message);
}

function setStatus(message) {
  els.status.textContent = message;
  if (state.workspaceRestored) {
    persistWorkspaceSnapshot();
  }
}

function showError(message) {
  setStatus("遇到错误。");
  els.errorOutput.hidden = false;
  els.errorOutput.textContent = message;
  setWorkflowStatus("出错", "请求失败，请检查配置或网络状态。");
}

function trimText(value, maxLength) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
