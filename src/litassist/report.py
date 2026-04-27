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
    write_json(target / "source_meta.json", run.source_meta)
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
        for round_index, round_query in enumerate(
            plan.query_rounds.get(source, [])[1:],
            start=2,
        ):
            lines.append(f"- `{source}` expansion {round_index}: {round_query}")

    if plan.research_questions:
        lines.extend(["", "## Research Questions", ""])
        for question in plan.research_questions:
            lines.append(f"- {question}")

    if plan.core_concepts:
        lines.extend(["", "## Core Concepts", ""])
        for concept in plan.core_concepts:
            label = " / ".join(
                item
                for item in [concept.get("label_zh"), concept.get("label_en")]
                if item
            )
            zh_syn = ", ".join(concept.get("synonyms_zh", []))
            en_syn = ", ".join(concept.get("synonyms_en", []))
            suffix = "; ".join(item for item in [zh_syn, en_syn] if item)
            lines.append(f"- {label}{': ' + suffix if suffix else ''}")

    if plan.inclusion_criteria or plan.exclusion_criteria:
        lines.extend(["", "## Screening Criteria", ""])
        if plan.inclusion_criteria:
            lines.append("Inclusion:")
            for item in plan.inclusion_criteria:
                lines.append(f"- {item}")
        if plan.exclusion_criteria:
            lines.append("Exclusion:")
            for item in plan.exclusion_criteria:
                lines.append(f"- {item}")

    if run.errors:
        lines.extend(["", "## Source Errors", ""])
        for source, error in run.errors.items():
            lines.append(f"- `{source}`: {error}")

    if run.source_meta:
        lines.extend(["", "## Source Metadata", ""])
        for source, meta in run.source_meta.items():
            lines.append(_source_meta_line(source, meta))
            for round_meta in meta.get("round_stats", []):
                if isinstance(round_meta, dict):
                    lines.append(_source_round_line(source, round_meta))

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
        f"- OA Status: {paper.oa_status or ''}",
        f"- Citations: {paper.cited_by_count if paper.cited_by_count is not None else ''}",
        f"- Score: {paper.score if paper.score is not None else ''}",
        f"- Relevance: {paper.relevance_score if paper.relevance_score is not None else ''}",
        "",
    ]
    if paper.relevance_reasons:
        lines.extend(["Matched terms:", "", ", ".join(paper.relevance_reasons), ""])
    if paper.abstract:
        lines.extend(["Abstract:", "", paper.abstract[:1200], ""])
    return lines


def _source_meta_line(source: str, meta: dict[str, object]) -> str:
    fragments = [f"`{source}`"]
    query_round_count = meta.get("query_round_count")
    if query_round_count is not None:
        fragments.append(
            f"rounds={meta.get('successful_rounds', 0)}/{query_round_count}"
        )
    if meta.get("retrieved_before_dedupe") is not None:
        fragments.append(f"retrieved={meta['retrieved_before_dedupe']}")
    if meta.get("unique_before_dedupe") is not None:
        fragments.append(f"unique={meta['unique_before_dedupe']}")
    if meta.get("budget_status"):
        fragments.append(f"status={meta['budget_status']}")
    if meta.get("remaining_this_month") is not None:
        fragments.append(f"remaining={meta['remaining_this_month']}")
    if meta.get("used_cache"):
        fragments.append("cache=hit")
    if meta.get("warning_message"):
        fragments.append(str(meta["warning_message"]))
    return "- " + " | ".join(fragments)


def _source_round_line(source: str, round_meta: dict[str, object]) -> str:
    fragments = [f"`{source}` round {round_meta.get('round', '?')}"]
    if round_meta.get("limit") is not None:
        fragments.append(f"limit={round_meta['limit']}")
    if round_meta.get("retrieved_count") is not None:
        fragments.append(f"hits={round_meta['retrieved_count']}")
    if round_meta.get("new_unique_count") is not None:
        fragments.append(f"new={round_meta['new_unique_count']}")
    if round_meta.get("cumulative_unique_count") is not None:
        fragments.append(f"cumulative={round_meta['cumulative_unique_count']}")
    if round_meta.get("error"):
        fragments.append(f"error={round_meta['error']}")
    return "- " + " | ".join(fragments)
