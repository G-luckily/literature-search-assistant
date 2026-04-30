from __future__ import annotations

import json
import logging
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

logger = logging.getLogger(__name__)

from . import db
from .config import (
    AppConfig,
    load_config,
    save_llm_config,
    save_source_config,
)
from .file_analyzer import FileAnalysisError, analyze_file
from .models import Paper
from .pipeline import _build_search_plan, run_search
from .report import write_json, write_run
from .semantic_scholar_state import get_budget_state
from .web_helpers import (
    api_key_update,
    create_timestamped_run_dir,
    default_endpoint,
    default_model,
    list_of_text,
    load_archive_detail,
    load_archive_summary,
    numeric_updates,
    optional_bool,
    optional_int,
    optional_text,
    resolve_archive_dir,
    required_text,
    serialize_source_meta,
    validate_semantic_budget_updates,
)
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

    # ── Routing ──────────────────────────────────────────────────

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
            elif parsed.path == "/api/analyze-file":
                self._handle_analyze_file(payload)
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
        logger.info("%s - %s", self.address_string(), format % args)

    # ── Route handlers ───────────────────────────────────────────

    def _handle_plan(self, payload: dict[str, Any]) -> None:
        need = required_text(payload, "need")
        use_llm = optional_bool(payload, "useLlm")
        file_context = optional_text(payload, "fileContext")
        search_dimensions = payload.get("searchDimensions")
        suggested_queries = payload.get("suggestedQueries")
        plan = _build_search_plan(
            need,
            config=self.server.config,
            zh_keywords=list_of_text(payload.get("zhKeywords")),
            en_keywords=list_of_text(payload.get("enKeywords")),
            use_llm=use_llm,
            file_context=file_context,
            search_dimensions=search_dimensions,
            suggested_queries=suggested_queries,
        )
        self._json({"plan": plan.to_dict()})

    def _handle_search(self, payload: dict[str, Any]) -> None:
        need = required_text(payload, "need")
        sources = list_of_text(payload.get("sources"))
        selected_sources = sources or list(self.server.config.general.enabled_sources)
        limit = int(
            payload.get("limit") or self.server.config.general.max_results_per_source
        )
        limit = max(1, min(limit, 1000))
        from_year = optional_int(payload, "fromYear")
        prefer_recent = optional_bool(payload, "preferRecent")
        use_llm = optional_bool(payload, "useLlm")
        file_context = optional_text(payload, "fileContext")
        search_dimensions = payload.get("searchDimensions")
        suggested_queries = payload.get("suggestedQueries")
        created_at = datetime.now()
        run = run_search(
            need,
            config=self.server.config,
            sources=selected_sources,
            limit=limit,
            zh_keywords=list_of_text(payload.get("zhKeywords")),
            en_keywords=list_of_text(payload.get("enKeywords")),
            use_llm=use_llm,
            from_year=from_year,
            prefer_recent=prefer_recent,
            state_root=self.server.project_root,
            file_context=file_context,
            search_dimensions=search_dimensions,
            suggested_queries=suggested_queries,
        )
        run_id, out_dir = create_timestamped_run_dir(
            self.server.project_root, created_at
        )
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
        # Persist archive metadata in SQLite
        db.init(self.server.project_root / "runs" / "litassist.db")
        db.archive_save(
            run_id=run_id,
            need=need,
            status="partial" if run.errors else "success",
            sources=selected_sources,
            zh_keywords=list_of_text(payload.get("zhKeywords")),
            en_keywords=list_of_text(payload.get("enKeywords")),
            from_year=from_year,
            limit_count=limit,
            prefer_recent=effective_prefer_recent,
            use_llm=effective_use_llm,
            plan=run.plan.to_dict(),
            papers=[paper.to_dict() for paper in run.papers],
            errors=run.errors,
            source_meta=serialize_source_meta(run.source_meta),
            created_at=created_at.isoformat(),
        )
        self._json(
            {
                "runId": run_id,
                "outDir": str(out_dir),
                "plan": run.plan.to_dict(),
                "papers": [paper.to_dict() for paper in run.papers],
                "errors": run.errors,
                "sourceMeta": serialize_source_meta(run.source_meta),
                "reportPath": str(out_dir / "report.md"),
                "reportUrl": f"/runs/web/{run_id}/report.md",
            }
        )

    def _handle_archive_list(self) -> None:
        db.init(self.server.project_root / "runs" / "litassist.db")
        items = db.archive_list()
        # Add reportUrl field expected by frontend
        for item in items:
            item["reportUrl"] = f"/runs/web/{item['id']}/report.md"
        # Fallback: scan filesystem for pre-migration archives
        archive_root_dir = (
            self.server.project_root / "runs" / "web"
        ).resolve()
        sqlite_ids = {item["id"] for item in items}
        if archive_root_dir.exists():
            for run_dir in sorted(archive_root_dir.iterdir(), reverse=True):
                if not run_dir.is_dir() or run_dir.name in sqlite_ids:
                    continue
                summary = load_archive_summary(run_dir)
                if summary:
                    items.append(summary)
        self._json({"items": items})

    def _handle_archive_detail(self, run_id: str) -> None:
        db.init(self.server.project_root / "runs" / "litassist.db")
        detail = db.archive_get(run_id)
        if detail is not None:
            detail["reportUrl"] = f"/runs/web/{run_id}/report.md"
            self._json({"item": detail})
            return
        # Fallback to filesystem for pre-migration archives
        run_dir = resolve_archive_dir(self.server.project_root, run_id)
        if not run_dir.exists() or not run_dir.is_dir():
            self._json({"error": "Archive not found"}, status=HTTPStatus.NOT_FOUND)
            return
        detail = load_archive_detail(run_dir)
        if detail is None:
            self._json({"error": "Archive not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._json({"item": detail})

    def _handle_archive_delete(self, payload: dict[str, Any]) -> None:
        run_id = required_text(payload, "runId")
        db.init(self.server.project_root / "runs" / "litassist.db")
        db.archive_delete(run_id)
        run_dir = resolve_archive_dir(self.server.project_root, run_id)
        if run_dir.exists() and run_dir.is_dir():
            shutil.rmtree(run_dir)
        self._json({"ok": True, "runId": run_id})

    def _handle_analyze_file(self, payload: dict[str, Any]) -> None:
        filename = required_text(payload, "filename")
        content = required_text(payload, "content")
        mime_type = optional_text(payload, "mimeType", "application/octet-stream")
        # ~20MB raw file = ~26MB base64; reject larger to prevent OOM
        if len(content) > 26 * 1024 * 1024:
            raise ValueError("File content exceeds 20 MB limit.")
        result = analyze_file(
            filename,
            content,
            mime_type,
            self.server.config.llm,
        )
        self._json({
            "description": result.description,
            "keywordsZh": result.keywords_zh,
            "keywordsEn": result.keywords_en,
            "sourceText": result.source_text,
            "searchDimensions": result.search_dimensions,
            "suggestedQueries": result.suggested_queries,
        })

    def _handle_import_zotero(self, payload: dict[str, Any]) -> None:
        papers_payload = payload.get("papers")
        if not isinstance(papers_payload, list):
            raise ValueError("papers must be a list")
        known_fields = Paper.__dataclass_fields__
        papers = [
            Paper(**{k: v for k, v in item.items() if k in known_fields})
            for item in papers_payload
        ]
        limit = payload.get("limit")
        result = import_papers(
            papers,
            self.server.config.zotero,
            limit=int(limit) if limit else None,
            apply=bool(payload.get("apply")),
        )
        self._json({"result": asdict(result)})

    def _handle_update_llm_config(self, payload: dict[str, Any]) -> None:
        provider = optional_text(
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
        enabled = optional_bool(payload, "enabled")
        clear_api_key = optional_bool(payload, "clearApiKey") or False

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
            "model": optional_text(payload, "model", default=default_model(provider)),
            "endpoint": optional_text(
                payload,
                "endpoint",
                default=default_endpoint(provider),
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
        from_year = optional_int(payload, "fromYear")
        if from_year is not None and not 1900 <= from_year <= 2100:
            raise ValueError("fromYear must be between 1900 and 2100")
        prefer_recent = optional_bool(payload, "preferRecent")

        values: dict[str, Any] = {
            "from_year": from_year,
            "semantic_scholar": {
                **api_key_update(payload, "semanticScholar"),
                **numeric_updates(
                    payload,
                    {
                        "monthly_search_budget": "semanticScholarMonthlySearchBudget",
                        "cache_ttl_days": "semanticScholarCacheTtlDays",
                        "warning_remaining": "semanticScholarWarningRemaining",
                        "cache_only_remaining": "semanticScholarCacheOnlyRemaining",
                    },
                ),
            },
            "web_of_science": api_key_update(payload, "webOfScience"),
            "google_scholar": api_key_update(payload, "googleScholar"),
            "zotero": {
                "library_id": payload.get("zoteroLibraryId", "").strip(),
                "api_key": payload.get("zoteroApiKey", "").strip(),
                "library_type": payload.get("zoteroLibraryType", "user").strip(),
                "collection_key": payload.get("zoteroCollectionKey", "").strip(),
            },
        }
        if prefer_recent is not None:
            values["prefer_recent"] = prefer_recent
        validate_semantic_budget_updates(
            values["semantic_scholar"],
            self.server.config.semantic_scholar,
        )
        web_endpoint = optional_text(payload, "webOfScienceEndpoint")
        google_endpoint = optional_text(payload, "googleScholarEndpoint")
        if web_endpoint:
            values["web_of_science"]["endpoint"] = web_endpoint
        if google_endpoint:
            values["google_scholar"]["endpoint"] = google_endpoint

        self.server.config = save_source_config(self.server.config_path, values)
        self._json(self._config_payload())

    # ── Config payload ───────────────────────────────────────────

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
                "zotero": {
                    "label": "Zotero 文献库",
                    "configured": bool(self.server.config.zotero.api_key and self.server.config.zotero.library_id),
                    "requiresKey": True,
                    "libraryId": self.server.config.zotero.library_id,
                    "libraryType": self.server.config.zotero.library_type,
                    "hasCollectionKey": bool(self.server.config.zotero.collection_key),
                },
            },
        }

    # ── Static file serving ──────────────────────────────────────

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
        if content_type == "text/html":
            self.send_header(
                "Cache-Control", "no-cache, no-store, must-revalidate"
            )
        elif content_type in ("text/css", "application/javascript"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(data)

    def _serve_project_file(self, request_path: str) -> None:
        relative = unquote(request_path.removeprefix("/runs/"))
        runs_root = (self.server.project_root / "runs").resolve()
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

    # ── I/O helpers ──────────────────────────────────────────────

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


# ── Server entry point ───────────────────────────────────────────


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: str | Path | None = None,
    project_root: str | Path | None = None,
    log_level: str = "INFO",
) -> str:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
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
    logger.info("Literature Search Assistant running at %s", url)
    logger.info("Press Ctrl+C to stop.")
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
