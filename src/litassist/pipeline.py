from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig
from .dedupe import dedupe_papers
from .enrich import enrich_papers
from .llm_planner import LLMPlannerError, build_llm_plan
from .models import Paper, ResearchPlan
from .planner import build_plan
from .search import (
    CrossrefSearcher,
    OpenAlexSearcher,
    SearchError,
    SemanticScholarSearcher,
    WebOfScienceSearcher,
)


@dataclass(slots=True)
class SearchRun:
    plan: ResearchPlan
    papers: list[Paper]
    errors: dict[str, str]


def run_search(
    need: str,
    config: AppConfig,
    sources: list[str] | None = None,
    limit: int | None = None,
    zh_keywords: list[str] | None = None,
    en_keywords: list[str] | None = None,
    use_llm: bool | None = None,
) -> SearchRun:
    plan = _build_search_plan(
        need,
        config=config,
        zh_keywords=zh_keywords,
        en_keywords=en_keywords,
        use_llm=use_llm,
    )
    selected_sources = sources or config.general.enabled_sources
    per_source_limit = limit or config.general.max_results_per_source
    searchers = _searchers(config)

    papers: list[Paper] = []
    errors: dict[str, str] = {}
    for source in selected_sources:
        searcher = searchers.get(source)
        if not searcher:
            errors[source] = f"Unknown or unavailable source: {source}"
            continue
        query = plan.queries.get(source) or plan.queries["openalex"]
        try:
            source_papers = searcher.search(query, per_source_limit)
        except SearchError as exc:
            errors[source] = str(exc)
            continue
        for paper in source_papers:
            paper.tags.extend([f"source:{source}", "status:to-screen"])
        papers.extend(source_papers)

    deduped = dedupe_papers(papers)
    enriched = enrich_papers(deduped, plan, config.general)
    return SearchRun(plan=plan, papers=dedupe_papers(enriched), errors=errors)


def _build_search_plan(
    need: str,
    config: AppConfig,
    zh_keywords: list[str] | None,
    en_keywords: list[str] | None,
    use_llm: bool | None,
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
        )
    except LLMPlannerError as exc:
        plan = build_plan(need, zh_keywords=zh_keywords, en_keywords=en_keywords)
        plan.notes.append(f"LLM planning unavailable; used rules instead. Reason: {exc}")
        return plan


def _searchers(config: AppConfig):
    return {
        "openalex": OpenAlexSearcher(config.general),
        "crossref": CrossrefSearcher(config.general),
        "semantic_scholar": SemanticScholarSearcher(
            config.general, config.semantic_scholar
        ),
        "web_of_science": WebOfScienceSearcher(config.general, config.web_of_science),
    }
