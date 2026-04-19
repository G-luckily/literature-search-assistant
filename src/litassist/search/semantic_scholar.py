from __future__ import annotations

from typing import Any

import httpx

from litassist.config import GeneralConfig, SemanticScholarConfig
from litassist.models import Paper
from litassist.search.base import SearchError, Searcher


class SemanticScholarSearcher(Searcher):
    source = "semantic_scholar"

    def __init__(self, general: GeneralConfig, config: SemanticScholarConfig):
        self.general = general
        self.config = config

    def search(self, query: str, limit: int) -> list[Paper]:
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": ",".join(
                [
                    "abstract",
                    "authors",
                    "citationCount",
                    "externalIds",
                    "openAccessPdf",
                    "title",
                    "url",
                    "venue",
                    "year",
                ]
            ),
        }
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

        return [self._to_paper(item) for item in payload.get("data", [])]

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
