"""SQLite storage for search cache, archive metadata, and API usage tracking.

Replaces fragmented JSON file storage with a single, transactional database.
The filesystem is still used for report.md and static file serving.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_DB_PATH: Path | None = None
_LOCAL = threading.local()


def init(db_path: str | Path) -> None:
    global _DB_PATH
    resolved = Path(db_path).resolve()
    if _DB_PATH == resolved:
        return  # already initialized with this path
    _DB_PATH = resolved
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _connection() as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS search_cache (
                cache_key TEXT PRIMARY KEY,
                results TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS search_archive (
                id TEXT PRIMARY KEY,
                need TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'running',
                sources TEXT NOT NULL DEFAULT '[]',
                zh_keywords TEXT NOT NULL DEFAULT '[]',
                en_keywords TEXT NOT NULL DEFAULT '[]',
                from_year INTEGER,
                limit_count INTEGER,
                prefer_recent INTEGER DEFAULT 0,
                use_llm INTEGER DEFAULT 0,
                plan TEXT NOT NULL DEFAULT '{}',
                papers TEXT NOT NULL DEFAULT '[]',
                paper_count INTEGER DEFAULT 0,
                errors TEXT NOT NULL DEFAULT '{}',
                source_meta TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_usage (
                service TEXT NOT NULL,
                month TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                PRIMARY KEY (service, month)
            );

            CREATE INDEX IF NOT EXISTS idx_cache_expires ON search_cache(expires_at);
            CREATE INDEX IF NOT EXISTS idx_archive_created ON search_archive(created_at DESC);
        """)


@contextmanager
def _connection() -> sqlite3.Connection:
    if _DB_PATH is None:
        raise RuntimeError("db.init() must be called before using the database")
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Cache operations ──────────────────────────────────────


def cache_get(
    cache_key: str,
    now: datetime | None = None,
) -> list[dict[str, Any]] | None:
    with _connection() as conn:
        row = conn.execute(
            "SELECT results, expires_at FROM search_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if row is None:
        return None
    now_dt = now or datetime.now()
    if datetime.fromisoformat(row["expires_at"]) < now_dt:
        return None
    return json.loads(row["results"])


def cache_set(
    cache_key: str,
    results: list[dict[str, Any]],
    ttl_days: int,
    now: datetime | None = None,
) -> None:
    now_dt = now or datetime.now()
    expires_at = now_dt + timedelta(days=ttl_days)
    with _connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO search_cache
               (cache_key, results, created_at, expires_at)
               VALUES (?, ?, ?, ?)""",
            (
                cache_key,
                json.dumps(results, ensure_ascii=False),
                now_dt.isoformat(),
                expires_at.isoformat(),
            ),
        )


def cache_evict(max_entries: int = 5000) -> int:
    """Remove oldest entries beyond max_entries. Returns count removed."""
    with _connection() as conn:
        count = conn.execute(
            """DELETE FROM search_cache WHERE cache_key IN (
                SELECT cache_key FROM search_cache
                ORDER BY created_at ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM search_cache) - ?)
            )""",
            (max_entries,),
        ).rowcount
    return count


def cache_clear_expired() -> int:
    with _connection() as conn:
        count = conn.execute(
            "DELETE FROM search_cache WHERE expires_at < ?",
            (datetime.now().isoformat(),),
        ).rowcount
    return count


# ── Archive operations ─────────────────────────────────────


def archive_save(
    run_id: str,
    need: str,
    title: str = "",
    status: str = "running",
    sources: list[str] | None = None,
    zh_keywords: list[str] | None = None,
    en_keywords: list[str] | None = None,
    from_year: int | None = None,
    limit_count: int | None = None,
    prefer_recent: bool = False,
    use_llm: bool = False,
    plan: dict[str, Any] | None = None,
    papers: list[dict[str, Any]] | None = None,
    errors: dict[str, str] | None = None,
    source_meta: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> None:
    now_str = created_at or datetime.now().isoformat()
    papers_list = papers or []
    with _connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO search_archive
               (id, need, title, status, sources, zh_keywords, en_keywords,
                from_year, limit_count, prefer_recent, use_llm,
                plan, papers, paper_count, errors, source_meta, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                need,
                title,
                status,
                json.dumps(sources or [], ensure_ascii=False),
                json.dumps(zh_keywords or [], ensure_ascii=False),
                json.dumps(en_keywords or [], ensure_ascii=False),
                from_year,
                limit_count,
                1 if prefer_recent else 0,
                1 if use_llm else 0,
                json.dumps(plan or {}, ensure_ascii=False),
                json.dumps(papers_list, ensure_ascii=False),
                len(papers_list),
                json.dumps(errors or {}, ensure_ascii=False),
                json.dumps(source_meta or {}, ensure_ascii=False),
                now_str,
                now_str,
            ),
        )


def archive_update(run_id: str, **fields: Any) -> None:
    sets: list[str] = []
    values: list[Any] = []
    for key, value in fields.items():
        if key in ("status", "title", "paper_count") and value is not None:
            sets.append(f"{key} = ?")
            values.append(value)
        elif key in ("plan", "papers", "errors", "source_meta"):
            sets.append(f"{key} = ?")
            values.append(json.dumps(value, ensure_ascii=False))
    if not sets:
        return
    sets.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(run_id)
    with _connection() as conn:
        conn.execute(
            f"UPDATE search_archive SET {', '.join(sets)} WHERE id = ?",
            values,
        )


def archive_list(
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    with _connection() as conn:
        rows = conn.execute(
            """SELECT id, need, title, status, sources, zh_keywords, en_keywords,
                      from_year, limit_count, prefer_recent, use_llm,
                      paper_count, errors, created_at
               FROM search_archive
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
    return [_row_to_archive_summary(row) for row in rows]


