from datetime import date

from litassist.config import AppConfig, GeneralConfig, SemanticScholarConfig
from litassist.models import Paper
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


def test_filter_low_relevance_keeps_positive_matches_when_available():
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
    second = run_search(
        "人工智能辅助文献检索",
        config=config,
        sources=["semantic_scholar"],
        limit=5,
        state_root=tmp_path,
    )

    assert calls["count"] == 1
    assert first.source_meta["semantic_scholar"]["used_cache"] is False
    assert second.source_meta["semantic_scholar"]["used_cache"] is True
    assert first.source_meta["semantic_scholar"]["remaining_this_month"] == 249
    assert second.source_meta["semantic_scholar"]["remaining_this_month"] == 249


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
