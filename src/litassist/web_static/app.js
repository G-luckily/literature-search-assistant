const PAGE_SIZE = 20;

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
  selectedMockTaskId: "",
  currentPage: 1,
  searchHistory: [],
  /** Full extracted text from the last uploaded file, for multimodal search injection */
  fileContext: "",
  /** Structured search dimensions extracted by LLM PDF analysis */
  searchDimensions: null,
  /** Per-database suggested queries from LLM PDF analysis */
  suggestedQueries: null,
};

const THEME_STORAGE_KEY = "litassist.theme.v1";
const SAVED_PAPERS_STORAGE_KEY = "litassist.savedPapers.v1";
const HISTORY_STORAGE_KEY = "litassist.history.v1";
const SEARCH_HISTORY_KEY = "litassist.searchHistory.v1";
const WORKSPACE_SNAPSHOT_STORAGE_KEY = "litassist.workspaceSnapshot.v1";
const DEFAULT_CANDIDATE_POOL_SIZE = 100;

const els = {
  workspaceOverview: document.querySelector("#workspace-overview"),
  pageViews: [...document.querySelectorAll(".page-view")],
  themeToggle: document.querySelector("#theme-toggle"),
  intentHistoryList: document.querySelector("#intent-history-list"),
  need: document.querySelector("#need"),
  zhKeywords: document.querySelector("#zh-keywords"),
  enKeywords: document.querySelector("#en-keywords"),
  limit: document.querySelector("#limit"),
  fromYear: document.querySelector("#from-year"),
  preferRecent: document.querySelector("#prefer-recent"),
  sortPreference: document.querySelector("#sort-preference"),
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
  zoteroLibraryId: document.querySelector("#zotero-library-id"),
  zoteroApiKey: document.querySelector("#zotero-api-key"),
  zoteroLibraryType: document.querySelector("#zotero-library-type"),
  zoteroCollectionKey: document.querySelector("#zotero-collection-key"),
  saveSourceConfig: document.querySelector("#save-source-config"),
  sourceConfigStatus: document.querySelector("#source-config-status"),
  filterText: document.querySelector("#filter-text"),
  sortBy: document.querySelector("#sort-by"),
  pdfOnly: null,
  exportBibtex: document.querySelector("#export-bibtex"),
  exportCsv: document.querySelector("#export-csv"),
  exportRis: document.querySelector("#export-ris"),
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
  confirmPlanSearch: document.querySelector("#confirm-plan-search"),
  topNavLinks: [...document.querySelectorAll(".topbar-link[data-page]")],
  sidebarNavLinks: [...document.querySelectorAll(".sidebar-link[data-page]")],
  searchProgressPanel: document.querySelector("#search-progress-panel"),
  progressSourceList: document.querySelector("#progress-source-list"),
  progressSummary: document.querySelector("#progress-summary"),
};

const sourceInputs = [...document.querySelectorAll('input[name="source"]')];

els.themeToggle.addEventListener("click", () => toggleTheme());
els.planButton.addEventListener("click", () => runPlan());
els.searchButton.addEventListener("click", () => runSearch());
// Quick search in top bar: fill need and run search, switch to search page
const quickSearchEl = document.querySelector("#quick-search");
if (quickSearchEl) {
  quickSearchEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && quickSearchEl.value.trim()) {
      els.need.value = quickSearchEl.value.trim();
      quickSearchEl.value = "";
      switchPage("search");
      runSearch();
    }
  });
}
els.dryRunButton.addEventListener("click", () => importZotero());
els.saveLlmConfig.addEventListener("click", () => saveLlmConfig());
els.saveSourceConfig.addEventListener("click", () => saveSourceConfig());
els.llmProvider.addEventListener("change", () => {
  applyProviderDefaults();
  updateDashboard();
});
els.llmEnabled.addEventListener("change", () => updateDashboard());
els.need.addEventListener("input", () => persistWorkspaceSnapshot());
initFileUpload();
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
els.exportBibtex.addEventListener("click", () => exportPapers("bibtex"));
els.exportCsv.addEventListener("click", () => exportPapers("csv"));
els.exportRis.addEventListener("click", () => exportPapers("ris"));
const analysisToggle = document.getElementById("analysis-toggle");
if (analysisToggle) {
  analysisToggle.addEventListener("click", () => {
    const panel = document.getElementById("analysis-panel");
    if (panel) {
      const isOpen = !panel.classList.contains("collapsed");
      panel.classList.toggle("collapsed", isOpen);
      analysisToggle.textContent = isOpen ? "展开" : "收起";
    }
  });
}
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
els.confirmPlanSearch.addEventListener("click", () => runSearch());
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
loadSearchHistory();
renderSearchHistory();
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

function loadSearchHistory() {
  try {
    const stored = localStorage.getItem(SEARCH_HISTORY_KEY);
    if (stored) {
      state.searchHistory = JSON.parse(stored);
    }
  } catch {}
}

function persistSearchHistory() {
  try {
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(state.searchHistory.slice(0, 50)));
  } catch {}
}

function renderSearchHistory() {
  const list = els.intentHistoryList;
  if (!list) return;
  list.innerHTML = "";
  const entries = state.searchHistory;
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty-copy";
    empty.textContent = "暂无检索记录";
    list.append(empty);
    return;
  }
  for (const entry of entries) {
    const item = document.createElement("div");
    item.className = `intent-history-item ${entry.id === state.selectedMockTaskId ? "active" : ""}`;
    item.title = entry.need || entry.title;

    const titleEl = document.createElement("span");
    titleEl.className = "intent-history-title";
    titleEl.textContent = entry.title || entry.need.slice(0, 40);

    const metaParts = [];
    if (entry.zhKeywordCount) metaParts.push(`${entry.zhKeywordCount} 中文词`);
    if (entry.enKeywordCount) metaParts.push(`${entry.enKeywordCount} 英文词`);
    if (entry.paperCount) metaParts.push(`${entry.paperCount} 篇文献`);
    if (metaParts.length) {
      const metaEl = document.createElement("span");
      metaEl.className = "intent-history-meta";
      metaEl.textContent = metaParts.join(" · ");
      item.append(titleEl, metaEl);
    } else {
      item.append(titleEl);
    }

    item.addEventListener("click", () => {
      onSelectSearchHistory(entry.id);
    });
    list.append(item);
  }
}

function addSearchHistory(need, title, sources, zhKeywordCount, enKeywordCount, paperCount, plan, papers) {
  const entry = {
    id: `search-${Date.now()}`,
    title: title || need.slice(0, 40),
    need,
    sources: sources || [],
    zhKeywordCount: zhKeywordCount || 0,
    enKeywordCount: enKeywordCount || 0,
    paperCount: paperCount || 0,
    time: new Date().toISOString(),
    plan: plan || null,
    papers: Array.isArray(papers) ? papers.slice(0, 50).map(stripPaperRaw) : [],
  };
  state.searchHistory = [entry, ...state.searchHistory.filter((e) => e.id !== entry.id)].slice(0, 50);
  persistSearchHistory();
  renderSearchHistory();
}

