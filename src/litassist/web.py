from __future__ import annotations

import json
import mimetypes
import socket
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .config import AppConfig, load_config
from .models import Paper
from .pipeline import run_search
from .planner import build_plan
from .report import write_run
from .zotero import import_papers


STATIC_DIR = Path(__file__).with_name("web_static")


class LiteratureWebServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        config: AppConfig,
        project_root: Path,
    ) -> None:
        super().__init__(server_address, LiteratureRequestHandler)
        self.config = config
        self.project_root = project_root


class LiteratureRequestHandler(BaseHTTPRequestHandler):
    server: LiteratureWebServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"ok": True})
            return
        if parsed.path.startswith("/runs/"):
            self._serve_project_file(parsed.path)
            return
        self._serve_static(parsed.path)

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
        plan = build_plan(
            need,
            zh_keywords=_list_of_text(payload.get("zhKeywords")),
            en_keywords=_list_of_text(payload.get("enKeywords")),
        )
        self._json({"plan": plan.to_dict()})

    def _handle_search(self, payload: dict[str, Any]) -> None:
        need = _required_text(payload, "need")
        sources = _list_of_text(payload.get("sources"))
        limit = int(payload.get("limit") or self.server.config.general.max_results_per_source)
        limit = max(1, min(limit, 50))
        run = run_search(
            need,
            config=self.server.config,
            sources=sources or None,
            limit=limit,
            zh_keywords=_list_of_text(payload.get("zhKeywords")),
            en_keywords=_list_of_text(payload.get("enKeywords")),
        )
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = self.server.project_root / "runs" / "web" / run_id
        write_run(run, out_dir)
        self._json(
            {
                "runId": run_id,
                "outDir": str(out_dir),
                "plan": run.plan.to_dict(),
                "papers": [paper.to_dict() for paper in run.papers],
                "errors": run.errors,
                "reportPath": str(out_dir / "report.md"),
                "reportUrl": f"/runs/web/{run_id}/report.md",
            }
        )

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

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        relative = unquote(relative)
        target = (STATIC_DIR / relative).resolve()
        static_root = STATIC_DIR.resolve()
        if static_root not in target.parents and target != static_root:
            self._json({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not target.exists() or not target.is_file():
            target = STATIC_DIR / "index.html"
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_project_file(self, request_path: str) -> None:
        relative = unquote(request_path.lstrip("/"))
        target = (self.server.project_root / relative).resolve()
        root = self.server.project_root.resolve()
        if root not in target.parents and target != root:
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

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
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
    config = load_config(config_path)
    server = LiteratureWebServer((host, port), config=config, project_root=root)
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


def _list_of_text(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("keyword and source values must be lists")
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
