from litassist.models import Paper
from litassist.pipeline import SearchRun
from litassist.planner import build_plan
from litassist.report import render_markdown


def test_render_markdown_contains_results():
    run = SearchRun(
        plan=build_plan("人工智能 文献检索"),
        papers=[Paper(title="Useful Paper", source="openalex", year=2024)],
        errors={},
    )

    rendered = render_markdown(run)

    assert "Useful Paper" in rendered
    assert "Total after dedupe: 1" in rendered
    assert "Research Questions" in rendered
