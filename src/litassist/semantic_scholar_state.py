"""Semantic Scholar API state management — cache, budget, usage tracking.

Cache and usage data are stored in SQLite (via db.py). The cache key
and normalization logic remain here; storage details are delegated.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import db
from .config import SemanticScholarConfig
from .models import SourceMeta


API_VERSION = "graph/v1/paper/search"
CACHE_MAX_ENTRIES = 5000


@dataclass(slots=True)
class SemanticScholarBudgetState:
    monthly_search_budget: int
    used_this_month: int
    remaining_this_month: int
    cache_ttl_days: int
    warning_remaining: int
    cache_only_remaining: int
    budget_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_cache_key(
    query: str,
    from_year: int | None,
    limit: int,
    requested_fields: str,
    api_version: str = API_VERSION,
) -> str:
    normalized_query = normalize_query(query)
    payload = "|".join(
        [
            normalized_query,
            str(from_year or ""),
            str(limit),
            requested_fields,
            api_version,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def load_cached_results(
    state_root: str | Path,
    cache_key: str,
    ttl_days: int,
    now: datetime | None = None,
) -> list[dict[str, Any]] | None:
    db_path = _db_path(state_root)
    db.init(db_path)
    return db.cache_get(cache_key, now=now)


def save_cached_results(
    state_root: str | Path,
    cache_key: str,
    results: list[dict[str, Any]],
    now: datetime | None = None,
) -> None:
    db_path = _db_path(state_root)
    db.init(db_path)
    db.cache_set(cache_key, results, ttl_days=30, now=now)
    db.cache_evict(max_entries=CACHE_MAX_ENTRIES)


def get_budget_state(
    state_root: str | Path,
    config: SemanticScholarConfig,
    today: date | None = None,
) -> SemanticScholarBudgetState:
    db_path = _db_path(state_root)
    db.init(db_path)
    current = today or date.today()
    month_key = _month_key(current)
    used = db.usage_get("semantic_scholar", month_key)
    remaining = max(config.monthly_search_budget - used, 0)
    if remaining <= config.cache_only_remaining:
        budget_status = "cache_only"
    elif remaining <= config.warning_remaining:
        budget_status = "warning"
    else:
        budget_status = "ok"
    return SemanticScholarBudgetState(
        monthly_search_budget=config.monthly_search_budget,
        used_this_month=used,
        remaining_this_month=remaining,
        cache_ttl_days=config.cache_ttl_days,
        warning_remaining=config.warning_remaining,
        cache_only_remaining=config.cache_only_remaining,
        budget_status=budget_status,
    )


def record_successful_search(
    state_root: str | Path,
    today: date | None = None,
) -> None:
    db_path = _db_path(state_root)
    db.init(db_path)
    current = today or date.today()
    month_key = _month_key(current)
    db.usage_increment("semantic_scholar", month_key)


def build_source_meta(
    budget_state: SemanticScholarBudgetState,
    used_cache: bool,
) -> SourceMeta:
    return SourceMeta(
        used_cache=used_cache,
        budget_status=budget_state.budget_status,
        remaining_this_month=budget_state.remaining_this_month,
        warning_message=budget_warning_message(budget_state, used_cache),
    )


def budget_warning_message(
    budget_state: SemanticScholarBudgetState,
    used_cache: bool = False,
) -> str:
    if budget_state.budget_status == "cache_only":
        if used_cache:
            return (
                "Semantic Scholar is in cache-only mode because the remaining monthly "
                "search budget is low."
            )
        return (
            "Semantic Scholar remaining monthly budget is low. This source is now in "
            "cache-only mode until next month or a higher budget is configured."
        )
    if budget_state.budget_status == "warning":
        return (
            f"Semantic Scholar monthly budget is low: "
            f"{budget_state.remaining_this_month} live searches remaining this month."
        )
    return ""


def _month_key(today: date) -> str:
    return today.strftime("%Y-%m")


def _db_path(state_root: str | Path) -> Path:
    return Path(state_root).resolve() / "runs" / "litassist.db"