def archive_get(run_id: str) -> dict[str, Any] | None:
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM search_archive WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_archive_detail(row)


def archive_delete(run_id: str) -> bool:
    with _connection() as conn:
        cursor = conn.execute(
            "DELETE FROM search_archive WHERE id = ?",
            (run_id,),
        )
    return cursor.rowcount > 0


def _row_to_archive_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "need": row["need"],
        "title": row["title"] or _compact_title(row["need"]),
        "createdAt": row["created_at"],
        "zhKeywords": json.loads(row["zh_keywords"]),
        "enKeywords": json.loads(row["en_keywords"]),
        "sources": json.loads(row["sources"]),
        "paperCount": row["paper_count"],
        "status": _status_label(row["status"], row["paper_count"]),
        "fromYear": row["from_year"],
        "limit": row["limit_count"],
        "preferRecent": bool(row["prefer_recent"]),
        "useLlm": bool(row["use_llm"]),
    }


def _row_to_archive_detail(row: sqlite3.Row) -> dict[str, Any]:
    summary = _row_to_archive_summary(row)
    summary.update(
        {
            "plan": json.loads(row["plan"]),
            "papers": json.loads(row["papers"]),
            "errors": json.loads(row["errors"]),
            "sourceMeta": json.loads(row["source_meta"]),
        }
    )
    return summary


def _status_label(status: str, paper_count: int) -> str:
    labels = {
        "success": "成功",
        "partial": "部分完成",
        "failed": "失败",
        "running": "进行中",
        "interrupted": "中断",
    }
    if status in labels:
        return labels[status]
    return "已归档" if paper_count else "暂无结果"


def _compact_title(need: str) -> str:
    compact = " ".join(need.split())
    return compact[:36] + ("..." if len(compact) > 36 else "")


# ── API usage operations ───────────────────────────────────


def usage_get(service: str, month: str) -> int:
    with _connection() as conn:
        row = conn.execute(
            "SELECT used FROM api_usage WHERE service = ? AND month = ?",
            (service, month),
        ).fetchone()
    return row["used"] if row else 0


def usage_increment(service: str, month: str) -> None:
    with _connection() as conn:
        conn.execute(
            """INSERT INTO api_usage (service, month, used) VALUES (?, ?, 1)
               ON CONFLICT(service, month) DO UPDATE SET used = used + 1""",
            (service, month),
        )
