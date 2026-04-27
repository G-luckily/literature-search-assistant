---
title: Literature Search Assistant
emoji: 🏃
colorFrom: yellow
colorTo: yellow
sdk: docker
pinned: false
---

# Literature Search Assistant

一个面向 Zotero 的文献检索 MVP：输入研究需求，生成中英文关键词和数据库检索式，调用开放学术 API 检索文献，去重、排序、导出报告，并可导入 Zotero。

当前版本先实现稳定链路：

- 需求拆解和中英文关键词生成
- 可选 LLM 结构化拆解研究问题、核心概念、纳入/排除标准
- OpenAlex、Crossref、Semantic Scholar 检索
- 可选 Google Scholar via SerpApi 与 Web of Science API 检索
- DOI / 标题去重
- 开放全文链接增强和伪 PDF 链接清理
- 默认近五年新文献优先、相关性评分、结果筛选和选中文献导入
- Semantic Scholar 本地 30 天缓存、月度预算统计和低余额缓存模式
- Markdown + JSON 报告
- Zotero Web API / pyzotero 导入
- CNKI 作为后续适配方向保留设计

## 快速开始

```powershell
uv sync --extra dev
Copy-Item config.example.toml config.toml
uv run litassist plan "我想研究人工智能辅助文献检索与Zotero协同管理"
uv run litassist search "我想研究人工智能辅助文献检索与Zotero协同管理" --out runs/demo
```

生成文件：

- `runs/demo/search_plan.json`
- `runs/demo/papers.json`
- `runs/demo/report.md`

## 本地可视化界面

```powershell
uv run litassist web
```

浏览器打开 `http://127.0.0.1:8765`。如果端口被占用，程序会自动换一个可用端口并在终端打印地址。

界面里可以选择是否使用 LLM 拆解研究问题，设置起始年份和新文献优先策略，配置 Semantic Scholar、Google Scholar via SerpApi、Web of Science 的 API key，筛选候选文献、只看可获取全文的条目、按新近/相关性/年份/引用排序，并选择部分文献导入 Zotero。Semantic Scholar 默认手动开启，检索结果会做本地缓存，并在额度偏低时自动切换到“仅缓存模式”。默认“导入选中项”是预演；勾选“写入 Zotero”后才会真实写入。

## LLM 研究需求拆解

默认使用离线规则拆解，不需要 API key。要启用 LLM 拆解，设置环境变量或编辑 `config.toml`。

OpenAI 示例：

```powershell
$env:OPENAI_API_KEY="你的 OpenAI API Key"
$env:LITASSIST_LLM_ENABLED="true"
uv run litassist plan "你的研究需求" --llm
```

DeepSeek 示例：

```powershell
$env:LITASSIST_LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
$env:DEEPSEEK_MODEL="deepseek-chat"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
$env:LITASSIST_LLM_ENABLED="true"
uv run litassist plan "你的研究需求" --llm
```

也可以在 `config.toml` 中配置：

```toml
[llm]
enabled = true
provider = "deepseek"
api_key = ""
model = "deepseek-chat"
endpoint = "https://api.deepseek.com/v1"
request_timeout_seconds = 45
```

建议把密钥放在 `DEEPSEEK_API_KEY` 环境变量里，而不是写入配置文件。或在前端勾选“使用 LLM 拆解研究问题”。没有可用 API key 时会自动回退到规则模式。

## 导入 Zotero

先编辑 `config.toml`：

```toml
[zotero]
library_id = "你的 userID 或 groupID"
library_type = "user"
api_key = "有写权限的 Zotero API Key"
collection_key = "可选：目标 collection key"
```

先预演：

```powershell
uv run litassist import-zotero runs/demo/papers.json --config config.toml --limit 10
```

确认后实际写入：

```powershell
uv run litassist import-zotero runs/demo/papers.json --config config.toml --limit 10 --apply
```

## 检索源策略

默认使用 API 友好的来源，并从近五年起按新文献优先检索：

- OpenAlex：开放学术图谱，适合宽检索、开放获取状态、引用量、DOI 补全
- Crossref：DOI 和出版元数据补全
- Semantic Scholar：摘要、引用、开放 PDF 线索；匿名请求容易限流，建议配置 API key
- Semantic Scholar：默认不勾选，优先节省月度 search 配额；同一查询 30 天内优先命中本地缓存
- Google Scholar：没有官方开放批量 API，本项目只支持通过 SerpApi 的 Google Scholar 引擎接入
- Web of Science：需要 Clarivate Web of Science API key

不做 Google Scholar 或 CNKI 的直接批量爬取。Google Scholar 没有官方开放检索 API，自动化访问容易触发封禁；CNKI 与机构订阅协议强相关，后续更适合做“题录导出解析 + Zotero translator 复用 + 本地合法附件匹配”。

更详细的平台接入边界见 `docs/SOURCE_STRATEGY.md`。

## 下一阶段

建议按这个顺序推进：

1. 完善 Web of Science Starter/Expanded API 的字段映射和错误诊断。
2. 增加 CNKI 题录导出解析与 `translators_CN` 复用。
3. 增加 Zotero Translation Server sidecar，用 URL 自动补元数据。
4. 增加任务历史、筛选记录和导入状态追踪。
