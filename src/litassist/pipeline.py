from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any

from .config import AppConfig
from .dedupe import dedupe_papers, paper_identity_key
from .enrich import enrich_papers, filter_low_quality
from .llm_planner import LLMPlannerError, build_llm_plan
from .models import Paper, ResearchPlan
from .planner import build_plan
from .search import (
    CrossrefSearcher,
    GoogleScholarSearcher,
    OpenAlexSearcher,
    SearchError,
    SemanticScholarSearcher,
    WebOfScienceSearcher,
    ZoteroSearcher,
)


@dataclass(slots=True)
class SearchRun:
    plan: ResearchPlan
    papers: list[Paper]
    errors: dict[str, str]
    source_meta: dict[str, dict[str, Any]] = field(default_factory=dict)


def run_search(
    need: str,
    config: AppConfig,
    sources: list[str] | None = None,
    limit: int | None = None,
    zh_keywords: list[str] | None = None,
    en_keywords: list[str] | None = None,
    use_llm: bool | None = None,
    from_year: int | None = None,
    prefer_recent: bool | None = None,
    state_root: str | Path | None = None,
    file_context: str | None = None,
    search_dimensions: list[dict] | None = None,
    suggested_queries: dict[str, str] | None = None,
    progress_callback: (
        Callable[[str, str, dict[str, Any]], None] | None
    ) = None,
) -> SearchRun:
    config = _runtime_config(config, from_year=from_year, prefer_recent=prefer_recent)
    resolved_state_root = Path(state_root or Path.cwd()).resolve()
    plan = _build_search_plan(
        need,
        config=config,
        zh_keywords=zh_keywords,
        en_keywords=en_keywords,
        use_llm=use_llm,
        file_context=file_context,
        search_dimensions=search_dimensions,
        suggested_queries=suggested_queries,
    )
    selected_sources = sources or config.general.enabled_sources
    per_source_limit = limit or config.general.max_results_per_source
    searchers = _searchers(config)

    papers: list[Paper] = []
    errors: dict[str, str] = {}
    source_meta: dict[str, dict[str, Any]] = {}

    def _search_one(
        source: str,
    ) -> tuple[str, list[Paper], str | None, dict[str, Any]]:
        if progress_callback:
            progress_callback(source, "running", {"source": source})
        searcher = searchers.get(source)
        if not searcher:
            return source, [], f"Unknown or unavailable source: {source}", {}

        query_rounds = _query_rounds(plan, source)
        round_errors: list[dict[str, Any]] = []
        round_stats: list[dict[str, Any]] = []
        last_meta: dict[str, Any] = {}
        successful_rounds = 0
        source_papers_total = 0
        source_unique_keys: set[str] = set()
        local_papers: list[Paper] = []
        for round_index, query in enumerate(query_rounds, start=1):
            round_limit = _query_round_limit(
                source=source,
                per_source_limit=per_source_limit,
                round_index=round_index,
            )
            try:
                if source == "semantic_scholar" and isinstance(
                    searcher, SemanticScholarSearcher
                ):
                    round_papers, meta = searcher.search_with_budget(
                        query,
                        round_limit,
                        state_root=resolved_state_root,
                    )
                    last_meta = meta.to_dict()
                else:
                    round_papers = searcher.search(query, round_limit)
            except SearchError as exc:
                round_errors.append(
                    {
                        "round": round_index,
                        "query": query,
                        "error": str(exc),
                    }
                )
                if exc.meta:
                    last_meta.update(dict(exc.meta))
                round_stats.append(
                    {
                        "round": round_index,
                        "query": query,
                        "limit": round_limit,
                        "retrieved_count": 0,
                        "new_unique_count": 0,
                        "cumulative_unique_count": len(source_unique_keys),
                        "error": str(exc),
                    }
                )
                continue
            successful_rounds += 1
            source_papers_total += len(round_papers)
            new_unique_count = 0
            for paper in round_papers:
                paper_key = paper_identity_key(paper)
                if paper_key not in source_unique_keys:
                    source_unique_keys.add(paper_key)
                    new_unique_count += 1
                paper.tags.extend(
                    [
                        f"source:{source}",
                        "status:to-screen",
                        f"query_round:{source}:{round_index}",
                    ]
                )
            round_stats.append(
                {
                    "round": round_index,
                    "query": query,
                    "limit": round_limit,
                    "retrieved_count": len(round_papers),
                    "new_unique_count": new_unique_count,
                    "cumulative_unique_count": len(source_unique_keys),
                }
            )
            local_papers.extend(round_papers)

        error_msg: str | None = None
        if successful_rounds == 0 and round_errors:
            error_msg = "; ".join(
                f"round {e['round']}: {e['error']}" for e in round_errors
            )
        meta = {
            **last_meta,
            "query_round_count": len(query_rounds),
            "successful_rounds": successful_rounds,
            "retrieved_before_dedupe": source_papers_total,
            "unique_before_dedupe": len(source_unique_keys),
            "query_rounds": query_rounds,
            "round_stats": round_stats,
            "round_errors": round_errors,
        }
        return source, local_papers, error_msg, meta

    with ThreadPoolExecutor(max_workers=len(selected_sources)) as pool:
        futs = {pool.submit(_search_one, s): s for s in selected_sources}
        for fut in as_completed(futs):
            source, local_papers, error_msg, meta = fut.result()
            papers.extend(local_papers)
            if error_msg:
                errors[source] = error_msg
            source_meta[source] = meta
            if progress_callback:
                if error_msg:
                    progress_callback(source, "error", {"message": error_msg})
                else:
                    progress_callback(source, "complete", {"paper_count": len(local_papers)})

    papers = _filter_by_year(papers, config.general.from_year)
    deduped = dedupe_papers(papers, prefer_recent=config.general.prefer_recent)
    enriched = enrich_papers(deduped, plan, config.general)
    enriched = _filter_by_year(enriched, config.general.from_year)
    enriched = _filter_low_relevance(enriched)
    return SearchRun(
        plan=plan,
        papers=dedupe_papers(
            enriched,
            prefer_recent=config.general.prefer_recent,
        ),
        errors=errors,
        source_meta=source_meta,
    )


