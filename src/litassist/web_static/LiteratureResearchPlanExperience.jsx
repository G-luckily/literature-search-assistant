import { useState } from "react";

const MOCK_PLAN = {
  prompt:
    "我想研究 AI 辅助文献检索与 Zotero 协同管理，重点关注近五年的工具实践、知识组织和研究工作流。",
  researchQuestions: [
    "AI 如何改变学术文献检索、筛选与综述写作流程？",
    "Zotero 等知识管理工具如何与 AI 检索系统协同？",
    "近五年相关工具实践中有哪些可复用的研究工作流？",
  ],
  keywordClusters: [
    {
      label: "AI 检索",
      tags: ["AI search", "semantic retrieval", "LLM agents", "research assistant"],
    },
    {
      label: "知识管理",
      tags: ["Zotero", "reference management", "knowledge organization", "PKM"],
    },
    {
      label: "研究工作流",
      tags: ["literature review", "screening workflow", "academic writing", "evidence synthesis"],
    },
  ],
  inclusionCriteria: [
    "2020 年以后发表的同行评审论文、预印本或高质量系统综述。",
    "明确讨论 AI 工具在文献检索、筛选、管理或综述写作中的作用。",
    "包含 Zotero、Mendeley、Obsidian、Notion 或其他知识库协同场景。",
  ],
  exclusionCriteria: [
    "仅介绍通用聊天机器人能力，缺少学术检索或文献管理场景的材料。",
    "没有方法描述、实验案例或工作流复盘的纯观点文章。",
  ],
  booleanQueries: {
    OpenAlex:
      '("AI search" OR "semantic retrieval" OR "large language model" OR "research assistant") AND ("Zotero" OR "reference management" OR "knowledge organization") AND ("literature review" OR "academic workflow")',
    "Web of Science":
      'TS=(("artificial intelligence" OR "large language model*" OR "semantic search") AND ("reference manager*" OR "Zotero" OR "knowledge management") AND ("literature review" OR "research workflow"))',
    SemanticScholar:
      '("LLM" OR "AI research assistant" OR "semantic literature search") + ("Zotero" OR "reference management") + ("review workflow" OR "evidence synthesis")',
  },
};

export default function LiteratureResearchPlanExperience() {
  const [query, setQuery] = useState(MOCK_PLAN.prompt);
  const [isSearched, setIsSearched] = useState(false);

  return (
    <main className="min-h-screen bg-[#f7f8fa] px-5 py-6 text-slate-950">
      <section
        className={[
          "mx-auto flex min-h-[78vh] w-full flex-col items-center transition-all duration-500 ease-out",
          isSearched ? "justify-start" : "justify-center",
        ].join(" ")}
      >
        {!isSearched && (
          <div className="mb-8 text-center transition-all duration-500">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.28em] text-teal-700">
              Literature Research
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
              你想研究什么？
            </h1>
            <p className="mt-4 text-base text-slate-500">
              直接描述研究意图，系统会自动拆解关键词、范围与检索策略。
            </p>
          </div>
        )}

        <div
          className={[
            "w-full bg-white shadow-[0_4px_20px_rgba(0,0,0,0.05)] transition-all duration-500 ease-out",
            isSearched
              ? "sticky top-6 z-20 max-w-3xl rounded-[28px] px-5 py-3 shadow-sm"
              : "max-w-5xl rounded-[34px] p-8",
          ].join(" ")}
        >
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例如：我想研究 AI 如何改变近五年的文献综述工作流..."
            className={[
              "w-full resize-none border-0 bg-transparent text-slate-950 outline-none placeholder:text-slate-300",
              isSearched
                ? "h-14 text-sm leading-7"
                : "h-64 text-xl leading-9",
            ].join(" ")}
          />

          <div className="mt-4 flex items-center justify-end gap-3">
            {isSearched && (
              <button
                type="button"
                onClick={() => setIsSearched(false)}
                className="rounded-full px-4 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
              >
                重新编辑
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsSearched(true)}
              className="rounded-full bg-slate-950 px-6 py-3 text-sm font-medium text-white shadow-lg shadow-slate-950/10 transition-all hover:scale-[1.03] hover:bg-slate-800"
            >
              生成方案
            </button>
          </div>
        </div>

        {isSearched && (
          <section className="mt-10 w-full max-w-5xl pb-28 transition-all duration-500">
            <div className="mb-5 flex items-end justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">
                  Search Plan
                </p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                  已生成一份可执行检索方案
                </h2>
              </div>
              <span className="hidden rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 md:inline-flex">
                近五年 · 多库检索 · AI 优化
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-[1.05fr_1.4fr]">
              <article className="rounded-3xl bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
                <h3 className="text-sm font-semibold text-slate-950">研究问题</h3>
                <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
                  {MOCK_PLAN.researchQuestions.map((question) => (
                    <li key={question} className="flex gap-3">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                      <span>{question}</span>
                    </li>
                  ))}
                </ul>
              </article>

              <article className="rounded-3xl bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
                <h3 className="text-sm font-semibold text-slate-950">关键词簇</h3>
                <div className="mt-4 space-y-5">
                  {MOCK_PLAN.keywordClusters.map((cluster) => (
                    <div key={cluster.label}>
                      <p className="mb-2 text-xs font-medium text-slate-400">{cluster.label}</p>
                      <div className="flex flex-wrap gap-2">
                        {cluster.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </div>

            <details className="mt-4 rounded-3xl bg-white p-6 shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
              <summary className="cursor-pointer list-none text-sm font-medium text-slate-700 marker:hidden">
                ⚙️ 查看底层布尔检索式与深度过滤策略
              </summary>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Inclusion
                  </h4>
                  <ul className="space-y-2 text-sm leading-6 text-slate-600">
                    {MOCK_PLAN.inclusionCriteria.map((item) => (
                      <li key={item}>+ {item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Exclusion
                  </h4>
                  <ul className="space-y-2 text-sm leading-6 text-slate-600">
                    {MOCK_PLAN.exclusionCriteria.map((item) => (
                      <li key={item}>- {item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {Object.entries(MOCK_PLAN.booleanQueries).map(([source, queryText]) => (
                  <div key={source} className="rounded-2xl bg-gray-50 p-4">
                    <p className="mb-2 text-xs font-semibold text-slate-400">{source}</p>
                    <code className="block whitespace-pre-wrap break-words font-mono text-xs leading-6 text-slate-600">
                      {queryText}
                    </code>
                  </div>
                ))}
              </div>
            </details>
          </section>
        )}
      </section>

      {isSearched && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-white/70 bg-white/85 px-5 py-4 shadow-[0_-8px_30px_rgba(15,23,42,0.06)] backdrop-blur">
          <button
            type="button"
            className="mx-auto flex w-full max-w-sm items-center justify-center rounded-full bg-gradient-to-r from-slate-950 to-slate-800 py-4 text-sm font-medium text-white shadow-lg shadow-slate-950/20 transition-all hover:scale-105"
          >
            🚀 确认方案，立即拉取底层文献
          </button>
        </div>
      )}
    </main>
  );
}