function stripPaperRaw(paper) {
  if (!paper || typeof paper !== "object") return paper;
  const { raw, ...rest } = paper;
  return rest;
}

function onSelectSearchHistory(id) {
  const entry = state.searchHistory.find((e) => e.id === id);
  if (!entry) return;
  state.selectedMockTaskId = id;
  els.need.value = entry.need;

  if (entry.plan) {
    state.plan = entry.plan;
    state.papers = entry.papers || [];
    state.visiblePapers = [];
    state.sourceMeta = {};
    state.selectedKeys = new Set();
    renderPlan(state.plan);
    clearErrors();
    applyResultControls();
    setFlowStep(state.papers.length ? "search" : "plan");
    setStatus(
      `已恢复历史检索：${state.papers.length} 篇文献`,
    );
  } else {
    setStatus("已载入历史检索（仅恢复检索词，完整结果请查看历史归档）。");
  }

  renderSearchHistory();
  persistWorkspaceSnapshot();
  setActivePage("search");
}

window.onSelectTask = function onSelectTask(taskId) {
  onSelectSearchHistory(taskId);
};

function startNewResearch() {
  els.need.value = "";
  els.zhKeywords.value = "";
  els.enKeywords.value = "";
  els.fromYear.value = "";
  els.limit.value = String(DEFAULT_CANDIDATE_POOL_SIZE);
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
  _resetFileUploadUI();
  els.keywordOutput.innerHTML = "";
  els.planDetailOutput.innerHTML = "";
  updateReportLink("");
  applyResultControls();
  setFlowStep("ask");
  setStatus("已新建文献课题。");
  renderSearchHistory();
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
  const sunIcon = els.themeToggle.querySelector(".theme-sun");
  const moonIcon = els.themeToggle.querySelector(".theme-moon");
  if (sunIcon && moonIcon) {
    sunIcon.style.display = normalized === "dark" ? "" : "none";
    moonIcon.style.display = normalized === "dark" ? "none" : "";
  }
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
  const limit = String(candidatePoolLimit());
  const parts = [
    keywordCount ? `${keywordCount} 组关键词` : "关键词待补充",
    fromYear ? `${fromYear} 起` : "年份待设置",
    `候选池 ${limit}/源`,
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
  const base = {
    need: els.need.value.trim(),
    zhKeywords: splitKeywords(els.zhKeywords.value),
    enKeywords: splitKeywords(els.enKeywords.value),
    useLlm: els.useLlm.checked,
  };
  if (state.fileContext) {
    base.fileContext = state.fileContext;
  }
  if (state.searchDimensions) {
    base.searchDimensions = state.searchDimensions;
  }
  if (state.suggestedQueries) {
    base.suggestedQueries = state.suggestedQueries;
  }
  return base;
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
    state.sourceMeta = {};
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

/** Stores the last search payload so "retry" can re-run it. */
let _lastSearchPayload = null;

window.retryLastSearch = function retryLastSearch() {
  if (_lastSearchPayload) {
    runSearch(_lastSearchPayload);
  }
};

async function runSearch(externalPayload) {
  const payload = externalPayload || {
    ...payloadBase(),
    sources: selectedSources(),
    limit: candidatePoolLimit(),
    fromYear: els.fromYear.value ? Number(els.fromYear.value) : null,
    preferRecent: els.preferRecent.checked,
  };
  _lastSearchPayload = payload;
  clearErrors();
  resetProgress();
  setWorkflowStatus("检索中", "正在调用已选数据库并整理候选结果。");
  setFlowStep("search");
  setBusy(true, "正在检索，开放 API 可能需要几十秒。");
  try {
    const data = await runSearchStream(payload);
    state.plan = data.plan;
    state.papers = data.papers || [];
    state.sourceMeta = data.sourceMeta || {};
    state.selectedKeys = new Set();
    state.reportPath = data.reportPath || "";
    renderPlan(data.plan);
    renderErrors(data.errors || {});
    renderSourceSummary(data.errors || {}, state.sourceMeta);
    renderCharts(state.papers);
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
    resetProgress();
    showError(error.message);
  } finally {
    setBusy(false);
    // Save search history
    try {
      if (payload.need) {
        const historyTitle = payload.need.length > 40
          ? payload.need.slice(0, 40) + "…"
          : payload.need;
        const zhCount = (state.plan?.zh_keywords || []).length;
        const enCount = (state.plan?.en_keywords || []).length;
        addSearchHistory(payload.need, historyTitle, payload.sources, zhCount, enCount, state.papers.length, state.plan, state.papers);
      }
    } catch (e) {
      console.warn("Failed to save search history:", e);
    }
    // Hide progress panel 2s after so user sees final summary
    setTimeout(() => { els.searchProgressPanel.hidden = true; }, 2000);
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
    const hasErrors = result.errors && result.errors.length;
    setStatus(
      `Zotero：已创建 ${result.created || 0}，已跳过 ${result.skipped || 0}，错误 ${hasErrors ? result.errors.length : 0}`,
    );
    setWorkflowStatus(
      apply ? "已同步" : "预演中",
      apply ? "Zotero 同步完成。" : "已完成 Zotero 预演检查。",
    );
    if (hasErrors) {
      showError(result.errors.join("\n"));
    }
    addHistoryEntry(apply ? "写入 Zotero" : "预演导入 Zotero", {
      selected: selectedPapers.length,
      created: result.created || 0,
      skipped: result.skipped || 0,
      errors: hasErrors ? result.errors.length : 0,
      applied: apply,
    });
    if (apply && !hasErrors) {
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

async function exportPapers(format) {
  const papers = state.selectedKeys.size
    ? state.papers.filter((paper) => state.selectedKeys.has(paperKey(paper)))
    : state.papers;
  if (!papers.length) {
    setStatus("没有可导出的文献。");
    return;
  }
  setBusy(true, `正在导出 ${papers.length} 篇文献…`);
  try {
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        format,
        papers: papers.map((p) => {
          const { raw, ...rest } = p;
          return rest;
        }),
      }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: "导出失败。" }));
      throw new Error(err.error || "导出失败。");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `export.${format === "bibtex" ? "bib" : format}`;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    const ext = format.toUpperCase();
    setStatus(`已导出 ${papers.length} 篇文献（${ext}）。`);
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
  els.limit.value = general.maxResultsPerSource || DEFAULT_CANDIDATE_POOL_SIZE;
  els.preferRecent.checked = general.preferRecent !== false;
  const llm = config.llm || {};
  els.llmEnabled.checked = Boolean(llm.enabled);
  els.useLlm.checked = Boolean(llm.hasApiKey);
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
  const enabledSources = new Set(config.general?.enabledSources || []);
  if (enabledSources.size) {
    for (const input of sourceInputs) {
      input.checked = enabledSources.has(input.value);
    }
  }
  els.semanticScholarApiKey.value = "";
  els.googleScholarApiKey.value = "";
  els.webOfScienceApiKey.value = "";
  // Zotero: show configured keys but not the actual value (password field cleared on purpose)
  const zotero = sources.zotero || {};
  els.zoteroLibraryId.value = zotero.libraryId || "";
  els.zoteroApiKey.value = "";
  els.zoteroLibraryType.value = zotero.libraryType || "user";
  els.zoteroCollectionKey.value = zotero.hasCollectionKey ? "(已配置)" : "";
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
      zoteroLibraryId: els.zoteroLibraryId.value.trim(),
      zoteroApiKey: els.zoteroApiKey.value.trim(),
      zoteroLibraryType: els.zoteroLibraryType.value,
      zoteroCollectionKey: els.zoteroCollectionKey.value.trim(),
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
    zoteroReadyText(sources.zotero),
  ].join(" · ");
}

function zoteroReadyText(status) {
  if (!status) return "Zotero 未配置";
  return status.configured ? "Zotero 已配置" : "Zotero 未配置";
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
  renderPlanValueLayer(plan);
  renderPlanEngineLayer(plan);
  updatePlannerMode(plan);
}

function renderPlanValueLayer(plan) {
  els.keywordOutput.innerHTML = "";

  const header = document.createElement("div");
  header.className = "plan-summary-head";
  header.innerHTML = `
    <div>
      <p>Search Plan</p>
      <h4>方案已压缩为可执行摘要</h4>
    </div>
    <div class="plan-summary-actions">
      <span>${escapeHtml(planBadgeText(plan))}</span>
      <button type="button" class="plan-edit-btn" title="编辑检索方案">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        <span>编辑方案</span>
      </button>
    </div>
  `;
  header.querySelector(".plan-edit-btn").addEventListener("click", () => openPlanEditor(plan));

  const grid = document.createElement("div");
  grid.className = "plan-value-grid";
  grid.append(researchQuestionPanel(plan), searchDimensionsPanel(plan), keywordClusterPanel(plan));

  els.keywordOutput.append(header, grid);
}

function researchQuestionPanel(plan) {
  const questions = nonEmptyList(plan.research_questions);
  const items = questions.length ? questions : [plan.need || "当前研究意图"];
  const box = document.createElement("section");
  box.className = "plan-value-card";
  box.innerHTML = "<h4>研究问题</h4>";

  const list = document.createElement("ul");
  list.className = "plan-question-list";
  for (const item of items.slice(0, 4)) {
    const li = document.createElement("li");
    li.textContent = item;
    list.append(li);
  }
  box.append(list);
  return box;
}

function searchDimensionsPanel(plan) {
  const dims = Array.isArray(plan.search_dimensions) ? plan.search_dimensions.filter(Boolean) : [];
  if (!dims.length) return document.createDocumentFragment();

  const box = document.createElement("section");
  box.className = "plan-value-card plan-keyword-card";
  box.innerHTML = "<h4>检索维度拆解</h4>";

  for (const dim of dims) {
    const group = document.createElement("div");
    group.className = "plan-keyword-cluster";

    const zhTerms = nonEmptyList(dim.zh_terms).slice(0, 8);
    const enTerms = nonEmptyList(dim.en_terms).slice(0, 8);
    const dimName = dim.name || "";
    const dimNameEn = dim.name_en || "";

    group.innerHTML = `
      <p>
        <strong>${escapeHtml(dimName)}</strong>
        ${dimNameEn ? `<span class="dim-en-label">${escapeHtml(dimNameEn)}</span>` : ""}
      </p>
    `;

    if (zhTerms.length) {
      const tags = document.createElement("div");
      tags.className = "plan-pill-row";
      for (const term of zhTerms) {
        const pill = document.createElement("span");
        pill.className = "plan-pill";
        pill.textContent = term;
        tags.append(pill);
      }
      group.append(tags);
    }

    if (enTerms.length) {
      const tags = document.createElement("div");
      tags.className = "plan-pill-row";
      tags.style.marginTop = "6px";
      for (const term of enTerms) {
        const pill = document.createElement("span");
        pill.className = "plan-pill plan-pill-en";
        pill.textContent = term;
        tags.append(pill);
      }
      group.append(tags);
    }

    box.append(group);
  }

  return box;
}

function keywordClusterPanel(plan) {
  const box = document.createElement("section");
  box.className = "plan-value-card plan-keyword-card plan-value-full";
  box.innerHTML = "<h4>关键词簇</h4>";

  const clusters = [
    { label: "核心概念", items: conceptTags(plan.core_concepts || []) },
    { label: "中文关键词", items: nonEmptyList(plan.zh_keywords).slice(0, 12) },
    { label: "英文关键词", items: nonEmptyList(plan.en_keywords).slice(0, 12) },
  ].filter((cluster) => cluster.items.length);

  if (!clusters.length) {
    const empty = document.createElement("p");
    empty.className = "empty-copy";
    empty.textContent = "暂无关键词，系统会在检索时自动拆解。";
    box.append(empty);
    return box;
  }

  for (const cluster of clusters) {
    const group = document.createElement("div");
    group.className = "plan-keyword-cluster";
    group.innerHTML = `<p>${escapeHtml(cluster.label)}</p>`;
    const tags = document.createElement("div");
    tags.className = "plan-pill-row";
    for (const keyword of cluster.items) {
      const pill = document.createElement("span");
      pill.className = "plan-pill";
      pill.textContent = keyword;
      tags.append(pill);
    }
    group.append(tags);
    box.append(group);
  }
  return box;
}

function openPlanEditor(plan) {
  const overlay = document.createElement("div");
  overlay.className = "plan-editor-overlay";

  const modal = document.createElement("div");
  modal.className = "plan-editor-modal";

  modal.innerHTML = `
    <div class="plan-editor-head">
      <h3>编辑检索方案</h3>
      <p>修改后点击保存，方案将更新并重新应用到检索。</p>
    </div>
    <div class="plan-editor-body">
      <label class="plan-editor-field">
        <span>中文关键词（每行一个）</span>
        <textarea id="plan-edit-zh" rows="5">${escapeHtml((plan.zh_keywords || []).join("\n"))}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>英文关键词（每行一个）</span>
        <textarea id="plan-edit-en" rows="5">${escapeHtml((plan.en_keywords || []).join("\n"))}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>OpenAlex 检索式</span>
        <textarea id="plan-edit-openalex" rows="2">${escapeHtml(plan.queries?.openalex || "")}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>Crossref 检索式</span>
        <textarea id="plan-edit-crossref" rows="2">${escapeHtml(plan.queries?.crossref || "")}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>Semantic Scholar 检索式</span>
        <textarea id="plan-edit-semantic" rows="2">${escapeHtml(plan.queries?.semantic_scholar || "")}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>Google Scholar 检索式</span>
        <textarea id="plan-edit-google" rows="2">${escapeHtml(plan.queries?.google_scholar || "")}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>Web of Science 检索式</span>
        <textarea id="plan-edit-wos" rows="2">${escapeHtml(plan.queries?.web_of_science || "")}</textarea>
      </label>
      <label class="plan-editor-field">
        <span>CNKI 检索式</span>
        <textarea id="plan-edit-cnki" rows="2">${escapeHtml(plan.queries?.cnki || "")}</textarea>
      </label>
    </div>
    <div class="plan-editor-actions">
      <button type="button" class="plan-editor-cancel">取消</button>
      <button type="button" class="plan-editor-save">保存修改</button>
    </div>
  `;

  overlay.append(modal);
  document.body.append(overlay);

  // Animate in
  requestAnimationFrame(() => overlay.classList.add("open"));

  const close = () => {
    overlay.classList.remove("open");
    setTimeout(() => overlay.remove(), 200);
  };

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });

  modal.querySelector(".plan-editor-cancel").addEventListener("click", close);

  modal.querySelector(".plan-editor-save").addEventListener("click", () => {
    const zhRaw = modal.querySelector("#plan-edit-zh").value;
    const enRaw = modal.querySelector("#plan-edit-en").value;
    plan.zh_keywords = zhRaw.split("\n").map(s => s.trim()).filter(Boolean);
    plan.en_keywords = enRaw.split("\n").map(s => s.trim()).filter(Boolean);
    plan.queries = plan.queries || {};
    plan.queries.openalex = modal.querySelector("#plan-edit-openalex").value.trim();
    plan.queries.crossref = modal.querySelector("#plan-edit-crossref").value.trim();
    plan.queries.semantic_scholar = modal.querySelector("#plan-edit-semantic").value.trim();
    plan.queries.google_scholar = modal.querySelector("#plan-edit-google").value.trim();
    plan.queries.web_of_science = modal.querySelector("#plan-edit-wos").value.trim();
    plan.queries.cnki = modal.querySelector("#plan-edit-cnki").value.trim();
    // Clear stale query_rounds so they regenerate on next plan render
    plan.query_rounds = {};

    renderPlan(plan);
    if (state.papers.length) {
      applyResultControls();
    }
    close();
    setStatus("检索方案已更新。");
  });
}

