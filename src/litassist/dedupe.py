from __future__ import annotations

import re

from .models import Paper


def dedupe_papers(papers: list[Paper]) -> list[Paper]:
    merged: dict[str, Paper] = {}
    order: list[str] = []

    for paper in papers:
        key = _paper_key(paper)
        if key not in merged:
            merged[key] = paper
            order.append(key)
            continue
        merged[key] = _merge(merged[key], paper)

    result = [merged[key] for key in order]
    result.sort(key=_rank_key, reverse=True)
    return result


def _paper_key(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{_normalize_doi(paper.doi)}"
    return f"title:{_normalize_title(paper.title)}"


def _normalize_doi(value: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", value.strip().lower())


def _normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def _merge(left: Paper, right: Paper) -> Paper:
    left.sources = sorted(set(left.sources + right.sources))
    left.tags = sorted(set(left.tags + right.tags))

    for field_name in ("abstract", "doi", "url", "pdf_url", "venue", "external_id"):
        if not getattr(left, field_name) and getattr(right, field_name):
            setattr(left, field_name, getattr(right, field_name))

    if not left.authors and right.authors:
        left.authors = right.authors
    if left.year is None and right.year is not None:
        left.year = right.year
    if right.cited_by_count is not None:
        left.cited_by_count = max(left.cited_by_count or 0, right.cited_by_count)
    if right.score is not None:
        left.score = max(left.score or 0, right.score)
    if right.relevance_score is not None:
        left.relevance_score = max(left.relevance_score or 0, right.relevance_score)
    if right.relevance_reasons:
        left.relevance_reasons = sorted(
            set(left.relevance_reasons + right.relevance_reasons)
        )
    if not left.oa_status and right.oa_status:
        left.oa_status = right.oa_status
    return left


def _rank_key(paper: Paper) -> tuple[int, float, int, int, int]:
    score = paper.relevance_score if paper.relevance_score is not None else paper.score or 0
    year = paper.year or 0
    source_count = len(paper.sources)
    has_pdf = 1 if paper.pdf_url else 0
    cites = paper.cited_by_count or 0
    return year, score, source_count, has_pdf, cites
