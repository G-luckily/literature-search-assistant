const state = {
  plan: null,
  papers: [],
  visiblePapers: [],
  selectedKeys: new Set(),
  reportPath: "",
  config: null,
  sourceMeta: {},
  workflowLabel: "待命",
  workflowDetail: "等待执行检索。",
};

const els = {
  need: document.querySelector("#need"),
  zhKeywords: document.querySelector("#zh-keywords"),
  enKeywords: document.querySelector("#en-keywords"),
  limit: document.querySelector("#limit"),
  fromYear: document.querySelector("#from-year"),
  preferRecent: document.querySelector("#prefer-recent"),
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
  llmTimeout: document.querySelector("#llm-timeout"),
  llmClearKey: document.querySelector("#llm-clear-key"),
  saveLlmConfig: document.querySelector("#save-llm-config"),
  llmConfigStatus: document.querySelector("#llm-config-status"),
  sourceStatus: document.querySelector("#source-status"),
  semanticScholarApiKey: document.querySelector("#semantic-scholar-api-key"),
  semanticScholarMonthlySearchBudget: document.querySelector(
    "#semantic-scholar-monthly-search-budget",
  ),
  semanticScholarWarningRemaining: document.querySelector(
    "#semantic-scholar-warning-remaining",
  ),
  semanticScholarCacheOnlyRemaining: document.querySelector(
    "#semantic-scholar-cache-only-remaining",
  ),
  semanticScholarCacheTtlDays: document.querySelector(
    "#semantic-scholar-cache-ttl-days",
  ),
  clearSemanticScholarApiKey: document.querySelector("#clear-semantic-scholar-api-key"),
  googleScholarApiKey: document.querySelector("#google-scholar-api-key"),
  googleScholarEndpoint: document.querySelector("#google-scholar-endpoint"),
  clearGoogleScholarApiKey: document.querySelector("#clear-google-scholar-api-key"),
  webOfScienceApiKey: document.querySelector("#web-of-science-api-key"),
  webOfScienceEndpoint: document.querySelector("#web-of-science-endpoint"),
  clearWebOfScienceApiKey: document.querySelector("#clear-web-of-science-api-key"),
  saveSourceConfig: document.querySelector("#save-source-config"),
  sourceConfigStatus: document.querySelector("#source-config-status"),
  filterText: document.querySelector("#filter-text"),
  pdfOnly: document.querySelector("#pdf-only"),
  sortBy: document.querySelector("#sort-by"),
  selectVisible: document.querySelector("#select-visible"),
  clearSelection: document.querySelector("#clear-selection"),
  keywordOutput: document.querySelector("#keyword-output"),
  planDetailOutput: document.querySelector("#plan-detail-output"),
  errorOutput: document.querySelector("#error-output"),
  papersEmpty: document.querySelector("#papers-empty"),
  papers: document.querySelector("#papers"),
  reportLink: document.querySelector("#report-link"),
  paperTemplate: document.querySelector("#paper-template"),
  selectedSourceCount: document.querySelector("#selected-source-count"),
  statSourceCount: document.querySelector("#stat-source-count"),
  statPaperCount: document.querySelector("#stat-paper-count"),
  statWorkflowLabel: document.querySelector("#stat-workflow-label"),
  statWorkflowDetail: document.querySelector("#stat-workflow-detail"),
  workflowPill: document.querySelector("#workflow-pill"),
  executionSteps: document.querySelector("#execution-steps"),
  insightText: document.querySelector("#insight-text"),
  plannerMode: document.querySelector("#planner-mode"),
  selectionCount: document.querySelector("#selection-count"),
  resultsCount: document.querySelector("#results-count"),
};

const sourceInputs = [...document.querySelectorAll('input[name="source"]')];

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
els.useLlm.addEventListener("change", () => updateDashboard());
els.filterText.addEventListener("input", () => applyResultControls());
els.pdfOnly.addEventListener("change", () => applyResultControls());
els.sortBy.addEventListener("change", () => applyResultControls());
els.selectVisible.addEventListener("click", () => selectVisiblePapers());
els.clearSelection.addEventListener("click", () => clearSelection());
for (const input of sourceInputs) {
  input.addEventListener("change", () => {
    renderSourceBadges();
    renderExecutionSteps(state.plan);
    updateInsight(state.plan);
    updateDashboard();
  });
}

