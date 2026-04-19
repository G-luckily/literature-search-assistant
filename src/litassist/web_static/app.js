const state = {
  plan: null,
  papers: [],
  reportPath: "",
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
  keywordOutput: document.querySelector("#keyword-output"),
  errorOutput: document.querySelector("#error-output"),
  papers: document.querySelector("#papers"),
  paperCount: document.querySelector("#paper-count"),
  reportLink: document.querySelector("#report-link"),
  paperTemplate: document.querySelector("#paper-template"),
};

els.planButton.addEventListener("click", () => runPlan());
els.searchButton.addEventListener("click", () => runSearch());
els.dryRunButton.addEventListener("click", () => importZotero());

function payloadBase() {
  return {
    need: els.need.value.trim(),
    zhKeywords: splitKeywords(els.zhKeywords.value),
    enKeywords: splitKeywords(els.enKeywords.value),
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
    state.reportPath = data.reportPath || "";
    renderPlan(data.plan);
    renderErrors(data.errors || {});
    renderPapers(state.papers);
    setStatus(`检索完成：${state.papers.length} 篇候选文献。`);
    els.dryRunButton.disabled = state.papers.length === 0;
    updateReportLink(data.reportUrl);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function importZotero() {
  if (!state.papers.length) {
    setStatus("没有可导入的候选文献。");
    return;
  }
  const apply = els.applyImport.checked;
  setBusy(true, apply ? "正在写入 Zotero。" : "正在执行 Zotero 预演。");
  try {
    const data = await postJson("/api/import-zotero", {
      papers: state.papers,
      limit: state.papers.length,
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

async function postJson(url, payload) {
  if (!payload.need && url !== "/api/import-zotero") {
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
    keywordGroup("中文关键词", plan.zh_keywords || []),
    keywordGroup("English keywords", plan.en_keywords || []),
    queryGroup(plan.queries || {}),
  );
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
    const node = els.paperTemplate.content.firstElementChild.cloneNode(true);
    const year = paper.year || "年份待补";
    const source = (paper.sources || [paper.source]).join(", ");
    node.querySelector(".paper-meta-line").textContent =
      `${year} · ${source} · 引用 ${paper.cited_by_count ?? "待补"}`;
    node.querySelector("h3").textContent = paper.title || "Untitled";
    node.querySelector(".authors").textContent = (paper.authors || []).slice(0, 8).join(", ");
    node.querySelector(".abstract").textContent = trimText(paper.abstract || "暂无摘要。", 520);
    const links = node.querySelector(".paper-links");
    addLink(links, "详情", paper.url);
    addLink(links, "PDF", paper.pdf_url);
    if (paper.doi) {
      addLink(links, "DOI", `https://doi.org/${paper.doi}`);
    }
    els.papers.append(node);
  }
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
  els.dryRunButton.disabled = isBusy || state.papers.length === 0;
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
