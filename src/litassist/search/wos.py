from __future__ import annotations

from typing import Any

import httpx

from litassist.config import GeneralConfig, WebOfScienceConfig
from litassist.models import Paper
from litassist.search.base import SearchError, Searcher


class WebOfScienceSearcher(Searcher):
    source = "web_of_science"

    def __init__(self, general: GeneralConfig, config: WebOfScienceConfig):
        self.general = general
        self.config = config

    def search(self, query: str, limit: int) -> list[Paper]:
        if not self.config.api_key:
            raise SearchError(
                "Web of Science requires an API key. Add it in Source 配置 or set WOS_API_KEY."
            )

        headers = {
            "User-Agent": self.general.user_agent,
            "X-ApiKey": self.config.api_key,
        }
        wos_query = query
        if self.general.from_year:
            wos_query = f"({query}) AND PY=({self.general.from_year}-{_current_year()})"
        params = {"q": wos_query, "limit": min(limit, 50), "page": 1}

        try:
            with httpx.Client(
                timeout=self.general.request_timeout_seconds, headers=headers
            ) as client:
                response = client.get(self.config.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"Web of Science request failed: {exc}") from exc

        return [self._to_paper(item) for item in payload.get("hits", [])]

    def _to_paper(self, item: dict[str, Any]) -> Paper:
        title = _first(item.get("title")) or item.get("title") or "Untitled"
        source = item.get("source") or {}
        identifiers = item.get("identifiers") or {}
        return Paper(
            title=title,
            source=self.source,
            authors=_authors(item.get("names", {}).get("authors", [])),
            year=_int_or_none(source.get("publishYear")),
            venue=source.get("sourceTitle"),
            doi=(identifiers.get("doi") or item.get("doi") or "").lower() or None,
            url=item.get("links", {}).get("record"),
            external_id=item.get("uid"),
            cited_by_count=_int_or_none(item.get("citations", {}).get("timesCited")),
            raw={"wos_uid": item.get("uid")},
        )


def _first(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return value[0]
    return None


def _authors(values: list[dict[str, Any]]) -> list[str]:
    authors = []
    for value in values:
        name = value.get("displayName") or value.get("wosStandard")
        if name:
            authors.append(name)
    return authors


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _current_year() -> int:
    from datetime import date

    return date.today().year
