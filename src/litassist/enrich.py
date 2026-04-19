from __future__ import annotations

import re
from typing import Any

import httpx

from .config import GeneralConfig
from .models import Paper, ResearchPlan


PDF_HINTS = (".pdf", "/pdf", "type=printable", "format=pdf")
BAD_PDF_HINTS = (".jpg", ".jpeg", ".png", ".gif", ".svg", "image/")


def enrich_papers(
    papers: list[Paper],
    plan: ResearchPlan,
    config: GeneralConfig,
    use_unpaywall: bool = True,
) -> list[Paper]:
    score_relevance(papers, plan)
    clean_pdf_links(papers)
    if use_unpaywall:
        enrich_open_access_links(papers, config)
    return papers


def score_relevance(papers: list[Paper], plan: ResearchPlan) -> None:
    terms = _query_terms(plan)
    for paper in papers:
        haystack = " ".join(
            value
            for value in [
                paper.title,
                paper.abstract or "",
                paper.venue or "",
                " ".join(paper.authors),
            ]
            if value
        ).lower()
        title_text = (paper.title or "").lower()
        matched = []
        match_score = 0.0
        for term in terms:
            normalized = term.lower()
            if not normalized:
                continue
            if normalized in title_text:
                match_score += 3.0
                matched.append(f"title:{term}")
            elif normalized in haystack:
                match_score += 1.0
                matched.append(f"text:{term}")
        score = match_score
        if paper.doi:
            score += 0.25 if match_score else 0
        if paper.pdf_url:
            score += 0.25 if match_score else 0
        if paper.cited_by_count and match_score:
            score += min(paper.cited_by_count / 500, 1.5)
        paper.relevance_score = round(score, 3)
        paper.relevance_reasons = matched[:8]


def clean_pdf_links(papers: list[Paper]) -> None:
    for paper in papers:
        if paper.pdf_url and not looks_like_pdf_url(paper.pdf_url):
            paper.raw["discarded_pdf_url"] = paper.pdf_url
            paper.pdf_url = None


def enrich_open_access_links(papers: list[Paper], config: GeneralConfig) -> None:
    dois = sorted({paper.doi for paper in papers if paper.doi})
    if not dois:
        return
    headers = {"User-Agent": config.user_agent}
    params = {}
    if config.contact_email:
        params["email"] = config.contact_email

    try:
        with httpx.Client(timeout=config.request_timeout_seconds, headers=headers) as client:
            for doi in dois:
                response = client.get(
                    f"https://api.unpaywall.org/v2/{doi}",
                    params=params,
                )
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                payload = response.json()
                _apply_unpaywall(papers, doi, payload)
    except httpx.HTTPError:
        return


def looks_like_pdf_url(url: str) -> bool:
    lowered = url.lower()
    if any(hint in lowered for hint in BAD_PDF_HINTS):
        return False
    return any(hint in lowered for hint in PDF_HINTS)


def _apply_unpaywall(papers: list[Paper], doi: str, payload: dict[str, Any]) -> None:
    best = payload.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf") or best.get("url")
    landing_url = best.get("url_for_landing_page")
    is_oa = payload.get("is_oa")
    oa_status = payload.get("oa_status")
    for paper in papers:
        if not paper.doi or paper.doi.lower() != doi.lower():
            continue
        if oa_status:
            paper.oa_status = oa_status
        elif is_oa is not None:
            paper.oa_status = "oa" if is_oa else "closed"
        if pdf_url and looks_like_pdf_url(pdf_url):
            paper.pdf_url = paper.pdf_url or pdf_url
        if landing_url:
            paper.url = paper.url or landing_url


def _query_terms(plan: ResearchPlan) -> list[str]:
    raw_terms = plan.zh_keywords + plan.en_keywords
    terms: list[str] = []
    seen = set()
    for term in raw_terms:
        cleaned = re.sub(r"\s+", " ", term.strip())
        key = cleaned.lower()
        if len(cleaned) < 2 or key in seen:
            continue
        seen.add(key)
        terms.append(cleaned)
    return terms
