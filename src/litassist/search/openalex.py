from __future__ import annotations

import re
from datetime import date
from typing import Any

import httpx

from litassist.config import GeneralConfig
from litassist.models import Paper
from litassist.search.base import SearchError, Searcher


class OpenAlexSearcher(Searcher):
    source = "openalex"

    def __init__(self, config: GeneralConfig):
        self.config = config

    def search(self, query: str, limit: int) -> list[Paper]:
        params: dict[str, Any] = {
            "search": query,
            "per-page": min(limit, 200),
            "sort": "relevance_score:desc",
        }
        if self.config.from_year:
            params["filter"] = ",".join(
                [
                    f"from_publication_date:{self.config.from_year}-01-01",
                    f"to_publication_date:{date.today().year}-12-31",
                ]
            )
        if self.config.contact_email:
            params["mailto"] = self.config.contact_email

        headers = {"User-Agent": self.config.user_agent}
        try:
            with httpx.Client(
                timeout=self.config.request_timeout_seconds, headers=headers
            ) as client:
                response = client.get("https://api.openalex.org/works", params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"OpenAlex request failed: {exc}") from exc

        return [self._to_paper(item) for item in payload.get("results", [])]

    def _to_paper(self, item: dict[str, Any]) -> Paper:
        title = item.get("display_name") or "Untitled"
        doi = _clean_doi(item.get("doi") or item.get("ids", {}).get("doi"))
        authors = [
            authorship.get("author", {}).get("display_name")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        location = item.get("primary_location") or {}
        best_oa = item.get("best_oa_location") or {}
        venue = (
            (location.get("source") or {}).get("display_name")
            or (best_oa.get("source") or {}).get("display_name")
        )
        url = (
            location.get("landing_page_url")
            or best_oa.get("landing_page_url")
            or item.get("id")
        )
        pdf_url = best_oa.get("pdf_url") or location.get("pdf_url")

        return Paper(
            title=title,
            source=self.source,
            authors=authors,
            year=item.get("publication_year"),
            venue=venue,
            abstract=_abstract_from_inverted_index(item.get("abstract_inverted_index")),
            doi=doi,
            url=url,
            pdf_url=pdf_url,
            external_id=item.get("id"),
            cited_by_count=item.get("cited_by_count"),
            score=item.get("relevance_score"),
            raw={"openalex_id": item.get("id")},
        )


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    positions: dict[int, str] = {}
    for word, offsets in index.items():
        for offset in offsets:
            positions[offset] = word
    return " ".join(positions[i] for i in sorted(positions))


def _clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", value.strip(), flags=re.I)
    return doi.lower() or None
