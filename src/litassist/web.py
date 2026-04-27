from __future__ import annotations

import json
import mimetypes
import shutil
import socket
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .config import (
    AppConfig,
    SemanticScholarConfig,
    load_config,
    save_llm_config,
    save_source_config,
)
from .models import Paper
from .pipeline import _build_search_plan, run_search
from .report import write_json, write_run
from .semantic_scholar_state import get_budget_state
from .zotero import import_papers


STATIC_DIR = Path(__file__).with_name("web_static")


class LiteratureWebServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        config: AppConfig,
        project_root: Path,
        config_path: Path | None = None,
    ) -> None:
        super().__init__(server_address, LiteratureRequestHandler)
        self.config = config
        self.project_root = project_root
        self.config_path = config_path or project_root / "config.toml"


class LiteratureRequestHandler(BaseHTTPRequestHandler):
    server: LiteratureWebServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                self._json({"ok": True})
                return
            if parsed.path == "/api/config":
                self._json(self._config_payload())
                return
            if parsed.path == "/api/archive":
                self._handle_archive_list()
                return
            if parsed.path.startswith("/api/archive/"):
                run_id = parsed.path.removeprefix("/api/archive/")
                self._handle_archive_detail(run_id)
                return
            if parsed.path.startswith("/runs/"):
                self._serve_project_file(parsed.path)
                return
            self._serve_static(parsed.path)
        except ValueError as exc:
            self._json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/plan":
                self._handle_plan(payload)
            elif parsed.path == "/api/search":
                self._handle_search(payload)
            elif parsed.path == "/api/import-zotero":
                self._handle_import_zotero(payload)
            elif parsed.path == "/api/config/llm":
                self._handle_update_llm_config(payload)
            elif parsed.path == "/api/config/sources":
                self._handle_update_source_config(payload)
            elif parsed.path == "/api/archive/delete":
                self._handle_archive_delete(payload)
            else:
                self._json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def _handle_plan(self, payload: dict[str, Any]) -> None:
        need = _required_text(payload, "need")
        use_llm = _optional_bool(payload, "useLlm")
        plan = _build_search_plan(
            need,
            config=self.server.config,
            zh_keywords=_list_of_text(payload.get("zhKeywords")),
            en_keywords=_list_of_text(payload.get("enKeywords")),
            use_llm=use_llm,
        )
        self._json({"plan": plan.to_dict()})

    def _handle_search(self, payload: dict[str, Any]) -> None:
        need = _required_text(payload, "need")
        sources = _list_of_text(payload.get("sources"))
        selected_sources = sources or list(self.server.config.general.enabled_sources)
        limit = int(
            payload.get("limit") or self.server.config.general.max_results_per_source
        )
        limit = max(1, min(limit, 1000))
        from_year = _optional_int(payload, "fromYear")
        prefer_recent = _optional_bool(payload, "preferRecent")
        use_llm = _optional_bool(payload, "useLlm")
        created_at = datetime.now()
        run = run_search(
            need,
            config=self.server.config,
            sources=selected_sources,
            limit=limit,
            zh_keywords=_list_of_text(payload.get("zhKeywords")),
            en_keywords=_list_of_text(payload.get("enKeywords")),
            use_llm=use_llm,
            from_year=from_year,
            prefer_recent=prefer_recent,
            state_root=self.server.project_root,
        )
        run_id, out_dir = _reserve_archive_run_dir(self.server.project_root, created_at)
        effective_prefer_recent = (
            self.server.config.general.prefer_recent
            if prefer_recent is None
            else prefer_recent
        )
        effective_use_llm = (
            self.server.config.llm.enabled if use_llm is None else use_llm
        )
        write_run(run, out_dir)
        write_json(
            out_dir / "run_meta.json",
            {
                "id": run_id,
                "createdAt": created_at.isoformat(),
                "need": need,
                "sources": selected_sources,
                "limit": limit,
                "fromYear": from_year,
                "preferRecent": effective_prefer_recent,
                "useLlm": effective_use_llm,
                "status": "partial" if run.errors else "success",
                "errors": run.errors,
                "paperCount": len(run.papers),
            },
        )
        self._json(
            {
                "runId": run_id,
                "outDir": str(out_dir),
                "plan": run.plan.to_dict(),
                "papers": [paper.to_dict() for paper in run.papers],
                "errors": run.errors,
                "sourceMeta": _serialize_source_meta(run.source_meta),
                "reportPath": str(out_dir / "report.md"),
                "reportUrl": f"/runs/web/{run_id}/report.md",
            }
        )

    def _handle_archive_list(self) -> None:
        archive_root = _archive_root(self.server.project_root)
        items = []
        if archive_root.exists():
            for run_dir in sorted(archive_root.iterdir(), reverse=True):
                if not run_dir.is_dir():
                    continue
                summary = _load_archive_summary(run_dir)
                if summary:
                    items.append(summary)
        self._json({"items": items})

    def _handle_archive_detail(self, run_id: str) -> None:
        run_dir = _resolve_archive_dir(self.server.project_root, run_id)
        if not run_dir.exists() or not run_dir.is_dir():
            self._json({"error": "Archive not found"}, status=HTTPStatus.NOT_FOUND)
            return
        detail = _load_archive_detail(run_dir)
        if detail is None:
            self._json({"error": "Archive not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._json({"item": detail})

    def _handle_archive_delete(self, payload: dict[str, Any]) -> None:
        run_id = _required_text(payload, "runId")
        run_dir = _resolve_archive_dir(self.server.project_root, run_id)
        if not run_dir.exists() or not run_dir.is_dir():
            raise ValueError("archive run not found")
        shutil.rmtree(run_dir)
        self._json({"ok": True, "runId": run_id})

    def _handle_import_zotero(self, payload: dict[str, Any]) -> None:
        papers_payload = payload.get("papers")
        if not isinstance(papers_payload, list):
            raise ValueError("papers must be a list")
        papers = [Paper(**item) for item in papers_payload]
        limit = payload.get("limit")
        result = import_papers(
            papers,
            self.server.config.zotero,
            limit=int(limit) if limit else None,
            apply=bool(payload.get("apply")),
        )
        self._json({"result": asdict(result)})

    def _handle_update_llm_config(self, payload: dict[str, Any]) -> None:
        provider = _optional_text(
            payload,
            "provider",
            default=self.server.config.llm.provider,
        )
        provider = provider.lower()
        if provider not in {"openai", "deepseek"}:
            raise ValueError("provider must be openai or deepseek")

        api_key = payload.get("apiKey")
        if api_key is not None and not isinstance(api_key, str):
            raise ValueError("apiKey must be text")
        enabled = _optional_bool(payload, "enabled")
        clear_api_key = _optional_bool(payload, "clearApiKey") or False

        timeout = payload.get("requestTimeoutSeconds")
        timeout_seconds = (
            self.server.config.llm.request_timeout_seconds
            if timeout is None or timeout == ""
            else float(timeout)
        )
        if timeout_seconds <= 0:
            raise ValueError("requestTimeoutSeconds must be positive")

        values: dict[str, Any] = {
            "provider": provider,
            "model": _optional_text(payload, "model", default=_default_model(provider)),
            "endpoint": _optional_text(
                payload,
                "endpoint",
                default=_default_endpoint(provider),
            ),
            "request_timeout_seconds": timeout_seconds,
        }
        if enabled is not None:
            values["enabled"] = enabled
        if clear_api_key:
            values["api_key"] = ""
        elif api_key and api_key.strip():
            values["api_key"] = api_key.strip()

        self.server.config = save_llm_config(
            self.server.config_path,
            values,
            preserve_empty_api_key=not clear_api_key,
        )
        self._json(self._config_payload())

    def _handle_update_source_config(self, payload: dict[str, Any]) -> None:
        from_year = _optional_int(payload, "fromYear")
        if from_year is not None and not 1900 <= from_year <= 2100:
            raise ValueError("fromYear must be between 1900 and 2100")
        prefer_recent = _optional_bool(payload, "preferRecent")

        values: dict[str, Any] = {
            "from_year": from_year,
            "semantic_scholar": {
                **_api_key_update(payload, "semanticScholar"),
                **_numeric_updates(
                    payload,
                    {
                        "monthly_search_budget": "semanticScholarMonthlySearchBudget",
                        "cache_ttl_days": "semanticScholarCacheTtlDays",
                        "warning_remaining": "semanticScholarWarningRemaining",
                        "cache_only_remaining": "semanticScholarCacheOnlyRemaining",
                    },
                ),
            },
            "web_of_science": _api_key_update(payload, "webOfScience"),
            "google_scholar": _api_key_update(payload, "googleScholar"),
        }
        if prefer_recent is not None:
            values["prefer_recent"] = prefer_recent
        _validate_semantic_budget_updates(
            values["semantic_scholar"],
            self.server.config.semantic_scholar,
        )
        web_endpoint = _optional_text(payload, "webOfScienceEndpoint")
        google_endpoint = _optional_text(payload, "googleScholarEndpoint")
        if web_endpoint:
            values["web_of_science"]["endpoint"] = web_endpoint
        if google_endpoint:
            values["google_scholar"]["endpoint"] = google_endpoint

        self.server.config = save_source_config(self.server.config_path, values)
        self._json(self._config_payload())

    def _config_payload(self) -> dict[str, Any]:
        general = self.server.config.general
        llm = self.server.config.llm
        semantic_budget = get_budget_state(
            self.server.project_root,
            self.server.config.semantic_scholar,
        )
        return {
            "configPath": str(self.server.config_path),
            "general": {
                "fromYear": general.from_year,
                "preferRecent": general.prefer_recent,
                "maxResultsPerSource": general.max_results_per_source,
                "enabledSources": list(general.enabled_sources),
            },
            "llm": {
                "enabled": llm.enabled,
                "provider": llm.provider,
                "model": llm.model,
                "endpoint": llm.endpoint,
                "requestTimeoutSeconds": llm.request_timeout_seconds,
                "hasApiKey": bool(llm.api_key),
            },
            "sources": {
                "openalex": {
                    "label": "OpenAlex",
                    "configured": True,
                    "requiresKey": False,
                },
                "crossref": {
                    "label": "Crossref",
                    "configured": True,
                    "requiresKey": False,
                },
                "semantic_scholar": {
                    "label": "Semantic Scholar",
                    "configured": bool(self.server.config.semantic_scholar.api_key),
                    "requiresKey": True,
                    "monthlySearchBudget": semantic_budget.monthly_search_budget,
                    "usedThisMonth": semantic_budget.used_this_month,
                    "remainingThisMonth": semantic_budget.remaining_this_month,
                    "cacheTtlDays": semantic_budget.cache_ttl_days,
                    "warningRemaining": semantic_budget.warning_remaining,
                    "cacheOnlyRemaining": semantic_budget.cache_only_remaining,
                    "budgetStatus": semantic_budget.budget_status,
                },
                "google_scholar": {
                    "label": "Google Scholar via SerpApi",
                    "configured": bool(self.server.config.google_scholar.api_key),
                    "requiresKey": True,
                    "endpoint": self.server.config.google_scholar.endpoint,
                },
                "web_of_science": {
                    "label": "Web of Science",
                    "configured": bool(self.server.config.web_of_science.api_key),
                    "requiresKey": True,
                    "endpoint": self.server.config.web_of_science.endpoint,
                },
            },
        }

    def _serve_static(self, request_path: str) -> None:
        relative = (
            "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        )
        relative = unquote(relative)
        target = (STATIC_DIR / relative).resolve()
        static_root = STATIC_DIR.resolve()
        if static_root not in target.parents and target != static_root:
            self._json({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not target.exists() or not target.is_file():
            target = STATIC_DIR / "index.html"
        content_type = (
            mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        )
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_project_file(self, request_path: str) -> None:
        relative = unquote(request_path.removeprefix("/runs/"))
        runs_root = _runs_root(self.server.project_root)
        target = (runs_root / relative).resolve()
        if runs_root not in target.parents and target != runs_root:
            self._json({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not target.exists() or not target.is_file():
            self._json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "text/plain"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _json(
        self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: str | Path | None = None,
    project_root: str | Path | None = None,
) -> str:
    root = Path(project_root or Path.cwd()).resolve()
    resolved_config_path = (
        Path(config_path).resolve() if config_path else root / "config.toml"
    )
    config = load_config(resolved_config_path)
    server = LiteratureWebServer(
        (host, port),
        config=config,
        project_root=root,
        config_path=resolved_config_path,
    )
    url = f"http://{host}:{server.server_port}"
    print(f"Literature Search Assistant running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return url


def find_free_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex((host, preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def _optional_text(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text")
    value = value.strip()
    return value or default


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _optional_bool(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{key} must be a boolean")


def _api_key_update(payload: dict[str, Any], prefix: str) -> dict[str, str | None]:
    api_key_field = f"{prefix}ApiKey"
    clear_field = f"clear{prefix[0].upper()}{prefix[1:]}ApiKey"
    api_key = payload.get(api_key_field)
    if api_key is not None and not isinstance(api_key, str):
        raise ValueError(f"{api_key_field} must be text")
    if bool(payload.get(clear_field)):
        return {"api_key": ""}
    if api_key and api_key.strip():
        return {"api_key": api_key.strip()}
    return {}


def _numeric_updates(
    payload: dict[str, Any],
    keys: dict[str, str],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for config_key, payload_key in keys.items():
        value = _optional_int(payload, payload_key)
        if value is not None:
            result[config_key] = value
    return result


def _serialize_source_meta(
    source_meta: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    serialized: dict[str, dict[str, Any]] = {}
    for source, meta in source_meta.items():
        serialized[source] = {
            "usedCache": bool(meta.get("used_cache")),
            "budgetStatus": meta.get("budget_status") or "",
            "remainingThisMonth": meta.get("remaining_this_month"),
            "warningMessage": meta.get("warning_message") or "",
            "queryRoundCount": meta.get("query_round_count")
            if meta.get("query_round_count") is not None
            else len(meta.get("query_rounds") or []),
            "successfulRounds": meta.get("successful_rounds", 0),
            "retrievedBeforeDedupe": meta.get("retrieved_before_dedupe"),
            "uniqueBeforeDedupe": _serialized_unique_before_dedupe(meta),
            "queryRounds": list(meta.get("query_rounds") or []),
            "roundErrors": [
                _serialize_round_error(item)
                for item in meta.get("round_errors") or []
                if isinstance(item, dict)
            ],
            "roundStats": [
                _serialize_round_stat(item)
                for item in meta.get("round_stats") or []
                if isinstance(item, dict)
            ],
        }
    return serialized


def _serialized_unique_before_dedupe(meta: dict[str, Any]) -> Any:
    if meta.get("unique_before_dedupe") is not None:
        return meta.get("unique_before_dedupe")
    for item in reversed(meta.get("round_stats") or []):
        if isinstance(item, dict) and item.get("cumulative_unique_count") is not None:
            return item.get("cumulative_unique_count")
    return None


def _serialize_round_error(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "round": meta.get("round"),
        "query": meta.get("query") or "",
        "error": meta.get("error") or "",
    }


def _serialize_round_stat(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "round": meta.get("round"),
        "query": meta.get("query") or "",
        "limit": meta.get("limit"),
        "retrievedCount": meta.get("retrieved_count", 0),
        "newUniqueCount": meta.get("new_unique_count", 0),
        "cumulativeUniqueCount": meta.get("cumulative_unique_count", 0),
        "error": meta.get("error") or "",
    }


def _archive_root(project_root: Path) -> Path:
    return (_runs_root(project_root) / "web").resolve()


def _runs_root(project_root: Path) -> Path:
    return (project_root / "runs").resolve()


def _reserve_archive_run_dir(
    project_root: Path,
    created_at: datetime,
) -> tuple[str, Path]:
    archive_root = _archive_root(project_root)
    archive_root.mkdir(parents=True, exist_ok=True)
    base_run_id = created_at.strftime("%Y%m%d-%H%M%S")
    suffix = 1
    while True:
        run_id = base_run_id if suffix == 1 else f"{base_run_id}-{suffix}"
        run_dir = archive_root / run_id
        try:
            run_dir.mkdir()
        except FileExistsError:
            suffix += 1
            continue
        return run_id, run_dir


def _resolve_archive_dir(project_root: Path, run_id: str) -> Path:
    archive_root = _archive_root(project_root)
    target = (archive_root / run_id).resolve()
    if archive_root not in target.parents:
        raise ValueError("invalid archive path")
    return target


def _load_archive_summary(run_dir: Path) -> dict[str, Any] | None:
    plan = _read_json_file(run_dir / "search_plan.json")
    if not isinstance(plan, dict):
        return None
    meta = _read_json_file(run_dir / "run_meta.json")
    papers = _read_json_file(run_dir / "papers.json")
    paper_count = (
        len(papers)
        if isinstance(papers, list)
        else int(meta.get("paperCount") or 0)
        if isinstance(meta, dict)
        else 0
    )
    return {
        "id": run_dir.name,
        "title": _archive_title(plan.get("need")),
        "need": plan.get("need") or "未命名任务",
        "createdAt": _archive_created_at(run_dir, meta),
        "zhKeywords": _list_text_field(plan.get("zh_keywords")),
        "enKeywords": _list_text_field(plan.get("en_keywords")),
        "sources": _archive_sources(plan, meta),
        "paperCount": paper_count,
        "status": _archive_status(meta, paper_count),
        "planner": plan.get("planner") or "rules",
        "fromYear": meta.get("fromYear") if isinstance(meta, dict) else None,
        "limit": meta.get("limit") if isinstance(meta, dict) else None,
        "preferRecent": meta.get("preferRecent") if isinstance(meta, dict) else None,
        "useLlm": (
            meta.get("useLlm")
            if isinstance(meta, dict) and "useLlm" in meta
            else plan.get("planner") == "llm"
        ),
        "reportUrl": f"/runs/web/{run_dir.name}/report.md",
    }


def _load_archive_detail(run_dir: Path) -> dict[str, Any] | None:
    summary = _load_archive_summary(run_dir)
    if summary is None:
        return None
    plan = _read_json_file(run_dir / "search_plan.json")
    meta = _read_json_file(run_dir / "run_meta.json")
    papers = _read_json_file(run_dir / "papers.json")
    source_meta = _read_json_file(run_dir / "source_meta.json")
    if not isinstance(plan, dict):
        return None
    summary.update(
        {
            "plan": plan,
            "papers": papers if isinstance(papers, list) else [],
            "sourceMeta": (
                _serialize_source_meta(source_meta)
                if isinstance(source_meta, dict)
                else {}
            ),
            "errors": meta.get("errors", {}) if isinstance(meta, dict) else {},
        }
    )
    return summary


def _read_json_file(path: Path) -> Any:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _archive_title(need: Any) -> str:
    if not isinstance(need, str) or not need.strip():
        return "未命名任务"
    compact = " ".join(need.split())
    return compact[:36] + ("..." if len(compact) > 36 else "")


def _archive_created_at(run_dir: Path, meta: Any) -> str:
    if isinstance(meta, dict) and isinstance(meta.get("createdAt"), str):
        return meta["createdAt"]
    try:
        parsed = datetime.strptime(run_dir.name, "%Y%m%d-%H%M%S")
        return parsed.isoformat()
    except ValueError:
        return datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat()


def _archive_sources(plan: dict[str, Any], meta: Any) -> list[str]:
    if isinstance(meta, dict) and isinstance(meta.get("sources"), list):
        return _list_text_field(meta.get("sources"))
    queries = plan.get("queries")
    if isinstance(queries, dict):
        return [str(key) for key in queries.keys()]
    return []


def _archive_status(meta: Any, paper_count: int) -> str:
    status_map = {
        "success": "成功",
        "partial": "部分完成",
        "failed": "失败",
        "running": "进行中",
        "interrupted": "中断",
    }
    if isinstance(meta, dict):
        raw = str(meta.get("status") or "").strip().lower()
        if raw in status_map:
            return status_map[raw]
    return "已归档" if paper_count else "暂无结果"


def _list_text_field(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _validate_semantic_budget_updates(
    values: dict[str, Any],
    current: SemanticScholarConfig,
) -> None:
    merged = {
        "monthly_search_budget": values.get(
            "monthly_search_budget",
            current.monthly_search_budget,
        ),
        "cache_ttl_days": values.get("cache_ttl_days", current.cache_ttl_days),
        "warning_remaining": values.get(
            "warning_remaining",
            current.warning_remaining,
        ),
        "cache_only_remaining": values.get(
            "cache_only_remaining",
            current.cache_only_remaining,
        ),
    }
    for key in (
        "monthly_search_budget",
        "cache_ttl_days",
        "warning_remaining",
        "cache_only_remaining",
    ):
        if int(merged[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    if int(merged["warning_remaining"]) < int(merged["cache_only_remaining"]):
        raise ValueError(
            "warning_remaining must be greater than or equal to cache_only_remaining"
        )


def _list_of_text(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("keyword and source values must be lists")
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _default_model(provider: str) -> str:
    if provider == "deepseek":
        return "deepseek-chat"
    return "gpt-4.1-mini"


def _default_endpoint(provider: str) -> str:
    if provider == "deepseek":
        return "https://api.deepseek.com/v1"
    return "https://api.openai.com/v1/responses"
