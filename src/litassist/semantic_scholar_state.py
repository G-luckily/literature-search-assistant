from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from .config import SemanticScholarConfig
from .models import SourceMeta


API_VERSION = "graph/v1/paper/search"
STATE_IO_LOCK = Lock()


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
    cache_path = _cache_dir(state_root) / f"{cache_key}.json"
    payload = _read_json_object(cache_path)
    if payload is None:
        return None
    created_at_raw = payload.get("created_at")
    if not isinstance(created_at_raw, str):
        return None
    try:
        created_at = datetime.fromisoformat(created_at_raw)
    except ValueError:
        return None
    current = now or datetime.now()
    if current - created_at > timedelta(days=ttl_days):
        return None
    results = payload.get("results")
    return results if isinstance(results, list) else None


def save_cached_results(
    state_root: str | Path,
    cache_key: str,
    results: list[dict[str, Any]],
    now: datetime | None = None,
) -> None:
    cache_dir = _cache_dir(state_root)
    cache_path = cache_dir / f"{cache_key}.json"
    payload = {
        "created_at": (now or datetime.now()).isoformat(),
        "results": results,
    }
    _write_json_object(cache_path, payload)


def get_budget_state(
    state_root: str | Path,
    config: SemanticScholarConfig,
    today: date | None = None,
) -> SemanticScholarBudgetState:
    current = today or date.today()
    usage = _load_usage(state_root)
    month_key = _month_key(current)
    used = usage.get("used", 0) if usage.get("month") == month_key else 0
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
    current = today or date.today()
    month_key = _month_key(current)
    usage_path = _usage_path(state_root)
    with STATE_IO_LOCK:
        usage = _load_usage_unlocked(usage_path)
        if usage.get("month") != month_key:
            usage = {"month": month_key, "used": 0}
        usage["used"] = int(usage.get("used", 0)) + 1
        _write_json_object_unlocked(usage_path, usage)


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


def _cache_dir(state_root: str | Path) -> Path:
    return Path(state_root).resolve() / "runs" / "cache" / "semantic_scholar"


def _usage_path(state_root: str | Path) -> Path:
    return Path(state_root).resolve() / "runs" / "state" / "semantic_scholar_usage.json"


def _load_usage(state_root: str | Path) -> dict[str, Any]:
    usage_path = _usage_path(state_root)
    with STATE_IO_LOCK:
        return _load_usage_unlocked(usage_path)


def _load_usage_unlocked(usage_path: Path) -> dict[str, Any]:
    payload = _read_json_object_unlocked(usage_path)
    return payload or {}


def _read_json_object(path: Path) -> dict[str, Any] | None:
    with STATE_IO_LOCK:
        return _read_json_object_unlocked(path)


def _read_json_object_unlocked(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json_object(path: Path, payload: dict[str, Any]) -> None:
    with STATE_IO_LOCK:
        _write_json_object_unlocked(path, payload)


def _write_json_object_unlocked(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        temp_path.write_text(serialized, encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def _month_key(today: date) -> str:
    return today.strftime("%Y-%m")