function renderPlanEngineLayer(plan) {
  els.planDetailOutput.innerHTML = "";

  const head = document.createElement("div");
  head.className = "plan-engine-head";
  head.innerHTML = `
    <button type="button" class="plan-edit-btn" title="编辑检索方案">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
      <span>编辑方案</span>
    </button>
  `;
  head.querySelector(".plan-edit-btn").addEventListener("click", () => openPlanEditor(plan));

  const details = document.createElement("details");
  details.className = "plan-engine-panel";
  details.innerHTML = `
    <summary>
      <span>查看底层布尔检索式与深度过滤策略</span>
      <small>${escapeHtml(engineSummaryText(plan))}</small>
    </summary>
  `;

  const body = document.createElement("div");
  body.className = "plan-engine-body";
  body.append(criteriaGrid(plan), queryRoundsPanel(plan));
  details.append(body);
  els.planDetailOutput.append(head, details);
}

function criteriaGrid(plan) {
  const grid = document.createElement("div");
  grid.className = "plan-criteria-grid";
  const cards = [
    detailCard("纳入标准", nonEmptyList(plan.inclusion_criteria)),
    detailCard("排除标准", nonEmptyList(plan.exclusion_criteria)),
    detailCard("检索策略", nonEmptyList(plan.search_strategy)),
    detailCard("系统备注", nonEmptyList(plan.notes)),
  ].filter(Boolean);
  for (const card of cards) grid.append(card);
  if (!cards.length) {
    const empty = document.createElement("p");
    empty.className = "empty-copy";
    empty.textContent = "当前方案没有额外过滤条件。";
    grid.append(empty);
  }
  return grid;
}

