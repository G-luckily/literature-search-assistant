from __future__ import annotations

from typing import Any


def papers_to_bibtex(papers: list[dict[str, Any]]) -> str:
    entries: list[str] = []
    for paper in papers:
        cite_key = _cite_key(paper)
        authors = _bibtex_authors(paper.get("authors") or [])
        title = _bibtex_escape(paper.get("title") or "Untitled")
        year = paper.get("year") or ""
        venue = _bibtex_escape(paper.get("venue") or "")
        doi = paper.get("doi") or ""
        url = paper.get("url") or ""
        abstract = _bibtex_escape(paper.get("abstract") or "")

        fields = [
            f"  author = {{{authors}}}",
            f"  title = {{{title}}}",
        ]
        if year:
            fields.append(f"  year = {{{year}}}")
        if venue:
            fields.append(f"  journal = {{{venue}}}")
        if doi:
            fields.append(f"  doi = {{{doi}}}")
        if url:
            fields.append(f"  url = {{{url}}}")
        if abstract:
            truncated = abstract[:500]
            fields.append(f"  abstract = {{{truncated}}}")

        entries.append(
            "@article{" + cite_key + ",\n" + ",\n".join(fields) + "\n}\n"
        )
    return "\n".join(entries)


def papers_to_csv(papers: list[dict[str, Any]]) -> str:
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Title",
            "Authors",
            "Year",
            "Venue",
            "DOI",
            "URL",
            "Abstract",
            "Cited By",
            "Source",
        ]
    )
    for paper in papers:
        writer.writerow(
            [
                paper.get("title") or "",
                "; ".join(paper.get("authors") or []),
                paper.get("year") or "",
                paper.get("venue") or "",
                paper.get("doi") or "",
                paper.get("url") or "",
                (paper.get("abstract") or "")[:500],
                paper.get("cited_by_count") or "",
                "; ".join(paper.get("sources") or [paper.get("source") or ""]),
            ]
        )
    return output.getvalue()


def papers_to_ris(papers: list[dict[str, Any]]) -> str:
    entries: list[str] = []
    for paper in papers:
        authors = paper.get("authors") or []
        title = paper.get("title") or "Untitled"
        year = paper.get("year") or ""
        venue = paper.get("venue") or ""
        doi = paper.get("doi") or ""
        url = paper.get("url") or ""
        abstract = paper.get("abstract") or ""

        entry = ["TY  - JOUR"]
        for author in authors:
            entry.append(f"AU  - {author}")
        entry.append(f"TI  - {title}")
        if year:
            entry.append(f"PY  - {year}")
        if venue:
            entry.append(f"JF  - {venue}")
        if doi:
            entry.append(f"DO  - {doi}")
        if url:
            entry.append(f"UR  - {url}")
        if abstract:
            entry.append(f"AB  - {abstract[:500]}")
        entry.append("ER  - ")
        entries.append("\n".join(entry))
    return "\n".join(entries)


def _cite_key(paper: dict[str, Any]) -> str:
    authors = paper.get("authors") or []
    surname = authors[0].split()[-1] if authors else "Unknown"
    year = paper.get("year") or "0000"
    title = paper.get("title") or ""
    words = title.split()[:3]
    short = "".join(w[0] for w in words if w) if words else "Untitled"
    return f"{surname}{year}{short}"


def _bibtex_authors(authors: list[str]) -> str:
    return " and ".join(authors[:20]) if authors else "Unknown"


def _bibtex_escape(text: str) -> str:
    return text.replace("&", "\\&").replace("{", "\\{").replace("}", "\\}").replace("#", "\\#")
