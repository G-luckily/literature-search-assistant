import { useState } from "react";

const MOCK_HISTORY = [
  { id: "ai-zotero", title: "AI 辅助文献检索与 Zotero 协同管理" },
  { id: "youth-ai", title: "青年群体与人工智能使用经验" },
  { id: "emotion-capital", title: "公考青年的情感资本困境" },
  { id: "policy-ai", title: "人工智能与社会政策治理" },
  { id: "workflow", title: "知识管理工具与研究工作流" },
  { id: "review-method", title: "系统综述方法与智能检索策略" },
];

export default function LiteratureResearchLayout({
  children,
  onNewResearch = () => {},
  onSelectTask = () => {},
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTaskId, setActiveTaskId] = useState("");

  function selectTask(taskId) {
    setActiveTaskId(taskId);
    onSelectTask(taskId);
  }

  function createResearch() {
    setActiveTaskId("");
    onNewResearch();
  }

  return (
    <div className="flex h-screen w-full bg-white text-slate-950">
      <aside
        className={[
          "flex h-full shrink-0 flex-col border-r border-gray-100 bg-white transition-all duration-300",
          sidebarOpen ? "w-72 px-3 py-4" : "w-16 px-2 py-4",
        ].join(" ")}
      >
        <div className="space-y-2">
          <button
            type="button"
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((value) => !value)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-400 transition-colors duration-200 hover:bg-gray-50 hover:text-gray-900"
          >
            <span className="relative block h-3.5 w-4">
              <span className="absolute left-0 top-0 h-px w-4 rounded-full bg-current" />
              <span className="absolute left-0 top-1.5 h-px w-4 rounded-full bg-current" />
              <span className="absolute left-0 top-3 h-px w-4 rounded-full bg-current" />
            </span>
          </button>

          <button
            type="button"
            onClick={createResearch}
            className={[
              "flex h-10 w-full items-center gap-2 rounded-xl px-3 text-sm font-medium text-gray-500 transition-colors duration-200 hover:bg-gray-50 hover:text-gray-950",
              sidebarOpen ? "justify-start" : "justify-center px-0",
            ].join(" ")}
          >
            <span className="text-base leading-none">+</span>
            {sidebarOpen && <span className="truncate">新建文献课题</span>}
          </button>
        </div>

        <div className="mt-5 min-h-0 flex-1">
          {sidebarOpen && (
            <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-300">
              History
            </p>
          )}

          <div className="h-full overflow-y-auto">
            {MOCK_HISTORY.map((task) => (
              <button
                key={task.id}
                type="button"
                onClick={() => selectTask(task.id)}
                title={task.title}
                className={[
                  "mb-1 flex h-9 w-full items-center rounded-lg text-left text-sm transition-all duration-200",
                  sidebarOpen ? "px-3" : "justify-center px-0",
                  activeTaskId === task.id
                    ? "bg-gray-50 text-gray-950"
                    : "text-gray-400 hover:bg-gray-50 hover:text-gray-900",
                ].join(" ")}
              >
                {sidebarOpen ? (
                  <span className="truncate">{task.title}</span>
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                )}
              </button>
            ))}
          </div>
        </div>

        <div
          className={[
            "mt-4 flex items-center gap-3 rounded-xl p-2 transition-all duration-300",
            sidebarOpen ? "justify-start" : "justify-center",
          ].join(" ")}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-500">
            G
          </div>
          {sidebarOpen && (
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-600">Guo</p>
              <p className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Zotero 已连接
              </p>
            </div>
          )}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col items-center justify-center px-6 transition-all duration-300">
        {children}
      </main>
    </div>
  );
}