loadConfig();
renderExecutionSteps(null);
updateInsight(null);
updateDashboard();

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
  setBusy(true, "正在生成检索计划。");
  try {
    const data = await postJson("/api/plan", payloadBase());
    state.plan = data.plan;
    renderPlan(data.plan);
    setStatus("检索计划已生成。");
    setWorkflowStatus("方案就绪", "研究问题已经拆解为可执行检索步骤。");
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
  } catch (error) {
    setConfigStatus(`配置读取失败：${error.message}`);
    setSourceConfigStatus(`配置读取失败：${error.message}`);
    renderSourceBadges();
    updateDashboard();
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
  updateDashboard();
}

function renderSourceConfig(config) {
  const sources = config.sources || {};
  els.semanticScholarApiKey.value = "";
  els.semanticScholarMonthlySearchBudget.value =
    sources.semantic_scholar?.monthlySearchBudget || 250;
  els.semanticScholarWarningRemaining.value =
    sources.semantic_scholar?.warningRemaining || 50;
  els.semanticScholarCacheOnlyRemaining.value =
    sources.semantic_scholar?.cacheOnlyRemaining || 25;
  els.semanticScholarCacheTtlDays.value =
    sources.semantic_scholar?.cacheTtlDays || 30;
  els.clearSemanticScholarApiKey.checked = false;
  els.googleScholarApiKey.value = "";
  els.googleScholarEndpoint.value =
    sources.google_scholar?.endpoint || "https://serpapi.com/search.json";
  els.clearGoogleScholarApiKey.checked = false;
  els.webOfScienceApiKey.value = "";
  els.webOfScienceEndpoint.value =
    sources.web_of_science?.endpoint ||
    "https://api.clarivate.com/apis/wos-starter/v1/documents";
  els.clearWebOfScienceApiKey.checked = false;
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
      semanticScholarMonthlySearchBudget: Number(
        els.semanticScholarMonthlySearchBudget.value || 250,
      ),
      semanticScholarWarningRemaining: Number(
        els.semanticScholarWarningRemaining.value || 50,
      ),
      semanticScholarCacheOnlyRemaining: Number(
        els.semanticScholarCacheOnlyRemaining.value || 25,
      ),
      semanticScholarCacheTtlDays: Number(
        els.semanticScholarCacheTtlDays.value || 30,
      ),
      clearSemanticScholarApiKey: els.clearSemanticScholarApiKey.checked,
      googleScholarApiKey: els.googleScholarApiKey.value.trim(),
      googleScholarEndpoint: els.googleScholarEndpoint.value.trim(),
      clearGoogleScholarApiKey: els.clearGoogleScholarApiKey.checked,
      webOfScienceApiKey: els.webOfScienceApiKey.value.trim(),
      webOfScienceEndpoint: els.webOfScienceEndpoint.value.trim(),
      clearWebOfScienceApiKey: els.clearWebOfScienceApiKey.checked,
    });
    state.config = data;
    renderConfig(data);
    setStatus("数据源配置已保存。");
    setWorkflowStatus("已配置", "数据源策略与 Key 配置已更新。");
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
  renderExecutionSteps(plan);
  renderKeywordOutput(plan);
  renderPlanDetails(plan);
  updatePlannerMode(plan);
  updateInsight(plan);
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

function renderExecutionSteps(plan) {
  els.executionSteps.innerHTML = "";
  const steps = buildExecutionSteps(plan);
  for (const step of steps) {
    const item = document.createElement("article");
    item.className = `step-item ${step.highlight ? "highlight" : ""}`;
    item.innerHTML = `<div class="step-index">${escapeHtml(step.label)}</div><div class="step-content">${escapeHtml(step.text)}</div>`;
    els.executionSteps.append(item);
  }
}

function buildExecutionSteps(plan) {
  const selected = selectedSources();
  const labels = selected.length ? selected.map(sourceLabel).join("、") : "已选数据源";
  const steps = [];

  steps.push({
    label: "步骤 01",
    text: plan
      ? plan.planner === "llm"
        ? "使用已配置的大模型规划器，把研究问题拆解为可执行的概念块与检索关键词。"
        : "使用规则规划器，把研究问题拆解为可执行的概念块与检索关键词。"
      : "等待输入研究问题，以生成可执行的概念块和关键词族。",
  });

  steps.push({
    label: "步骤 02",
    text: plan?.queries && Object.keys(plan.queries).length
      ? `已为 ${Object.keys(plan.queries).length} 个数据库生成检索式：${Object.keys(plan.queries).map(sourceLabel).join("、")}。`
      : `执行检索后，将对 ${labels} 发起查询。`,
  });

  if (plan?.search_strategy?.length) {
    steps.push({
      label: "步骤 03",
      text: plan.search_strategy[0],
    });
  } else {
    steps.push({
      label: "步骤 03",
      text: "跨来源结果会进行去重，并按新近性、相关性或引用信号排序。",
    });
  }

  if (state.papers.length) {
    steps.push({
      label: `步骤 ${String(steps.length + 1).padStart(2, "0")}`,
      text: `已在 ${selected.length || 1} 个启用数据源上完成去重与排序，共得到 ${state.papers.length} 篇候选文献。`,
      highlight: true,
    });
  } else {
    steps[steps.length - 1].highlight = true;
  }

  return steps.slice(0, 4);
}