function detailCard(title, items) {
  if (!items.length) return null;
  const card = document.createElement("section");
  card.className = "plan-engine-card";
  card.innerHTML = `<h4>${escapeHtml(title)}</h4>`;
  const list = document.createElement("ul");
  for (const item of items.slice(0, 6)) {
    const li = document.createElement("li");
    li.textContent = item;
    list.append(li);
  }
  card.append(list);
  return card;
}

function queryRoundsPanel(plan) {
  const panel = document.createElement("section");
  panel.className = "plan-query-rounds";
  panel.innerHTML = "<h4>分库检索式与查询轮次</h4>";

  const sources = planSources(plan);
  if (!sources.length) {
    const empty = document.createElement("p");
    empty.className = "empty-copy";
    empty.textContent = "暂无底层检索式。";
    panel.append(empty);
    return panel;
  }

  for (const source of sources) {
    panel.append(sourceQueryBlock(source, plan));
  }
  return panel;
}

function sourceQueryBlock(source, plan) {
  const meta = state.sourceMeta?.[source] || {};
  const rounds = queryRoundsForSource(plan, source);
  const block = document.createElement("article");
  block.className = "plan-query-source";
  block.innerHTML = `
    <div class="plan-query-source-head">
      <strong>${escapeHtml(sourceLabel(source))}</strong>
      <span>${escapeHtml(sourceMetaSummary(meta, rounds.length))}</span>
    </div>
  `;

  const list = document.createElement("div");
  list.className = "plan-query-list";
  rounds.forEach((query, index) => {
    const stat = roundStat(meta, index + 1);
    const item = document.createElement("div");
    item.className = "plan-query-item";
    item.innerHTML = `
      <div>
        <strong>第 ${index + 1} 轮</strong>
        <span>${escapeHtml(roundStatText(stat))}</span>
      </div>
      <code>${escapeHtml(query)}</code>
    `;
    list.append(item);
  });
  block.append(list);
  return block;
}

function planSources(plan) {
  return Array.from(
    new Set([
      ...Object.keys(plan.queries || {}),
      ...Object.keys(plan.query_rounds || {}),
    ]),
  );
}

function queryRoundsForSource(plan, source) {
  const rounds = nonEmptyList(plan.query_rounds?.[source]);
  if (rounds.length) return rounds;
  const primary = plan.queries?.[source];
  return primary ? [primary] : [];
}

function conceptTags(concepts) {
  return concepts
    .flatMap((concept) => [
      concept.label_zh || "",
      concept.label_en || "",
      ...(concept.synonyms_zh || []).slice(0, 2),
      ...(concept.synonyms_en || []).slice(0, 2),
    ])
    .filter(Boolean)
    .slice(0, 10);
}

function nonEmptyList(value) {
  return Array.isArray(value)
    ? value.map((item) => String(item || "").trim()).filter(Boolean)
    : [];
}

function planBadgeText(plan) {
  const keywordCount = nonEmptyList(plan.zh_keywords).length + nonEmptyList(plan.en_keywords).length;
  const sourceCount = planSources(plan).length;
  const roundCount = planSources(plan).reduce(
    (total, source) => total + queryRoundsForSource(plan, source).length,
    0,
  );
  const planner = plan.planner === "llm" ? "AI 规划" : "规则规划";
  return `${planner} · ${keywordCount} 个关键词 · ${sourceCount} 个来源 · ${roundCount} 轮查询`;
}

function engineSummaryText(plan) {
  const sourceCount = planSources(plan).length;
  const roundCount = planSources(plan).reduce(
    (total, source) => total + queryRoundsForSource(plan, source).length,
    0,
  );
  return `${sourceCount} 个来源 / ${roundCount} 轮`;
}

