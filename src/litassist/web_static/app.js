const state = {
  plan: null,
  papers: [],
  visiblePapers: [],
  selectedKeys: new Set(),
  reportPath: "",
  config: null,
};

const els = {
  need: document.querySelector("#need"),
  zhKeywords: document.querySelector("#zh-keywords"),
  enKeywords: document.querySelector("#en-keywords"),
  limit: document.querySelector("#limit"),
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
  filterText: document.querySelector("#filter-text"),
  pdfOnly: document.querySelector("#pdf-only"),
  sortBy: document.querySelector("#sort-by"),
  selectVisible: document.querySelector("#select-visible"),
  clearSelection: document.querySelector("#clear-selection"),
  keywordOutput: document.querySelector("#keyword-output"),
  planDetailOutput: document.querySelector("#plan-detail-output"),
  errorOutput: document.querySelector("#error-output"),
  papers: document.querySelector("#papers"),
  paperCount: document.querySelector("#paper-count"),
  selectionCount: document.querySelector("#selection-count"),
  reportLink: document.querySelector("#report-link"),
  paperTemplate: document.querySelector("#paper-template"),
};

els.planButton.addEventListener("click", () => runPlan());
els.searchButton.addEventListener("click", () => runSearch());
els.dryRunButton.addEventListener("click", () => importZotero());
els.saveLlmConfig.addEventListener("click", () => saveLlmConfig());
els.llmProvider.addEventListener("change", () => applyProviderDefaults());
els.filterText.addEventListener("input", () => applyResultControls());
els.pdfOnly.addEventListener("change", () => applyResultControls());
els.sortBy.addEventListener("change", () => applyResultControls());
els.selectVisible.addEventListener("click", () => selectVisiblePapers());
els.clearSelection.addEventListener("click", () => clearSelection());

loadConfig();

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
  return [...document.querySelectorAll('input[name="source"]:checked')].map(
    (input) => input.value,
  );
}

