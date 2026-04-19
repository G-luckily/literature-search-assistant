from __future__ import annotations

import json
from pathlib import Path

from .models import Paper
from .pipeline import SearchRun


def write_run(run: SearchRun, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "search_plan.json", run.plan.to_dict())
    write_json(target / "papers.json", [paper.to_dict() for paper in run.papers])
    (target / "report.md").write_text(render_markdown(run), encoding="utf-8")


def write_json(path: str | Path, data) -> None:
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_papers(path: str | Path) -> list[Paper]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Paper(**item) for item in data]


def render_markdown(run: SearchRun) -> str:
    plan = run.plan
    lines = [
        "# Literature Search Report",
        "",
        "## Need",
        "",
        plan.need,
        "",
        "## Keywords",
        "",
        "- Chinese: " + ", ".join(plan.zh_keywords),
        "- English: " + ", ".join(plan.en_keywords),
        "",
        "## Queries",
        "",
    ]
    for source, query in plan.queries.items():
        lines.append(f"- `{source}`: {query}")

    if run.errors:
        lines.extend(["", "## Source Errors", ""])
        for source, error in run.errors.items():
            lines.append(f"- `{source}`: {error}")

    lines.extend(["", "## Results", "", f"Total after dedupe: {len(run.papers)}", ""])
    for index, paper in enumerate(run.papers, start=1):
        lines.extend(_paper_lines(index, paper))

    if plan.notes:
        lines.extend(["", "## Notes", ""])
        for note in plan.notes:
            lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


def _paper_lines(index: int, paper: Paper) -> list[str]:
    authors = ", ".join(paper.authors[:6])
    if len(paper.authors) > 6:
        authors += " et al."
    lines = [
        f"### {index}. {paper.title}",
        "",
        f"- Sources: {', '.join(paper.sources)}",
        f"- Year: {paper.year or ''}",
        f"- Authors: {authors}",
        f"- Venue: {paper.venue or ''}",
        f"- DOI: {paper.doi or ''}",
        f"- URL: {paper.url or ''}",
        f"- PDF: {paper.pdf_url or ''}",
        f"- Citations: {paper.cited_by_count if paper.cited_by_count is not None else ''}",
        f"- Score: {paper.score if paper.score is not None else ''}",
        "",
    ]
    if paper.abstract:
        lines.extend(["Abstract:", "", paper.abstract[:1200], ""])
    return lines