function sourceMetaSummary(meta, fallbackRounds) {
  const roundCount = meta.queryRoundCount ?? fallbackRounds;
  const successful = meta.successfulRounds;
  const unique = meta.uniqueBeforeDedupe;
  if (unique !== undefined && unique !== null) {
    return `${roundCount} 轮 · ${successful ?? 0} 轮成功 · 去重前 ${unique} 条`;
  }
  return `${roundCount} 轮查询`;
}

function roundStat(meta, round) {
  return (meta.roundStats || []).find((item) => Number(item.round) === round);
}

function roundStatText(stat) {
  if (!stat) return "待执行";
  if (stat.error) return `错误：${stat.error}`;
  return `取回 ${stat.retrievedCount ?? 0} · 新增 ${stat.newUniqueCount ?? 0}`;
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
  const html = [];
  for (const [source, error] of entries) {
    html.push(
      `<details class="source-error-detail">
        <summary><strong>${escapeHtml(sourceLabel(source))}</strong> <span class="error-badge">出错</span></summary>
        <p class="error-message">${escapeHtml(error)}</p>
      </details>`
    );
  }
  // Add retry button
  html.push(
    `<div class="error-actions">
      <button id="retry-search-btn" class="retry-btn" onclick="retryLastSearch()">
        <span class="retry-icon">↻</span> 重试检索
      </button>
    </div>`
  );
  els.errorOutput.innerHTML = html.join("");
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
    "zotero",
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
    if (state.papers.length > 0 && papers.length === 0) {
      // Has results but all filtered out
      els.papersEmpty.innerHTML =
        '<div class="empty-state"><h3>筛选无结果</h3><p>当前筛选条件未匹配到文献，试试调整关键词或清除筛选条件。</p></div>';
    } else if (state.plan) {
      // Search was attempted but returned nothing
      els.papersEmpty.innerHTML =
        '<div class="empty-state"><h3>未找到匹配文献</h3><p>当前检索条件未返回结果，建议调整关键词、扩大年份范围或启用更多数据源。</p></div>';
    } else {
      els.papersEmpty.innerHTML = '<p>检索结果将呈现在此处。</p>';
    }
    renderPagination(papers);
    updateSelectionUi();
    return;
  }

  const totalPages = Math.ceil(papers.length / PAGE_SIZE);
  const page = Math.min(state.currentPage, totalPages);
  const start = (page - 1) * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, papers.length);
  const pagePapers = papers.slice(start, end);

  pagePapers.forEach((paper, index) => {
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

    node.querySelector(".paper-rank-badge").textContent = start + index === 0 ? "最佳" : "候选";
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

    const score = paper.relevance_score ?? paper.score ?? null;
    const relevanceTags = relevanceTagElements(paper, score);
    if (relevanceTags) {
      metrics.after(relevanceTags);
    }

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

    const imported = paperImported(paper);
    const zoteroBtn = document.createElement("button");
    zoteroBtn.type = "button";
    zoteroBtn.className = "paper-zotero-btn";
    zoteroBtn.textContent = imported ? "已导入 Zotero" : "导入 Zotero";
    zoteroBtn.disabled = imported;
    zoteroBtn.classList.toggle("active", imported);
    zoteroBtn.addEventListener("click", async () => {
      zoteroBtn.disabled = true;
      zoteroBtn.textContent = "同步中…";
      try {
        const data = await postJson("/api/import-zotero", {
          papers: [paper],
          limit: 1,
          apply: true,
        });
        const result = data.result || {};
        if (!result.errors || !result.errors.length) {
          paper.imported = true;
          paper.zoteroImported = true;
          zoteroBtn.textContent = "已导入 Zotero";
          zoteroBtn.classList.add("active");
          setStatus(`Zotero：已创建 ${result.created || 0} 篇文献。`);
        } else {
          zoteroBtn.disabled = false;
          zoteroBtn.textContent = "导入重试";
          showError(result.errors.join("\n"));
        }
        persistWorkspaceMemory();
        renderSavedPapers();
        renderPapers(state.visiblePapers);
      } catch (error) {
        zoteroBtn.disabled = false;
        zoteroBtn.textContent = "导入 Zotero";
        showError(error.message);
      }
    });
    favoriteButton.parentNode.insertBefore(zoteroBtn, favoriteButton.nextSibling);

    els.papers.append(node);
  });

  renderPagination(papers);
  updateSelectionUi();
}

function renderPagination(papers) {
  let paginationEl = document.getElementById("pagination-controls");
  if (!paginationEl) {
    paginationEl = document.createElement("div");
    paginationEl.id = "pagination-controls";
    paginationEl.className = "pagination-bar";
    els.papers.after(paginationEl);
  }

  const total = papers.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  if (totalPages <= 1) {
    paginationEl.innerHTML = `<span class="pagination-info">共 ${total} 条</span>`;
    return;
  }

  const page = Math.min(state.currentPage, totalPages);
  let html = `<span class="pagination-info">共 ${total} 条，第 ${page}/${totalPages} 页</span><div class="pagination-buttons">`;

  html += `<button type="button" class="pagination-btn" onclick="changePage(${page - 1})" ${page <= 1 ? "disabled" : ""}>‹ 上一页</button>`;

  const maxVisible = 7;
  let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
  let endPage = Math.min(totalPages, startPage + maxVisible - 1);
  if (endPage - startPage + 1 < maxVisible) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  if (startPage > 1) {
    html += `<button type="button" class="pagination-btn" onclick="changePage(1)">1</button>`;
    if (startPage > 2) html += `<span class="pagination-ellipsis">…</span>`;
  }

  for (let i = startPage; i <= endPage; i++) {
    html += `<button type="button" class="pagination-btn ${i === page ? "active" : ""}" onclick="changePage(${i})">${i}</button>`;
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) html += `<span class="pagination-ellipsis">…</span>`;
    html += `<button type="button" class="pagination-btn" onclick="changePage(${totalPages})">${totalPages}</button>`;
  }

  html += `<button type="button" class="pagination-btn" onclick="changePage(${page + 1})" ${page >= totalPages ? "disabled" : ""}>下一页 ›</button>`;
  html += "</div>";
  paginationEl.innerHTML = html;
}

window.changePage = function changePage(page) {
  const totalPages = Math.ceil(state.visiblePapers.length / PAGE_SIZE);
  state.currentPage = Math.max(1, Math.min(page, totalPages));
  renderPapers(state.visiblePapers);
};

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
  state.currentPage = 1;
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
  const hasPapers = state.papers.length > 0;
  els.exportBibtex.disabled = !hasPapers;
  els.exportCsv.disabled = !hasPapers;
  els.exportRis.disabled = !hasPapers;
  updateDashboard();
}

