# Literature Search Assistant

一个面向 Zotero 的文献检索 MVP：输入研究需求，生成中英文关键词和数据库检索式，调用开放学术 API 检索文献，去重、排序、导出报告，并可导入 Zotero。

当前版本先实现稳定链路：

- 需求拆解和中英文关键词生成
- OpenAlex、Crossref、Semantic Scholar 检索
- DOI / 标题去重
- Markdown + JSON 报告
- Zotero Web API / pyzotero 导入
- Web of Science 与 CNKI 作为后续适配方向保留设计

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

MVP 默认使用 API 友好的来源：

- OpenAlex：开放学术图谱，适合宽检索、开放获取状态、引用量、DOI 补全
- Crossref：DOI 和出版元数据补全
- Semantic Scholar：摘要、引用、开放 PDF 线索

不把 Google Scholar 或 CNKI 的批量爬取作为第一阶段核心。Google Scholar 没有官方开放检索 API，自动化访问容易触发封禁；CNKI 与机构订阅协议强相关，后续更适合做“题录导出解析 + Zotero translator 复用 + 本地合法附件匹配”。

更详细的平台接入边界见 `docs/SOURCE_STRATEGY.md`。

## 下一阶段

建议按这个顺序推进：

1. 接入 LLM 需求拆解模块，替换当前规则式关键词生成。
2. 接入 Web of Science Starter/Expanded API。
3. 增加 CNKI 题录导出解析与 `translators_CN` 复用。
4. 增加 Zotero Translation Server sidecar，用 URL 自动补元数据。
5. 做本地 Web UI：任务列表、筛选确认、导入状态。
