"""Helper functions for the web server — serialization, validation, archive I/O."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import SemanticScholarConfig


# ── Payload parsing ────────────────────────────────────────────────


def required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def optional_text(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text")
    value = value.strip()
    return value or default


def optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc


def optional_bool(payload: dict[str, Any], key: str) -> bool | None:
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


def api_key_update(payload: dict[str, Any], prefix: str) -> dict[str, str | None]:
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


def numeric_updates(
    payload: dict[str, Any],
    keys: dict[str, str],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for config_key, payload_key in keys.items():
        value = optional_int(payload, payload_key)
        if value is not None:
            result[config_key] = value
    return result


def list_of_text(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("keyword and source values must be lists")
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def default_model(provider: str) -> str:
    if provider == "deepseek":
        return "deepseek-chat"
    return "gpt-4.1-mini"


def default_endpoint(provider: str) -> str:
    if provider == "deepseek":
        return "https://api.deepseek.com/v1"
    return "https://api.openai.com/v1/responses"


# ── Semantic Scholar budget validation ────────────────────────────


def validate_semantic_budget_updates(
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


# ── Source meta serialization ─────────────────────────────────────


def serialize_source_meta(
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


# ── Archive file helpers ──────────────────────────────────────────


def archive_root(project_root: Path) -> Path:
    return (_runs_root(project_root) / "web").resolve()


def _runs_root(project_root: Path) -> Path:
    return (project_root / "runs").resolve()


def create_timestamped_run_dir(
    project_root: Path,
    created_at: datetime,
) -> tuple[str, Path]:
    archive_root_dir = archive_root(project_root)
    archive_root_dir.mkdir(parents=True, exist_ok=True)
    base_run_id = created_at.strftime("%Y%m%d-%H%M%S")
    suffix = 1
    while True:
        run_id = base_run_id if suffix == 1 else f"{base_run_id}-{suffix}"
        run_dir = archive_root_dir / run_id
        try:
            run_dir.mkdir()
        except FileExistsError:
            suffix += 1
            continue
        return run_id, run_dir


def resolve_archive_dir(project_root: Path, run_id: str) -> Path:
    archive_root_dir = archive_root(project_root)
    target = (archive_root_dir / run_id).resolve()
    if archive_root_dir not in target.parents:
        raise ValueError("invalid archive path")
    return target


def load_archive_summary(run_dir: Path) -> dict[str, Any] | None:
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


def load_archive_detail(run_dir: Path) -> dict[str, Any] | None:
    summary = load_archive_summary(run_dir)
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
                serialize_source_meta(source_meta)
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