function updateSidebarBadges() {
  const searchLink = document.querySelector('.sidebar-link[data-page="search"]');
  const collectionLink = document.querySelector('.sidebar-link[data-page="collection"]');
  const archiveLink = document.querySelector('.sidebar-link[data-page="archive"]');
  if (searchLink) searchLink.dataset.count = String(state.papers.length || "");
  if (collectionLink) collectionLink.dataset.count = String(state.savedPapers.length || "");
  if (archiveLink) archiveLink.dataset.count = String(state.archiveItems.length || "");
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
  updateSidebarBadges();
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
    els.limit.value = normalizedCandidatePoolValue(snapshot.limit);
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
  renderCharts(state.papers);
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
      <button type="button" data-saved-action="import" ${imported ? "disabled" : ""}>${imported ? "已同步" : "导入 Zotero"}</button>
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
    if (!result.errors || !result.errors.length) {
      paper.imported = true;
      paper.zoteroImported = true;
      setStatus(`已同步到 Zotero：创建 ${result.created || 0}，跳过 ${result.skipped || 0}。`);
    } else {
      showError(result.errors.join("\n"));
    }
    persistWorkspaceMemory();
    renderSavedPapers();
    renderPapers(state.visiblePapers);
    addHistoryEntry("收藏页导入 Zotero", {
      title: paper.title || "未命名文献",
      created: result.created || 0,
      skipped: result.skipped || 0,
      errors: (result.errors || []).length,
    });
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

  // Research questions
  const questions = nonEmptyList(plan.research_questions);
  const questionsHtml = questions.length
    ? `<ul class="plan-question-list">${questions.slice(0, 6).map(q => `<li>${escapeHtml(q)}</li>`).join("")}</ul>`
    : "";

  // Search dimensions
  const dims = Array.isArray(plan.search_dimensions) ? plan.search_dimensions.filter(Boolean) : [];
  const dimsHtml = dims.length
    ? dims.map(dim => {
        const zhTerms = nonEmptyList(dim.zh_terms).slice(0, 8);
        const enTerms = nonEmptyList(dim.en_terms).slice(0, 8);
        const dimName = dim.name || "";
        const dimNameEn = dim.name_en || "";
        return `<div class="archive-dim-block">
          <p class="archive-dim-title"><strong>${escapeHtml(dimName)}</strong>${dimNameEn ? ` <span class="dim-en-label">${escapeHtml(dimNameEn)}</span>` : ""}</p>
          ${zhTerms.length ? `<div class="archive-chip-row">${zhTerms.map(t => `<span class="archive-chip">${escapeHtml(t)}</span>`).join("")}</div>` : ""}
          ${enTerms.length ? `<div class="archive-chip-row" style="margin-top:4px">${enTerms.map(t => `<span class="archive-chip archive-chip-en">${escapeHtml(t)}</span>`).join("")}</div>` : ""}
        </div>`;
      }).join("")
    : "";

  // Query rounds
  const queries = plan.queries || {};
  const queryRounds = plan.query_rounds || {};
  const querySources = Object.keys(queryRounds).length ? Object.keys(queryRounds) : Object.keys(queries);
  const queriesHtml = querySources.length
    ? querySources.map(src => {
        const rounds = (queryRounds[src] || [queries[src]].filter(Boolean)).slice(0, 4);
        if (!rounds.length) return "";
        return `<div class="archive-query-block">
          <p class="archive-dim-title"><strong>${escapeHtml(sourceLabel(src))}</strong> <span class="dim-en-label">${rounds.length} 轮</span></p>
          <ol class="archive-query-list">${rounds.map((q, i) => `<li><code>${escapeHtml(q.slice(0, 120))}${q.length > 120 ? "…" : ""}</code></li>`).join("")}</ol>
        </div>`;
      }).join("")
    : "";

  // Papers list (all papers, not just 5)
  const papersHtml = papers.length
    ? papers.map((paper, i) => `
        <article class="archive-paper-preview">
          <span class="archive-paper-index">#${i + 1}</span>
          <div class="archive-paper-body">
            <h5>${escapeHtml(paper.title || "未命名文献")}</h5>
            <p>${escapeHtml((paper.authors || []).slice(0, 6).join(", ") || "作者信息待补")}</p>
            <span>${escapeHtml(`${paper.year || "年份未知"} · ${(paper.venue || "来源待补")}`)}</span>
          </div>
          ${paper.relevance_score != null ? `<span class="archive-paper-score">${Math.round(paper.relevance_score * 100)}%</span>` : ""}
        </article>
      `).join("")
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
          <li>候选池规模/源：${escapeHtml(formatArchiveField(entry.limit))}</li>
          <li>优先最新/高被引：${escapeHtml(formatArchiveBoolean(entry.preferRecent))}</li>
          <li>AI 优化检索词：${escapeHtml(formatArchiveBoolean(entry.useLlm))}</li>
        </ul>
      </section>
      ${questionsHtml ? `<section class="archive-detail-section"><h4>研究问题</h4>${questionsHtml}</section>` : ""}
      ${dimsHtml ? `<section class="archive-detail-section archive-detail-dims"><h4>检索维度拆解</h4>${dimsHtml}</section>` : ""}
      <section class="archive-detail-section">
        <h4>检索方案</h4>
        <ul class="archive-detail-list">
          ${archiveListItems(plan.search_strategy)}
          ${!Array.isArray(plan.search_strategy) || !plan.search_strategy.length ? "<li>暂无方案说明。</li>" : ""}
        </ul>
      </section>
      ${queriesHtml ? `<section class="archive-detail-section archive-detail-queries"><h4>分库检索式</h4>${queriesHtml}</section>` : ""}
      <section class="archive-detail-section">
        <h4>来源与模型</h4>
        <ul class="archive-detail-list">
          <li>规划方式：${escapeHtml(plan.planner === "llm" ? "大模型规划器" : "规则规划器")}</li>
          <li>数据源：${escapeHtml(formatSources(entry.sources))}</li>
          ${sourceMetaHtml || "<li>暂无来源元数据。</li>"}
        </ul>
      </section>
      <section class="archive-detail-section full-width">
        <h4>结果摘要（${papers.length} 篇）</h4>
        <div class="archive-paper-preview-list">${papersHtml}</div>
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
  renderCharts(state.papers);
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
  if (typeof payload.limit !== "undefined" && payload.limit !== null) {
    els.limit.value = normalizedCandidatePoolValue(payload.limit);
  }
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

function candidatePoolLimit() {
  return normalizedCandidatePoolValue(els.limit.value);
}

function normalizedCandidatePoolValue(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 20) return DEFAULT_CANDIDATE_POOL_SIZE;
  return Math.max(1, Math.min(200, Math.round(parsed)));
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

function relevanceTagElements(paper, score) {
  const reasons = paper.relevance_reasons;
  if ((!reasons || !reasons.length) && score === null) return null;

  const container = document.createElement("div");
  container.className = "paper-relevance-tags";

  // Add relevance score badge
  if (score !== null) {
    const scoreTag = document.createElement("span");
    const scoreClass = score >= 6 ? "high" : score >= 3 ? "medium" : "low";
    scoreTag.className = `paper-relevance-tag paper-relevance-score ${scoreClass}`;
    scoreTag.textContent = `得分 ${Number(score).toFixed(1)}`;
    container.append(scoreTag);
  }

  // Add reason tags
  if (reasons && reasons.length) {
    for (const reason of reasons) {
      const tag = document.createElement("span");
      tag.className = "paper-relevance-tag";
      if (reason.includes("核心技术")) tag.classList.add("tech");
      else if (reason.includes("研究对象")) tag.classList.add("population");
      else if (reason.includes("核心现象")) tag.classList.add("phenomenon");
      else if (reason.includes("交叉匹配") || reason.includes("综合匹配")) tag.classList.add("bonus");
      else if (reason.includes("降权") || reason.includes("惩罚") || reason.includes("强降权")) tag.classList.add("penalty");
      const label = reason.replace(/\([^)]*\)/, "").replace(/:\d+$/, "");
      tag.textContent = label;
      container.append(tag);
    }
  }

  return container;
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
    zotero: "Zotero",
  }[key] || key;
}

