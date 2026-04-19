from __future__ import annotations

from dataclasses import dataclass

from .config import ZoteroConfig
from .models import Paper


@dataclass(slots=True)
class ZoteroImportResult:
    created: int
    skipped: int
    errors: list[str]


def import_papers(
    papers: list[Paper],
    config: ZoteroConfig,
    limit: int | None = None,
    apply: bool = False,
) -> ZoteroImportResult:
    selected = papers[:limit] if limit else papers
    if not apply:
        return ZoteroImportResult(created=0, skipped=len(selected), errors=[])

    if not config.library_id or not config.api_key:
        return ZoteroImportResult(
            created=0,
            skipped=0,
            errors=["Zotero library_id and api_key are required."],
        )

    try:
        from pyzotero import zotero
    except ImportError as exc:
        return ZoteroImportResult(
            created=0,
            skipped=0,
            errors=[f"pyzotero is not installed: {exc}"],
        )

    zot = zotero.Zotero(config.library_id, config.library_type, config.api_key)
    items = [_paper_to_zotero_item(paper, config.collection_key) for paper in selected]
    errors: list[str] = []
    created = 0

    for start in range(0, len(items), 50):
        batch = items[start : start + 50]
        try:
            response = zot.create_items(batch)
        except Exception as exc:  # pyzotero raises several HTTP-specific errors.
            errors.append(str(exc))
            continue
        created += len(response.get("successful", response.get("success", {})))
        failed = response.get("failed", {})
        for failure in failed.values():
            errors.append(str(failure))

    return ZoteroImportResult(created=created, skipped=0, errors=errors)


def _paper_to_zotero_item(paper: Paper, collection_key: str = "") -> dict:
    return {
        "itemType": "journalArticle",
        "title": paper.title,
        "creators": [{"creatorType": "author", "name": name} for name in paper.authors],
        "abstractNote": paper.abstract or "",
        "publicationTitle": paper.venue or "",
        "date": str(paper.year or ""),
        "DOI": paper.doi or "",
        "url": paper.url or paper.pdf_url or "",
        "tags": [{"tag": tag} for tag in sorted(set(paper.tags + paper.sources))],
        "extra": _extra(paper),
        "collections": [collection_key] if collection_key else [],
    }


def _extra(paper: Paper) -> str:
    lines = []
    if paper.pdf_url:
        lines.append(f"PDF URL: {paper.pdf_url}")
    if paper.external_id:
        lines.append(f"External ID: {paper.external_id}")
    if paper.cited_by_count is not None:
        lines.append(f"Cited by: {paper.cited_by_count}")
    if paper.score is not None:
        lines.append(f"Search score: {paper.score}")
    return "\n".join(lines)