async function runPlan() {
  setBusy(true, "正在生成检索计划。");
  try {
    const data = await postJson("/api/plan", payloadBase());
    state.plan = data.plan;
    renderPlan(data.plan);
    setStatus("检索计划已生成。");
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
  };
  setBusy(true, "正在检索，开放 API 可能需要几十秒。");
  clearErrors();
  try {
    const data = await postJson("/api/search", payload);
    state.plan = data.plan;
    state.papers = data.papers || [];
    state.selectedKeys = new Set(state.papers.map((paper) => paperKey(paper)));
    state.reportPath = data.reportPath || "";
    renderPlan(data.plan);
    renderErrors(data.errors || {});
    applyResultControls();
    setStatus(`检索完成：${state.papers.length} 篇候选文献。`);
    updateSelectionUi();
    updateReportLink(data.reportUrl);
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
  setBusy(true, apply ? "正在写入 Zotero。" : "正在执行 Zotero 预演。");
  try {
    const data = await postJson("/api/import-zotero", {
      papers: selectedPapers,
      limit: selectedPapers.length,
      apply,
    });
    const result = data.result || {};
    setStatus(
      `Zotero：created=${result.created || 0}, skipped=${result.skipped || 0}, errors=${(result.errors || []).length}`,
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
  }
}

function renderConfig(config) {
  const llm = config.llm || {};
  els.llmEnabled.checked = Boolean(llm.enabled);
  els.useLlm.checked = Boolean(llm.enabled);
  els.llmProvider.value = llm.provider || "deepseek";
  els.llmModel.value = llm.model || defaultModel(els.llmProvider.value);
  els.llmEndpoint.value = llm.endpoint || defaultEndpoint(els.llmProvider.value);
  els.llmTimeout.value = llm.requestTimeoutSeconds || 45;
  els.llmApiKey.value = "";
  els.llmClearKey.checked = false;
  setConfigStatus(
    `${providerLabel(els.llmProvider.value)} · ${llm.hasApiKey ? "API Key 已配置" : "API Key 未配置"}`,
  );
}

async function saveLlmConfig() {
  setBusy(true, "正在保存 LLM 配置。");
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
    setStatus("LLM 配置已保存。");
  } catch (error) {
    setConfigStatus(`保存失败：${error.message}`);
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
  if (provider === "openai") return "OpenAI";
  return "DeepSeek";
}

function setConfigStatus(message) {
  els.llmConfigStatus.textContent = message;
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
  els.keywordOutput.innerHTML = "";
  els.keywordOutput.append(
    plannerGroup(plan),
    keywordGroup("中文关键词", plan.zh_keywords || []),
    keywordGroup("English keywords", plan.en_keywords || []),
    queryGroup(plan.queries || {}),
  );
  renderPlanDetails(plan);
}

function plannerGroup(plan) {
  const box = document.createElement("section");
  box.className = "keyword-group";
  box.innerHTML = `<h3>拆解方式</h3><p>${escapeHtml(plan.planner === "llm" ? "LLM 结构化拆解" : "规则拆解")}</p>`;
  return box;
}

function renderPlanDetails(plan) {
  els.planDetailOutput.innerHTML = "";
  const fragments = [];
  fragments.push(detailList("研究问题", plan.research_questions || []));
  fragments.push(conceptList(plan.core_concepts || []));
  fragments.push(detailList("纳入标准", plan.inclusion_criteria || []));
  fragments.push(detailList("排除标准", plan.exclusion_criteria || []));
  fragments.push(detailList("检索策略", plan.search_strategy || []));
  for (const fragment of fragments) {
    if (fragment) els.planDetailOutput.append(fragment);
  }
}

function detailList(title, items) {
  if (!items.length) return null;
  const box = document.createElement("section");
  box.className = "detail-box";
  box.innerHTML = `<h3>${escapeHtml(title)}</h3>`;
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
  box.innerHTML = "<h3>核心概念</h3>";
  const list = document.createElement("ul");
  for (const concept of concepts) {
    const zh = concept.label_zh || "";
    const en = concept.label_en || "";
    const zhSyn = (concept.synonyms_zh || []).join("，");
    const enSyn = (concept.synonyms_en || []).join(", ");
    const li = document.createElement("li");
    li.textContent = [zh, en, zhSyn, enSyn].filter(Boolean).join(" / ");
    list.append(li);
  }
  box.append(list);
  return box;
}

function keywordGroup(title, keywords) {
  const box = document.createElement("section");
  box.className = "keyword-group";
  box.innerHTML = `<h3>${escapeHtml(title)}</h3>`;
  const chips = document.createElement("div");
  chips.className = "chips";
  if (!keywords.length) {
    chips.textContent = "暂无";
  } else {
    for (const keyword of keywords) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = keyword;
      chips.append(chip);
    }
  }
  box.append(chips);
  return box;
}

function queryGroup(queries) {
  const box = document.createElement("section");
  box.className = "keyword-group";
  box.innerHTML = "<h3>检索式</h3>";
  const list = document.createElement("div");
  list.className = "query-list";
  for (const [source, query] of Object.entries(queries)) {
    const item = document.createElement("div");
    item.innerHTML = `<strong>${escapeHtml(source)}</strong><code>${escapeHtml(query)}</code>`;
    list.append(item);
  }
  box.append(list);
  return box;
}

function renderErrors(errors) {
  clearErrors();
  const entries = Object.entries(errors);
  if (!entries.length) return;
  els.errorOutput.hidden = false;
  els.errorOutput.innerHTML = entries
    .map(([source, error]) => `<p><strong>${escapeHtml(source)}</strong>: ${escapeHtml(error)}</p>`)
    .join("");
}

function clearErrors() {
  els.errorOutput.hidden = true;
  els.errorOutput.innerHTML = "";
}

function renderPapers(papers) {
  els.papers.innerHTML = "";
  els.paperCount.textContent = `${papers.length} 篇`;
  for (const paper of papers) {
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
    const year = paper.year || "年份待补";
    const source = (paper.sources || [paper.source]).join(", ");
    node.querySelector(".paper-meta-line").textContent =
      `${year} · ${source} · 引用 ${paper.cited_by_count ?? "待补"} · ${paper.oa_status || "OA待补"}`;
    node.querySelector("h3").textContent = paper.title || "Untitled";
    node.querySelector(".authors").textContent = (paper.authors || []).slice(0, 8).join(", ");
    node.querySelector(".score-row").textContent = scoreText(paper);
    node.querySelector(".abstract").textContent = trimText(paper.abstract || "暂无摘要。", 520);
    const links = node.querySelector(".paper-links");
    addLink(links, "详情", paper.url);
    addLink(links, "PDF", paper.pdf_url);
    if (paper.doi) {
      addLink(links, "DOI", `https://doi.org/${paper.doi}`);
    }
    els.papers.append(node);
  }
  updateSelectionUi();
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
}

function sortPapers(left, right, sortBy) {
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
}

function paperKey(paper) {
  if (paper.doi) return `doi:${paper.doi.toLowerCase()}`;
  return `title:${paper.title || ""}:${paper.year || ""}`.toLowerCase();
}

function scoreText(paper) {
  const relevance = paper.relevance_score ?? "待补";
  const sourceScore = paper.score ?? "待补";
  const reasons = (paper.relevance_reasons || []).slice(0, 4).join("，");
  return `相关性 ${relevance} · 来源分 ${sourceScore}${reasons ? ` · 命中 ${reasons}` : ""}`;
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

function setBusy(isBusy, message = "") {
  els.planButton.disabled = isBusy;
  els.searchButton.disabled = isBusy;
  els.dryRunButton.disabled = isBusy || state.selectedKeys.size === 0;
  els.saveLlmConfig.disabled = isBusy;
  if (message) setStatus(message);
}

function setStatus(message) {
  els.status.textContent = message;
}

function showError(message) {
  setStatus("遇到错误。");
  els.errorOutput.hidden = false;
  els.errorOutput.textContent = message;
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