function setBusy(isBusy, message = "") {
  els.planButton.disabled = isBusy;
  els.searchButton.disabled = isBusy;
  els.dryRunButton.disabled = isBusy || state.selectedKeys.size === 0;
  els.saveLlmConfig.disabled = isBusy;
  els.saveSourceConfig.disabled = isBusy;
  if (message) {
    setStatus(message);
    if (isBusy) {
      const dots = document.createElement("span");
      dots.className = "loading-dots";
      dots.append(document.createElement("span"));
      dots.append(document.createElement("span"));
      dots.append(document.createElement("span"));
      els.status.append(dots);
    }
  }
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

// ── Search Progress Panel ─────────────────────────────────

const SOURCE_LABELS = {
  openalex: "OpenAlex",
  crossref: "Crossref",
  semantic_scholar: "Semantic Scholar",
  google_scholar: "Google Scholar",
  web_of_science: "Web of Science",
  zotero: "Zotero 文献库",
};

let _progressState = {};

function resetProgress() {
  _progressState = {};
  els.searchProgressPanel.hidden = true;
}

function initProgress(sources) {
  _progressState = { total: sources.length, done: 0, items: {} };
  const list = els.progressSourceList;
  list.innerHTML = "";
  for (const src of sources) {
    const label = SOURCE_LABELS[src] || src;
    _progressState.items[src] = { status: "waiting", count: 0 };
    const item = document.createElement("div");
    item.className = "progress-source-item";
    item.id = "progress-" + src;
    item.innerHTML = `
      <span class="progress-source-icon" id="picon-${src}">◯</span>
      <span class="progress-source-name">${escapeHtml(label)}</span>
      <span class="progress-source-detail" id="pdetail-${src}">等待中</span>
      <span class="progress-source-bar" id="pbar-${src}">
        <span class="progress-source-bar-fill" id="pfill-${src}" style="width:0%"></span>
      </span>
    `;
    list.append(item);
  }
  updateProgressSummary();
  els.searchProgressPanel.hidden = false;
}

function updateProgress(src, status, count, errorMsg) {
  const item = _progressState.items[src];
  if (!item) return;
  item.status = status;
  if (count !== undefined) item.count = count;

  const icon = document.querySelector("#picon-" + src);
  const detail = document.querySelector("#pdetail-" + src);
  const fill = document.querySelector("#pfill-" + src);

  switch (status) {
    case "running":
      if (icon) icon.textContent = "◌";
      if (detail) detail.textContent = "搜索中...";
      if (fill) { fill.style.width = "50%"; fill.className = "progress-source-bar-fill searching"; }
      break;
    case "complete":
      if (icon) icon.textContent = "✓";
      if (detail) detail.textContent = count + " 篇";
      if (fill) { fill.style.width = "100%"; fill.className = "progress-source-bar-fill"; }
      _progressState.done++;
      break;
    case "error":
      if (icon) icon.textContent = "✗";
      if (detail) detail.textContent = errorMsg || "出错";
      if (fill) { fill.style.width = "100%"; fill.className = "progress-source-bar-fill error"; }
      _progressState.done++;
      break;
  }
  updateProgressSummary();
}

function updateProgressSummary() {
  const s = _progressState;
  if (els.progressSummary) {
    els.progressSummary.textContent = `${s.done} / ${s.total} 已完成`;
  }
}

// ── Streaming Search ─────────────────────────────────────

async function runSearchStream(payload) {
  const response = await fetch("/api/search-stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error || "流式检索请求失败。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      if (!part.trim()) continue;
      const lines = part.split("\n");
      let eventType = "message";
      let jsonData = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) eventType = line.slice(7);
        else if (line.startsWith("data: ")) jsonData = line.slice(6);
      }
      if (!jsonData) continue;
      const data = JSON.parse(jsonData);

      switch (eventType) {
        case "sources":
          initProgress(data.sources);
          break;
        case "running":
          updateProgress(data.source, "running");
          break;
        case "complete":
          updateProgress(data.source, "complete", data.paper_count);
          break;
        case "error":
          updateProgress(data.source, "error", 0, data.message);
          break;
        case "done":
          result = data;
          break;
      }
    }
  }
  return result;
}

// ── Analysis Charts (SVG) ──────────────────────────────────

function renderCharts(papers) {
  renderYearChart(papers);
  renderSourceChart(papers);
  renderCitationChart(papers);
  const panel = document.getElementById("analysis-panel");
  if (panel) {
    panel.hidden = papers.length === 0;
  }
}

function renderYearChart(papers) {
  const svg = document.getElementById("chart-year-svg");
  if (!svg) return;
  const years = {};
  for (const p of papers) {
    const y = p.year;
    if (y) years[y] = (years[y] || 0) + 1;
  }
  const entries = Object.entries(years).sort((a, b) => Number(a[0]) - Number(b[0]));
  if (!entries.length) { svg.innerHTML = ""; return; }

  const margin = 30;
  const W = 370;
  const H = 170;
  const maxVal = Math.max(...entries.map((e) => e[1])) || 1;
  const barW = Math.min(30, (W - margin - 10) / entries.length - 4);
  const colors = ["#2dd4bf", "#0ea5e9", "#8b5cf6", "#f59e0b", "#ef4444"];

  let html = `<line x1="${margin}" y1="10" x2="${margin}" y2="${H - 10}" stroke="#2a2a3a" stroke-width="1"/>
    <line x1="${margin}" y1="${H - 10}" x2="${W}" y2="${H - 10}" stroke="#2a2a3a" stroke-width="1"/>`;
  entries.forEach(([year, count], i) => {
    const barH = (count / maxVal) * (H - 40);
    const x = margin + 4 + i * (barW + 4);
    const y = H - 10 - barH;
    const color = colors[i % colors.length];
    html += `<rect x="${x}" y="${y}" width="${barW}" height="${barH}" rx="3" fill="${color}" opacity="0.85">
      <title>${year}: ${count} 篇</title></rect>`;
    if (barW > 8) {
      html += `<text x="${x + barW / 2}" y="${H - 20}" text-anchor="middle" font-size="8" fill="#94a3b8">${year}</text>`;
    } else if (i % 2 === 0) {
      html += `<text x="${x + barW / 2}" y="${H - 20}" text-anchor="middle" font-size="7" fill="#94a3b8">${year}</text>`;
    }
  });
  svg.innerHTML = html;
}

