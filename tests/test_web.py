from __future__ import annotations

import threading
from pathlib import Path

import httpx

from litassist.config import AppConfig, load_config
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


def test_web_updates_llm_config_without_returning_api_key(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[zotero]\nlibrary_id = "123"\nlibrary_type = "user"\n',
        encoding="utf-8",
    )
    server = LiteratureWebServer(
        ("127.0.0.1", 0),
        load_config(config_path),
        tmp_path,
        config_path=config_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            saved = client.post(
                f"{base_url}/api/config/llm",
                json={
                    "enabled": True,
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "endpoint": "https://api.deepseek.com/v1",
                    "apiKey": "test-secret",
                    "requestTimeoutSeconds": 30,
                },
            )
            loaded = client.get(f"{base_url}/api/config")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert saved.status_code == 200
    assert saved.json()["llm"]["hasApiKey"] is True
    assert "apiKey" not in saved.json()["llm"]
    assert loaded.json()["llm"]["provider"] == "deepseek"
    text = config_path.read_text(encoding="utf-8")
    assert '[zotero]' in text
    assert 'api_key = "test-secret"' in text


def test_web_updates_source_config_without_returning_api_keys(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    server = LiteratureWebServer(
        ("127.0.0.1", 0),
        load_config(config_path),
        tmp_path,
        config_path=config_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            saved = client.post(
                f"{base_url}/api/config/sources",
                json={
                    "fromYear": 2022,
                    "preferRecent": True,
                    "semanticScholarApiKey": "semantic-secret",
                    "googleScholarApiKey": "serp-secret",
                    "googleScholarEndpoint": "https://serpapi.com/search.json",
                    "webOfScienceApiKey": "wos-secret",
                    "webOfScienceEndpoint": "https://api.clarivate.com/apis/wos-starter/v1/documents",
                },
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    payload = saved.json()
    assert saved.status_code == 200
    assert payload["general"]["fromYear"] == 2022
    assert payload["sources"]["semantic_scholar"]["configured"] is True
    assert payload["sources"]["google_scholar"]["configured"] is True
    assert payload["sources"]["web_of_science"]["configured"] is True
    assert "apiKey" not in str(payload)
    text = config_path.read_text(encoding="utf-8")
    assert 'api_key = "semantic-secret"' in text
    assert 'api_key = "serp-secret"' in text
    assert 'api_key = "wos-secret"' in text
