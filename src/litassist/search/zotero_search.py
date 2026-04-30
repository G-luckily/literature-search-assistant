from __future__ import annotations

import re
from typing import Any

from litassist.config import ZoteroConfig, GeneralConfig
from litassist.models import Paper
from litassist.search.base import SearchError, Searcher

ALLOWED_TYPES = frozenset({
    "journalArticle",
    "conferencePaper",
    "book",
    "bookSection",
    "thesis",
})


class ZoteroSearcher(Searcher):
    source = "zotero"

    def __init__(self, zotero_config: ZoteroConfig, general_config: GeneralConfig):
        self.config = zotero_config
        self.general = general_config

    def search(self, query: str, limit: int) -> list[Paper]:
        if not self.config.api_key or not self.config.library_id:
            raise SearchError("Zotero library_id and api_key are required.")

        try:
            from pyzotero import zotero
            from pyzotero.zotero import PyZoteroError
        except ImportError as exc:
            raise SearchError(f"pyzotero is not installed: {exc}") from exc

        import requests

        zot = zotero.Zotero(
            self.config.library_id,
            self.config.library_type,
            self.config.api_key,
        )

        zot.add_parameters(
            q=query,
            qmode="titleCreatorYear",
            limit=min(limit, 100),
        )

        try:
            items = zot.top()
        except (PyZoteroError, requests.RequestException) as exc:
            raise SearchError(f"Zotero search failed: {exc}") from exc

        papers: list[Paper] = []
        seen_keys: set[str] = set()

        for item in items:
            data = item.get("data", {})
            if data.get("itemType") not in ALLOWED_TYPES:
                continue

            paper = self._to_paper(data, item.get("key"))
            if paper is None:
                continue

            dedup_key = paper.doi or paper.title.lower()
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            if self.general.from_year and paper.year and paper.year < self.general.from_year:
                continue

            papers.append(paper)
            if len(papers) >= limit:
                break

        return papers

    def _to_paper(self, data: dict[str, Any], zotero_key: str | None) -> Paper | None:
        title = (data.get("title") or "").strip()
        if not title:
            return None

        creators = data.get("creators", [])
        authors: list[str] = []
        for c in creators:
            if not isinstance(c, dict):
                continue
            name = (
                c.get("name")
                or _join_name(c.get("firstName"), c.get("lastName"))
                or ""
            ).strip()
            if name:
                authors.append(name)

        date_str = data.get("date") or ""
        year = None
        m = re.search(r"\b(\d{4})\b", date_str)
        if m:
            year = int(m.group(1))

        doi = _clean_doi(data.get("DOI") or "")
        url = data.get("url") or None
        abstract = (data.get("abstractNote") or "").strip() or None
        venue = (data.get("publicationTitle") or data.get("bookTitle") or "").strip() or None

        raw_tags = data.get("tags") or []
        tags = [
            f"zotero:{t['tag']}"
            for t in raw_tags
            if isinstance(t, dict) and t.get("tag")
        ]

        return Paper(
            title=title,
            source=self.source,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            doi=doi,
            url=url,
            external_id=zotero_key,
            sources=[self.source],
            tags=tags,
            raw={"zotero_key": zotero_key, "item_type": data.get("itemType")},
        )


def _join_name(first: Any, last: Any) -> str:
    parts = []
    if isinstance(first, str) and first.strip():
        parts.append(first.strip())
    if isinstance(last, str) and last.strip():
        parts.append(last.strip())
    return " ".join(parts)


def _clean_doi(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    return doi.lower() or None
