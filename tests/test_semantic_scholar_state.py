from __future__ import annotations

from datetime import date, datetime, timedelta

from litassist.config import SemanticScholarConfig
from litassist.semantic_scholar_state import (
    build_cache_key,
    get_budget_state,
    load_cached_results,
    normalize_query,
    record_successful_search,
    save_cached_results,
)


def test_cache_key_is_stable_for_normalized_query():
    left = build_cache_key(
        "Large   Language Models ",
        from_year=2023,
        limit=10,
        requested_fields="title,authors",
    )
    right = build_cache_key(
        "large language models",
        from_year=2023,
        limit=10,
        requested_fields="title,authors",
    )

    assert normalize_query("Large   Language Models ") == "large language models"
    assert left == right


def test_cached_results_expire_after_ttl(tmp_path):
    cache_key = build_cache_key("llm", 2023, 10, "title")
    now = datetime(2026, 4, 23, 10, 0, 0)
    save_cached_results(
        tmp_path,
        cache_key=cache_key,
        results=[{"title": "Cached"}],
        now=now,
    )

    assert load_cached_results(tmp_path, cache_key, ttl_days=30, now=now) == [
        {"title": "Cached"}
    ]
    assert (
        load_cached_results(
            tmp_path,
            cache_key,
            ttl_days=30,
            now=now + timedelta(days=31),
        )
        is None
    )


def test_budget_state_tracks_successful_searches_by_month(tmp_path):
    config = SemanticScholarConfig(monthly_search_budget=250)
    today = date(2026, 4, 23)

    record_successful_search(tmp_path, today=today)
    record_successful_search(tmp_path, today=today)

    state = get_budget_state(tmp_path, config, today=today)

    assert state.used_this_month == 2
    assert state.remaining_this_month == 248
    assert state.budget_status == "ok"


def test_corrupted_cached_results_are_ignored(tmp_path):
    cache_key = build_cache_key("llm", 2023, 10, "title")
    cache_path = tmp_path / "runs" / "cache" / "semantic_scholar" / f"{cache_key}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text('{"created_at": "broken"', encoding="utf-8")

    assert load_cached_results(tmp_path, cache_key, ttl_days=30) is None


def test_corrupted_usage_file_falls_back_to_empty_state(tmp_path):
    usage_path = tmp_path / "runs" / "state" / "semantic_scholar_usage.json"
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    usage_path.write_text("not-json", encoding="utf-8")

    state = get_budget_state(tmp_path, SemanticScholarConfig(monthly_search_budget=10))

    assert state.used_this_month == 0
    assert state.remaining_this_month == 10
