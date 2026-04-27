from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from litassist.config import AppConfig, load_config
from litassist.models import ResearchPlan
from litassist.pipeline import SearchRun
from litassist.web import LiteratureWebServer, _reserve_archive_run_dir


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
    assert "[zotero]" in text
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
                    "semanticScholarMonthlySearchBudget": 250,
                    "semanticScholarWarningRemaining": 50,
                    "semanticScholarCacheOnlyRemaining": 25,
                    "semanticScholarCacheTtlDays": 30,
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
    assert payload["sources"]["semantic_scholar"]["monthlySearchBudget"] == 250
    assert payload["sources"]["semantic_scholar"]["cacheTtlDays"] == 30
    assert payload["sources"]["semantic_scholar"]["budgetStatus"] == "ok"
    assert payload["sources"]["google_scholar"]["configured"] is True
    assert payload["sources"]["web_of_science"]["configured"] is True
    assert "apiKey" not in str(payload)
    text = config_path.read_text(encoding="utf-8")
    assert 'api_key = "semantic-secret"' in text
    assert 'api_key = "serp-secret"' in text
    assert 'api_key = "wos-secret"' in text


def test_web_search_serializes_source_meta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    def fake_run_search(*args, **kwargs):
        return SearchRun(
            plan=ResearchPlan(
                need="test",
                zh_keywords=["人工智能"],
                en_keywords=["artificial intelligence"],
                queries={"openalex": "test"},
            ),
            papers=[],
            errors={},
            source_meta={
                "semantic_scholar": {
                    "used_cache": True,
                    "budget_status": "warning",
                    "remaining_this_month": 42,
                    "warning_message": "budget low",
                    "query_round_count": 2,
                    "successful_rounds": 1,
                    "retrieved_before_dedupe": 5,
                    "unique_before_dedupe": 3,
                    "query_rounds": ["primary query", "secondary query"],
                    "round_errors": [
                        {
                            "round": 2,
                            "query": "secondary query",
                            "error": "rate limit",
                        }
                    ],
                    "round_stats": [
                        {
                            "round": 1,
                            "query": "primary query",
                            "limit": 8,
                            "retrieved_count": 5,
                            "new_unique_count": 3,
                            "cumulative_unique_count": 3,
                        },
                        {
                            "round": 2,
                            "query": "secondary query",
                            "limit": 5,
                            "retrieved_count": 0,
                            "new_unique_count": 0,
                            "cumulative_unique_count": 3,
                            "error": "rate limit",
                        },
                    ],
                }
            },
        )

    monkeypatch.setattr("litassist.web.run_search", fake_run_search)
    server = LiteratureWebServer(("127.0.0.1", 0), AppConfig(), tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.post(
                f"{base_url}/api/search",
                json={"need": "人工智能辅助文献检索"},
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    payload = response.json()
    assert payload["sourceMeta"]["semantic_scholar"]["usedCache"] is True
    assert payload["sourceMeta"]["semantic_scholar"]["budgetStatus"] == "warning"
    assert payload["sourceMeta"]["semantic_scholar"]["remainingThisMonth"] == 42
    assert payload["sourceMeta"]["semantic_scholar"]["queryRoundCount"] == 2
    assert payload["sourceMeta"]["semantic_scholar"]["successfulRounds"] == 1
    assert payload["sourceMeta"]["semantic_scholar"]["retrievedBeforeDedupe"] == 5
    assert payload["sourceMeta"]["semantic_scholar"]["uniqueBeforeDedupe"] == 3
    assert payload["sourceMeta"]["semantic_scholar"]["queryRounds"] == [
        "primary query",
        "secondary query",
    ]
    assert (
        payload["sourceMeta"]["semantic_scholar"]["roundErrors"][0]["error"]
        == "rate limit"
    )
    assert (
        payload["sourceMeta"]["semantic_scholar"]["roundStats"][0]["newUniqueCount"]
        == 3
    )


def test_web_blocks_path_traversal_outside_runs(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('[llm]\napi_key = "secret"\n', encoding="utf-8")
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
            response = client.get(f"{base_url}/runs/%2e%2e/config.toml")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert response.status_code == 400
    assert response.json()["error"] == "Invalid path"


def test_archive_run_dir_is_unique_with_same_second_timestamp(tmp_path: Path):
    created_at = datetime(2026, 4, 26, 12, 0, 0)

    first_run_id, first_dir = _reserve_archive_run_dir(tmp_path, created_at)
    second_run_id, second_dir = _reserve_archive_run_dir(tmp_path, created_at)

    assert first_run_id == "20260426-120000"
    assert second_run_id == "20260426-120000-2"
    assert first_dir.exists()
    assert second_dir.exists()


def test_web_search_records_effective_sources_and_llm_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    def fake_run_search(*args, **kwargs):
        return SearchRun(
            plan=ResearchPlan(
                need="test",
                zh_keywords=["人工智能"],
                en_keywords=["artificial intelligence"],
                queries={
                    "openalex": "test",
                    "crossref": "test",
                    "semantic_scholar": "test",
                },
                planner="llm",
            ),
            papers=[],
            errors={},
            source_meta={},
        )

    monkeypatch.setattr("litassist.web.run_search", fake_run_search)
    server = LiteratureWebServer(
        ("127.0.0.1", 0),
        AppConfig(),
        tmp_path,
    )
    server.config.llm.enabled = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with httpx.Client(timeout=5, trust_env=False) as client:
            response = client.post(
                f"{base_url}/api/search",
                json={"need": "人工智能辅助文献检索"},
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    payload = response.json()
    run_meta_path = tmp_path / "runs" / "web" / payload["runId"] / "run_meta.json"
    run_meta = json.loads(run_meta_path.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert run_meta["sources"] == ["openalex", "crossref", "semantic_scholar"]
    assert run_meta["useLlm"] is True
