from datetime import date

from litassist.config import AppConfig, GeneralConfig, SemanticScholarConfig
from litassist.models import Paper, ResearchPlan
from litassist.pipeline import _filter_by_year, _filter_low_relevance, run_search


def test_filter_by_year_removes_old_and_future_metadata():
    current_year = date.today().year
    papers = [
        Paper(title="Old", source="crossref", year=2021),
        Paper(title="Current", source="crossref", year=current_year),
        Paper(title="Future", source="crossref", year=current_year + 50),
        Paper(title="Unknown", source="crossref", year=None),
    ]

    result = _filter_by_year(papers, from_year=current_year - 1)

    assert [paper.title for paper in result] == ["Current", "Unknown"]


def test_filter_low_relevance_removes_low_quality():
    papers = [
        Paper(title="Noise", source="crossref", relevance_score=0),
        Paper(title="Match", source="crossref", relevance_score=2),
    ]

    result = _filter_low_relevance(papers)

    assert [paper.title for paper in result] == ["Match"]


def test_semantic_scholar_reuses_cache_without_incrementing_budget(
    monkeypatch,
    tmp_path,
):
    calls = {"count": 0}

    def fake_search_items(self, query, limit):
        calls["count"] += 1
        return [
            {
                "title": "Semantic Result",
                "authors": [{"name": "Alice"}],
                "year": 2024,
                "paperId": "paper-1",
                "citationCount": 5,
                "externalIds": {"DOI": "10.1/example"},
            }
        ]

    monkeypatch.setattr(
        "litassist.search.semantic_scholar.SemanticScholarSearcher.search_items",
        fake_search_items,
    )
    config = AppConfig(
        general=GeneralConfig(enabled_sources=["semantic_scholar"]),
        semantic_scholar=SemanticScholarConfig(api_key="test-key"),
    )

    first = run_search(
        "人工智能辅助文献检索",
        config=config,
        sources=["semantic_scholar"],
        limit=5,
        state_root=tmp_path,
    )
    first_calls = calls["count"]
    assert first_calls > 0
    assert first.source_meta["semantic_scholar"]["used_cache"] is False

    second = run_search(
        "人工智能辅助文献检索",
        config=config,
        sources=["semantic_scholar"],
        limit=5,
        state_root=tmp_path,
    )

    assert calls["count"] == first_calls
    assert second.source_meta["semantic_scholar"]["used_cache"] is True


def test_semantic_scholar_warning_budget_allows_live_request(monkeypatch, tmp_path):
    def fake_search_items(self, query, limit):
        return [{"title": "Semantic Result", "year": 2024, "paperId": "paper-1"}]

    monkeypatch.setattr(
        "litassist.search.semantic_scholar.SemanticScholarSearcher.search_items",
        fake_search_items,
    )
    config = AppConfig(
        general=GeneralConfig(enabled_sources=["semantic_scholar"]),
        semantic_scholar=SemanticScholarConfig(
            api_key="test-key",
            monthly_search_budget=30,
            warning_remaining=50,
            cache_only_remaining=25,
        ),
    )

    run = run_search(
        "人工智能辅助文献检索",
        config=config,
        sources=["semantic_scholar"],
        state_root=tmp_path,
    )

    meta = run.source_meta["semantic_scholar"]
    assert meta["budget_status"] == "warning"
    assert meta["warning_message"]
    assert "semantic_scholar" not in run.errors


def test_semantic_scholar_cache_only_mode_skips_live_request(monkeypatch, tmp_path):
    calls = {"count": 0}

    def fake_search_items(self, query, limit):
        calls["count"] += 1
        return [{"title": "Semantic Result", "year": 2024, "paperId": "paper-1"}]

    monkeypatch.setattr(
        "litassist.search.semantic_scholar.SemanticScholarSearcher.search_items",
        fake_search_items,
    )
    config = AppConfig(
        general=GeneralConfig(enabled_sources=["semantic_scholar"]),
        semantic_scholar=SemanticScholarConfig(
            api_key="test-key",
            monthly_search_budget=25,
            warning_remaining=50,
            cache_only_remaining=25,
        ),
    )

    run = run_search(
        "人工智能辅助文献检索",
        config=config,
        sources=["semantic_scholar"],
        state_root=tmp_path,
    )

    assert calls["count"] == 0
    assert "semantic_scholar" in run.errors
    assert run.source_meta["semantic_scholar"]["budget_status"] == "cache_only"


