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
                "query_round_count": 2,
                "successful_rounds": 2,
                "retrieved_before_dedupe": 3,
                "unique_before_dedupe": 2,
                "budget_status": "warning",
                "remaining_this_month": 12,
                "used_cache": True,
                "warning_message": "Semantic Scholar is in warning mode.",
                "round_stats": [
                    {
                        "round": 1,
                        "query": "artificial intelligence zotero",
                        "limit": 8,
                        "retrieved_count": 2,
                        "new_unique_count": 2,
                        "cumulative_unique_count": 2,
                    },
                    {
                        "round": 2,
                        "query": "research workflow",
                        "limit": 5,
                        "retrieved_count": 1,
                        "new_unique_count": 0,
                        "cumulative_unique_count": 2,
                    },
                ],
            }
        },
    )

    rendered = render_markdown(run)

    assert "Useful Paper" in rendered
    assert "Total after dedupe: 1" in rendered
    assert "Research Questions" in rendered
    assert "Source Metadata" in rendered
    assert "expansion 2" in rendered
    assert "rounds=2/2 | retrieved=3 | unique=2" in rendered
    assert "round 1 | limit=8 | hits=2 | new=2 | cumulative=2" in rendered
