from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .models import Paper


def dedupe_papers(papers: list[Paper], prefer_recent: bool = True) -> list[Paper]:
    merged: dict[str, Paper] = {}
    order: list[str] = []

    for paper in papers:
        key = paper_identity_key(paper)
        if key not in merged:
            merged[key] = paper
            order.append(key)
            continue
        merged[key] = _merge_into_target(merged[key], paper)

    result = [merged[key] for key in order]
    result.sort(
        key=lambda paper: _rank_key(paper, prefer_recent=prefer_recent),
        reverse=True,
    )
    return result


def paper_identity_key(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{_normalize_doi(paper.doi)}"
    return f"title:{_normalize_title(paper.title)}"


def _normalize_doi(value: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", value.strip().lower())


def _normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def _merge_into_target(target: Paper, source: Paper) -> Paper:
    kwargs: dict[str, Any] = {}
    for field_name in ("abstract", "doi", "url", "pdf_url", "venue", "external_id"):
        if not getattr(target, field_name) and getattr(source, field_name):
            kwargs[field_name] = getattr(source, field_name)

    if not target.authors and source.authors:
        kwargs["authors"] = source.authors
    if target.year is None and source.year is not None:
        kwargs["year"] = source.year
    if source.cited_by_count is not None:
        kwargs["cited_by_count"] = max(
            target.cited_by_count or 0, source.cited_by_count
        )
    if source.score is not None:
        kwargs["score"] = max(target.score or 0, source.score)
    if source.relevance_score is not None:
        kwargs["relevance_score"] = max(
            target.relevance_score or 0, source.relevance_score
        )
    if source.relevance_reasons:
        kwargs["relevance_reasons"] = sorted(
            set(target.relevance_reasons + source.relevance_reasons)
        )
    if not target.oa_status and source.oa_status:
        kwargs["oa_status"] = source.oa_status

    return replace(
        target,
        sources=sorted(set(target.sources + source.sources)),
        tags=(
            sorted(set(target.tags + source.tags))
            if target.tags or source.tags
            else target.tags
        ),
        **kwargs,
    )


def _rank_key(paper: Paper, prefer_recent: bool) -> tuple[float, int, int, int, int]:
    score = (
        paper.relevance_score if paper.relevance_score is not None else paper.score or 0
    )
    year = paper.year or 0
    source_count = len(paper.sources)
    has_pdf = 1 if paper.pdf_url else 0
    cites = paper.cited_by_count or 0
    if prefer_recent:
        return year, score, source_count, has_pdf, cites
    return score, cites, source_count, has_pdf, year
