from __future__ import annotations

import re
from datetime import date
from html import unescape
from typing import Any

import httpx

from litassist.config import GeneralConfig
from litassist.models import Paper
from litassist.search.base import SearchError, Searcher


class CrossrefSearcher(Searcher):
    source = "crossref"

    def __init__(self, config: GeneralConfig):
        self.config = config

    def search(self, query: str, limit: int) -> list[Paper]:
        params: dict[str, Any] = {
            "query.bibliographic": query,
            "rows": min(limit, 100),
            "sort": "relevance",
            "order": "desc",
            "select": ",".join(
                [
                    "DOI",
                    "URL",
                    "abstract",
                    "author",
                    "container-title",
                    "is-referenced-by-count",
                    "issued",
                    "published-online",
                    "published-print",
                    "title",
                ]
            ),
        }
        if self.config.from_year:
            params["filter"] = ",".join(
                [
                    f"from-pub-date:{self.config.from_year}-01-01",
                    f"until-pub-date:{date.today().year}-12-31",
                ]
            )
        if self.config.contact_email:
            params["mailto"] = self.config.contact_email

        headers = {"User-Agent": self.config.user_agent}
        try:
            with httpx.Client(
                timeout=self.config.request_timeout_seconds, headers=headers
            ) as client:
                response = client.get("https://api.crossref.org/works", params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"Crossref request failed: {exc}") from exc

        items = payload.get("message", {}).get("items", [])
        return [self._to_paper(item) for item in items]

    def _to_paper(self, item: dict[str, Any]) -> Paper:
        return Paper(
            title=_first(item.get("title")) or "Untitled",
            source=self.source,
            authors=_authors(item.get("author", [])),
            year=_year(item),
            venue=_first(item.get("container-title")),
            abstract=_strip_html(item.get("abstract")),
            doi=(item.get("DOI") or "").lower() or None,
            url=item.get("URL"),
            cited_by_count=item.get("is-referenced-by-count"),
            score=item.get("score"),
            raw={"crossref_doi": item.get("DOI")},
        )


def _first(values: list[str] | None) -> str | None:
    if not values:
        return None
    return values[0]


def _authors(values: list[dict[str, Any]]) -> list[str]:
    authors = []
    for author in values:
        if author.get("name"):
            authors.append(author["name"])
            continue
        full = " ".join(
            part for part in [author.get("given"), author.get("family")] if part
        )
        if full:
            authors.append(full)
    return authors


def _year(item: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "issued"):
        parts = item.get(key, {}).get("date-parts")
        if parts and parts[0]:
            return parts[0][0]
    return None


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(value))).strip()