function updateInsight(plan) {
  const selected = selectedSources().map(sourceLabel);
  if (state.papers.length && plan?.core_concepts?.length) {
    const first = primaryConceptLabel(plan.core_concepts[0]);
    els.insightText.textContent = `当前结果已围绕“${first}”形成主轴，建议优先复核高相关候选文献，再决定是否扩展到更宽泛的邻近概念。`;
    return;
  }
  if (plan?.core_concepts?.length) {
    const first = primaryConceptLabel(plan.core_concepts[0]);
    const second = plan.core_concepts[1] ? primaryConceptLabel(plan.core_concepts[1]) : "";
    els.insightText.textContent = second
      ? `建议把“${first}”作为主概念，把“${second}”作为限制条件，用于缩小检索空间并提升命中质量。`
      : `建议把“${first}”作为首要概念轴，再按方法、场景或时间范围继续细化检索式。`;
    return;
  }
  if (selected.length) {
    els.insightText.textContent = `当前已准备对 ${selected.join("、")} 建立检索通路。输入研究问题后，系统会生成关键词矩阵和查询逻辑。`;
    return;
  }
  els.insightText.textContent = "先定义研究问题，系统会把核心概念、检索式和候选文献分析同步铺开。";
}

function primaryConceptLabel(concept) {
  return concept.label_zh || concept.label_en || "核心概念";
}

function updatePlannerMode(plan) {
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

    node.querySelector(".paper-rank-badge").textContent = index === 0 ? "最佳匹配" : "候选";
    node.querySelector(".paper-domain").textContent = paperDomainLabel(paper);
    node.querySelector(".paper-title").textContent = paper.title || "未命名文献";
    node.querySelector(".paper-authors").textContent =
      (paper.authors || []).slice(0, 8).join(", ") || "作者信息待补";
    node.querySelector(".paper-abstract").textContent = trimText(
      paper.abstract || "暂无摘要。",
      420,
    );

    const metrics = node.querySelector(".paper-metrics");
    addPaperMetric(metrics, "年份", paper.year || "暂无");
    addPaperMetric(metrics, "引用", paper.cited_by_count ?? "暂无");
    addPaperMetric(metrics, "开放获取", paper.oa_status || "未知");
    addPaperMetric(
      metrics,
      "得分",
      formatScore(paper.relevance_score ?? paper.score ?? null),
    );

    const sources = (paper.sources || [paper.source]).filter(Boolean).map(sourceLabel);
    node.querySelector(".paper-meta-line").textContent = [
      paper.venue || "期刊/会议待补",
      paper.year || "年份待补",
      sources.join(" · "),
    ]
      .filter(Boolean)
      .join(" · ");

    const links = node.querySelector(".paper-links");
    addLink(links, "详情", paper.url);
    addLink(links, "PDF", paper.pdf_url);
    if (paper.doi) addLink(links, "DOI", `https://doi.org/${paper.doi}`);

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
  const pdfOnly = els.pdfOnly.checked;
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
  renderExecutionSteps(state.plan);
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
  updateDashboard();
}

function updateDashboard() {
  const sourceCount = selectedSources().length;
  const visibleCount = state.visiblePapers.length;
  const totalCount = state.papers.length;

  els.selectedSourceCount.textContent = `已选 ${sourceCount} 个`;
  els.statSourceCount.textContent = String(sourceCount).padStart(2, "0");
  els.statPaperCount.textContent = Intl.NumberFormat("en-US").format(totalCount);
  els.statWorkflowLabel.textContent = state.workflowLabel;
  els.statWorkflowDetail.textContent = state.workflowDetail;
  els.workflowPill.textContent = state.workflowLabel;

  els.resultsCount.textContent = totalCount
    ? visibleCount !== totalCount
      ? `${visibleCount} / ${totalCount} 条记录`
      : `${totalCount} 条记录`
    : "0 条记录";
}

function setWorkflowStatus(label, detail) {
  state.workflowLabel = label;
  state.workflowDetail = detail;
  updateDashboard();
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

function updateReportLink(url) {
  if (!url) {
    els.reportLink.hidden = true;
    return;
  }
  els.reportLink.hidden = false;
  els.reportLink.href = url;
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