def _build_search_plan(
    need: str,
    config: AppConfig,
    zh_keywords: list[str] | None,
    en_keywords: list[str] | None,
    use_llm: bool | None,
    file_context: str | None = None,
    search_dimensions: list[dict] | None = None,
    suggested_queries: dict[str, str] | None = None,
) -> ResearchPlan:
    should_use_llm = config.llm.enabled if use_llm is None else use_llm
    if not should_use_llm:
        return build_plan(need, zh_keywords=zh_keywords, en_keywords=en_keywords)
    try:
        return build_llm_plan(
            need,
            config.llm,
            zh_keywords=zh_keywords,
            en_keywords=en_keywords,
            file_context=file_context,
            search_dimensions=search_dimensions,
            suggested_queries=suggested_queries,
        )
    except LLMPlannerError as exc:
        plan = build_plan(need, zh_keywords=zh_keywords, en_keywords=en_keywords)
        plan.notes.append(
            f"LLM planning unavailable; used rules instead. Reason: {exc}"
        )
        return plan


def _searchers(config: AppConfig):
    return {
        "openalex": OpenAlexSearcher(config.general),
        "crossref": CrossrefSearcher(config.general),
        "zotero": ZoteroSearcher(config.zotero, config.general),
        "google_scholar": GoogleScholarSearcher(
            config.general,
            config.google_scholar,
        ),
        "semantic_scholar": SemanticScholarSearcher(
            config.general, config.semantic_scholar
        ),
        "web_of_science": WebOfScienceSearcher(config.general, config.web_of_science),
    }


def _runtime_config(
    config: AppConfig,
    from_year: int | None,
    prefer_recent: bool | None,
) -> AppConfig:
    if from_year is None and prefer_recent is None:
        return config
    general = replace(
        config.general,
        from_year=config.general.from_year if from_year is None else from_year,
        prefer_recent=(
            config.general.prefer_recent if prefer_recent is None else prefer_recent
        ),
    )
    return replace(config, general=general)


def _filter_by_year(papers: list[Paper], from_year: int | None) -> list[Paper]:
    current_year = date.today().year
    if not from_year:
        return [
            paper
            for paper in papers
            if paper.year is None or paper.year <= current_year
        ]
    return [
        paper
        for paper in papers
        if paper.year is None or from_year <= paper.year <= current_year
    ]


def _filter_low_relevance(papers: list[Paper]) -> list[Paper]:
    return filter_low_quality(papers)


def _query_rounds(plan: ResearchPlan, source: str) -> list[str]:
    rounds = plan.query_rounds.get(source) or []
    if rounds:
        return rounds
    fallback = plan.queries.get(source) or plan.queries["openalex"]
    return [fallback]


def _query_round_limit(
    source: str,
    per_source_limit: int,
    round_index: int,
) -> int:
    if round_index == 1:
        return per_source_limit
    if source == "google_scholar":
        return max(3, min(10, per_source_limit // 2 or per_source_limit))
    return max(5, min(per_source_limit, per_source_limit // 2 or per_source_limit))