def test_run_search_executes_expansion_rounds_for_openalex(monkeypatch):
    calls: list[tuple[str, int]] = []

    def fake_search(self, query, limit):
        calls.append((query, limit))
        if len(calls) == 1:
            return [
                Paper(
                    title="人工智能 Primary Result",
                    source="openalex",
                    year=2024,
                    doi="10.1/primary",
                )
            ]
        return [
            Paper(
                title="人工智能 Expansion Result",
                source="openalex",
                year=2023,
                doi="10.1/expansion",
            )
        ]

    monkeypatch.setattr(
        "litassist.search.openalex.OpenAlexSearcher.search", fake_search
    )
    config = AppConfig(
        general=GeneralConfig(enabled_sources=["openalex"], from_year=None)
    )

    run = run_search(
        "人工智能辅助文献检索与Zotero协同管理",
        config=config,
        sources=["openalex"],
        limit=8,
    )

    assert len(calls) >= 2
    assert calls[0][1] == 8
    assert calls[1][1] == 5
    assert {paper.title for paper in run.papers} == {
        "人工智能 Primary Result",
        "人工智能 Expansion Result",
    }
    assert run.source_meta["openalex"]["successful_rounds"] >= 2


def test_run_search_tracks_round_contribution_stats(monkeypatch):
    def fake_build_search_plan(need, **kwargs):
        return ResearchPlan(
            need=need,
            zh_keywords=["人工智能"],
            en_keywords=["artificial intelligence"],
            queries={"openalex": "primary query"},
            query_rounds={
                "openalex": [
                    "primary query",
                    "secondary query",
                    "tertiary query",
                ]
            },
        )

    def fake_search(self, query, limit):
        items = {
            "primary query": [
                Paper(title="人工智能 Primary Result", source="openalex", year=2024),
                Paper(title="人工智能 Secondary Result", source="openalex", year=2023),
            ],
            "secondary query": [
                Paper(title="人工智能 Primary Result", source="openalex", year=2024),
                Paper(title="人工智能 Third Result", source="openalex", year=2022),
            ],
            "tertiary query": [
                Paper(title="人工智能 Third Result", source="openalex", year=2022),
                Paper(title="人工智能 Fourth Result", source="openalex", year=2021),
            ],
        }
        return items[query]

    monkeypatch.setattr("litassist.pipeline._build_search_plan", fake_build_search_plan)
    monkeypatch.setattr(
        "litassist.search.openalex.OpenAlexSearcher.search", fake_search
    )
    config = AppConfig(
        general=GeneralConfig(enabled_sources=["openalex"], from_year=None)
    )

    run = run_search(
        "人工智能辅助文献检索",
        config=config,
        sources=["openalex"],
        limit=6,
    )

    stats = run.source_meta["openalex"]["round_stats"]

    assert run.source_meta["openalex"]["query_round_count"] == 3
    assert run.source_meta["openalex"]["successful_rounds"] == 3
    assert run.source_meta["openalex"]["retrieved_before_dedupe"] == 6
    assert run.source_meta["openalex"]["unique_before_dedupe"] == 4
    assert [item["limit"] for item in stats] == [6, 5, 5]
    assert [
        (
            item["retrieved_count"],
            item["new_unique_count"],
            item["cumulative_unique_count"],
        )
        for item in stats
    ] == [(2, 2, 2), (2, 1, 3), (2, 1, 4)]
    assert {paper.title for paper in run.papers} == {
        "人工智能 Primary Result",
        "人工智能 Secondary Result",
        "人工智能 Third Result",
        "人工智能 Fourth Result",
    }
