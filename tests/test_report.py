from litassist.models import Paper
from litassist.pipeline import SearchRun
from litassist.planner import build_plan
from litassist.report import render_markdown


def test_render_markdown_contains_results():
    run = SearchRun(
        plan=build_plan("人工智能 文献检索"),
        papers=[Paper(title="Useful Paper", source="openalex", year=2024)],
        errors={},
        source_meta={
            "semantic_scholar": {
                "budget_status": "warning",
                "remaining_this_month": 12,
                "used_cache": True,
                "warning_message": "Semantic Scholar is in warning mode.",
            }
        },
    )

    rendered = render_markdown(run)

    assert "Useful Paper" in rendered
    assert "Total after dedupe: 1" in rendered
    assert "Research Questions" in rendered
    assert "Source Metadata" in rendered
