from __future__ import annotations

import re
from datetime import date
from typing import Any

import httpx

from litassist.config import GeneralConfig, GoogleScholarConfig
from litassist.models import Paper
from litassist.search.base import SearchError, Searcher


class GoogleScholarSearcher(Searcher):
    source = "google_scholar"

    def __init__(self, general: GeneralConfig, config: GoogleScholarConfig):
        self.general = general
        self.config = config

    def search(self, query: str, limit: int) -> list[Paper]:
        if not self.config.api_key:
            raise SearchError(
                "Google Scholar has no official open API in this app. "
                "Add a SerpApi key in Source 配置 or disable this source."
            )

        params: dict[str, Any] = {
            "engine": "google_scholar",
            "q": query,
            "api_key": self.config.api_key,
            "num": min(limit, 20),
        }
        if self.general.from_year:
            params["as_ylo"] = self.general.from_year
            params["as_yhi"] = date.today().year

        headers = {"User-Agent": self.general.user_agent}
        try:
            with httpx.Client(
                timeout=self.general.request_timeout_seconds, headers=headers
            ) as client:
                response = client.get(self.config.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"Google Scholar via SerpApi request failed: {exc}") from exc

        if payload.get("error"):
            raise SearchError(f"Google Scholar via SerpApi failed: {payload['error']}")
        return [self._to_paper(item) for item in payload.get("organic_results", [])]

    def _to_paper(self, item: dict[str, Any]) -> Paper:
        publication_info = item.get("publication_info") or {}
        summary = publication_info.get("summary") or ""
        resources = item.get("resources") or []
        inline_links = item.get("inline_links") or {}
        cited_by = inline_links.get("cited_by") or {}
        pdf_url = _first_pdf(resources)
        return Paper(
            title=item.get("title") or "Untitled",
            source=self.source,
            authors=_authors(publication_info),
            year=_year(summary),
            venue=_venue(summary),
            url=item.get("link"),
            pdf_url=pdf_url,
            cited_by_count=_int_or_none(cited_by.get("total")),
            score=item.get("position"),
            raw={"google_scholar_result_id": item.get("result_id")},
        )


def _authors(publication_info: dict[str, Any]) -> list[str]:
    authors = publication_info.get("authors")
    if isinstance(authors, list):
        names = [author.get("name") for author in authors if author.get("name")]
        if names:
            return names
    summary = publication_info.get("summary") or ""
    first_segment = summary.split(" - ", 1)[0]
    return [part.strip() for part in first_segment.split(",") if part.strip()]


def _year(value: str) -> int | None:
    years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", value)]
    return max(years) if years else None


def _venue(value: str) -> str | None:
    parts = [part.strip() for part in value.split(" - ") if part.strip()]
    if len(parts) >= 2:
        return parts[1]
    return None


def _first_pdf(resources: list[dict[str, Any]]) -> str | None:
    for resource in resources:
        title = str(resource.get("title") or "").lower()
        link = resource.get("link")
        if link and ("pdf" in title or str(link).lower().endswith(".pdf")):
            return link
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
