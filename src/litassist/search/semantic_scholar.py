from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import httpx

from litassist.config import GeneralConfig, SemanticScholarConfig
from litassist.models import Paper, SourceMeta
from litassist.search.base import SearchError, Searcher
from litassist.semantic_scholar_state import (
    API_VERSION,
    build_cache_key,
    build_source_meta,
    get_budget_state,
    load_cached_results,
    record_successful_search,
    save_cached_results,
)


class SemanticScholarSearcher(Searcher):
    source = "semantic_scholar"
    FIELDS = (
        "abstract",
        "authors",
        "citationCount",
        "externalIds",
        "openAccessPdf",
        "title",
        "url",
        "venue",
        "year",
    )

    def __init__(self, general: GeneralConfig, config: SemanticScholarConfig):
        self.general = general
        self.config = config

    def search(self, query: str, limit: int) -> list[Paper]:
        items = self.search_items(query, limit)
        return [self._to_paper(item) for item in items]

    def search_with_budget(
        self,
        query: str,
        limit: int,
        state_root: str | Path,
    ) -> tuple[list[Paper], SourceMeta]:
        requested_limit = min(limit, 100)
        requested_fields = ",".join(self.FIELDS)
        budget_state = get_budget_state(state_root, self.config)
        cache_key = build_cache_key(
            query,
            self.general.from_year,
            requested_limit,
            requested_fields,
            api_version=API_VERSION,
        )
        cached = load_cached_results(
            state_root,
            cache_key=cache_key,
            ttl_days=self.config.cache_ttl_days,
        )
        if cached is not None:
            return [self._to_paper(item) for item in cached], build_source_meta(
                budget_state,
                used_cache=True,
            )

        if budget_state.budget_status == "cache_only":
            meta = build_source_meta(budget_state, used_cache=False)
            raise SearchError(meta.warning_message, meta=meta.to_dict())

        try:
            items = self.search_items(query, requested_limit)
        except SearchError as exc:
            meta = build_source_meta(budget_state, used_cache=False).to_dict()
            if exc.meta:
                meta.update(exc.meta)
            raise SearchError(str(exc), meta=meta) from exc

        save_cached_results(state_root, cache_key=cache_key, results=items)
        record_successful_search(state_root)
        updated_budget_state = get_budget_state(state_root, self.config)
        return [self._to_paper(item) for item in items], build_source_meta(
            updated_budget_state,
            used_cache=False,
        )

    def search_items(self, query: str, limit: int) -> list[dict[str, Any]]:
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": ",".join(self.FIELDS),
        }
        if self.general.from_year:
            params["year"] = f"{self.general.from_year}-{date.today().year}"
        headers = {"User-Agent": self.general.user_agent}
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        try:
            with httpx.Client(
                timeout=self.general.request_timeout_seconds, headers=headers
            ) as client:
                response = client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and not self.config.api_key:
                raise SearchError(
                    "Semantic Scholar rate limited the anonymous request. "
                    "Set SEMANTIC_SCHOLAR_API_KEY or disable this source."
                ) from exc
            raise SearchError(f"Semantic Scholar request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise SearchError(f"Semantic Scholar request failed: {exc}") from exc

        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def _to_paper(self, item: dict[str, Any]) -> Paper:
        external_ids = item.get("externalIds") or {}
        open_access_pdf = item.get("openAccessPdf") or {}
        return Paper(
            title=item.get("title") or "Untitled",
            source=self.source,
            authors=[
                author.get("name")
                for author in item.get("authors", [])
                if author.get("name")
            ],
            year=item.get("year"),
            venue=item.get("venue") or None,
            abstract=item.get("abstract"),
            doi=(external_ids.get("DOI") or "").lower() or None,
            url=item.get("url"),
            pdf_url=open_access_pdf.get("url"),
            external_id=item.get("paperId"),
            cited_by_count=item.get("citationCount"),
            score=item.get("score"),
            raw={"semantic_scholar_id": item.get("paperId")},
        )