function renderSourceChart(papers) {
  const svg = document.getElementById("chart-source-svg");
  if (!svg) return;
  const sources = {};
  for (const p of papers) {
    const srcList = p.sources || [p.source];
    for (const s of srcList) {
      if (s) sources[s] = (sources[s] || 0) + 1;
    }
  }
  const entries = Object.entries(sources).sort((a, b) => b[1] - a[1]).slice(0, 6);
  if (!entries.length) { svg.innerHTML = ""; return; }

  const total = entries.reduce((s, e) => s + e[1], 0) || 1;
  const colors = ["#2dd4bf", "#0ea5e9", "#8b5cf6", "#f59e0b", "#ef4444", "#34d399"];
  const cx = 80, cy = 100, r = 65;
  let html = "";
  let cumulative = 0;

  entries.forEach(([key, count], i) => {
    const angle = (cumulative / total) * 360;
    const sweep = (count / total) * 360;
    cumulative += count;
    const a1 = (angle - 90) * (Math.PI / 180);
    const a2 = ((angle + sweep) - 90) * (Math.PI / 180);
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2);
    const y2 = cy + r * Math.sin(a2);
    const large = sweep > 180 ? 1 : 0;
    const color = colors[i % colors.length];
    html += `<path d="M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z" fill="${color}" opacity="0.85">
      <title>${sourceLabel(key)}: ${count} 篇 (${Math.round((count / total) * 100)}%)</title></path>`;
  });

  // Legend on the right
  const lx = 180, ly = 20;
  entries.forEach(([key, count], i) => {
    const color = colors[i % colors.length];
    html += `<rect x="${lx}" y="${ly + i * 22}" width="10" height="10" rx="2" fill="${color}"/>`;
    html += `<text x="${lx + 16}" y="${ly + i * 22 + 9}" font-size="10" fill="#94a3b8">${sourceLabel(key)}: ${count}</text>`;
  });
  svg.innerHTML = html;
}

function renderCitationChart(papers) {
  const svg = document.getElementById("chart-citation-svg");
  if (!svg) return;
  const points = papers
    .map((p) => ({ x: p.year || 0, y: p.cited_by_count || 0, title: p.title || "" }))
    .filter((p) => p.x > 0)
    .sort((a, b) => a.x - b.x);
  if (points.length < 2) { svg.innerHTML = ""; return; }

  const margin = { top: 10, right: 10, bottom: 25, left: 35 };
  const W = 370, H = 170;
  const maxY = Math.max(...points.map((p) => p.y)) || 1;
  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  const rangeX = Math.max(maxX - minX, 1);

  let html = `<line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${H - margin.bottom}" stroke="#2a2a3a" stroke-width="1"/>
    <line x1="${margin.left}" y1="${H - margin.bottom}" x2="${W}" y2="${H - margin.bottom}" stroke="#2a2a3a" stroke-width="1"/>`;

  // Y axis ticks
  for (let i = 0; i <= 4; i++) {
    const val = Math.round((maxY / 4) * i);
    const y = H - margin.bottom - (i / 4) * (H - margin.top - margin.bottom);
    html += `<text x="${margin.left - 4}" y="${y + 3}" text-anchor="end" font-size="8" fill="#94a3b8">${val}</text>`;
  }

  points.forEach((p) => {
    const px = margin.left + ((p.x - minX) / rangeX) * (W - margin.left - margin.right);
    const py = H - margin.bottom - (p.y / maxY) * (H - margin.top - margin.bottom);
    html += `<circle cx="${px}" cy="${py}" r="2.5" fill="#2dd4bf" opacity="0.6">
      <title>${escapeHtml(p.title || "")}: ${p.y} 次引用 (${p.x})</title></circle>`;
  });
  svg.innerHTML = html;
}

// ── File Upload / Multimodal Input ───────────────────────────

function _resetFileUploadUI() {
  const dropzone = document.querySelector("#file-dropzone");
  const preview = document.querySelector("#file-preview");
  const statusEl = document.querySelector("#file-upload-status");
  const fileInput = document.querySelector("#file-input");
  if (dropzone) dropzone.hidden = false;
  if (preview) preview.hidden = true;
  if (statusEl) statusEl.hidden = true;
  if (fileInput) fileInput.value = "";
  state.fileContext = "";
  state.searchDimensions = null;
  state.suggestedQueries = null;
}

function initFileUpload() {
  const dropzone = document.querySelector("#file-dropzone");
  const fileInput = document.querySelector("#file-input");
  const preview = document.querySelector("#file-preview");
  const previewName = document.querySelector("#file-preview-name");
  const clearBtn = document.querySelector("#file-preview-clear");
  const statusEl = document.querySelector("#file-upload-status");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag-over");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    const files = e.dataTransfer?.files;
    if (files?.length) handleFile(files[0]);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files?.length) handleFile(fileInput.files[0]);
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", () => clearFileUpload());
  }

  async function handleFile(file) {
    const maxSize = 20 * 1024 * 1024; // 20 MB
    if (file.size > maxSize) {
      showFileStatus("文件超过 20MB 限制。", true);
      return;
    }

    previewName.textContent = file.name;
    dropzone.hidden = true;
    preview.hidden = false;
    showFileStatus("正在分析文件…", false);

    try {
      const base64 = await fileToBase64(file);
      const data = await postJson("/api/analyze-file", {
        filename: file.name,
        content: base64.split(",").pop() || base64,
        mimeType: file.type || "application/octet-stream",
      });

      if (data.description) {
        els.need.value = data.description;
      }
      if (Array.isArray(data.keywordsZh) && data.keywordsZh.length) {
        els.zhKeywords.value = data.keywordsZh.join(", ");
      }
      if (Array.isArray(data.keywordsEn) && data.keywordsEn.length) {
        els.enKeywords.value = data.keywordsEn.join(", ");
      }
      state.fileContext = data.sourceText || "";
      state.searchDimensions = data.searchDimensions || null;
      state.suggestedQueries = data.suggestedQueries || null;

      const dimCount = (state.searchDimensions && state.searchDimensions.length) || 0;
      showFileStatus(`分析完成：已提取研究主题与 ${data.keywordsZh.length + data.keywordsEn.length} 个关键词${dimCount ? `、${dimCount} 个检索维度` : ""}。`, false);
      updateSearchSettingsSummary();
      persistWorkspaceSnapshot();
    } catch (error) {
      showFileStatus(`分析失败：${error.message}`, true);
      clearFileUpload();
    }
  }

  function showFileStatus(message, isError) {
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.hidden = false;
    statusEl.className = "file-upload-status" + (isError ? " error" : "");
  }

  function clearFileUpload() {
    preview.hidden = true;
    dropzone.hidden = false;
    statusEl.hidden = true;
    fileInput.value = "";
    state.fileContext = "";
    state.searchDimensions = null;
    state.suggestedQueries = null;
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("读取文件失败。"));
    reader.readAsDataURL(file);
  });
}
