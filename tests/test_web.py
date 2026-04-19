from __future__ import annotations

import threading
from pathlib import Path

import httpx

from litassist.config import AppConfig
from litassist.web import LiteratureWebServer


def test_web_health_and_plan(tmp_path: Path):
    server = LiteratureWebServer(("127.0.0.1", 0), AppConfig(), tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            health = client.get(f"{base_url}/api/health")
            plan = client.post(
                f"{base_url}/api/plan",
                json={"need": "人工智能辅助文献检索 Zotero 文献管理"},
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert health.json() == {"ok": True}
    assert plan.status_code == 200
    assert "人工智能" in plan.json()["plan"]["zh_keywords"]
