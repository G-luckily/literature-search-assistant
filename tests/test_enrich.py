from litassist.config import GeneralConfig
from litassist.enrich import clean_pdf_links, score_relevance
from litassist.models import Paper
from litassist.planner import build_plan


def test_clean_pdf_links_discards_image_urls():
    paper = Paper(
        title="Image masquerading as PDF",
        source="openalex",
        pdf_url="https://example.org/graph.jpg",
    )

    clean_pdf_links([paper])

    assert paper.pdf_url is None
    assert paper.raw["discarded_pdf_url"] == "https://example.org/graph.jpg"


def test_score_relevance_prefers_title_matches():
    plan = build_plan(
        "人工智能辅助文献检索",
        en_keywords=["artificial intelligence", "literature retrieval"],
    )
    paper = Paper(
        title="Artificial intelligence for literature retrieval",
        source="openalex",
        abstract="A general article.",
        doi="10.1234/example",
    )

    score_relevance([paper], plan)

    assert paper.relevance_score is not None
    assert paper.relevance_score >= 6
    assert "title:artificial intelligence" in paper.relevance_reasons


def test_score_relevance_does_not_reward_unmatched_citation_count():
    plan = build_plan("人工智能辅助文献检索")
    paper = Paper(
        title="Unrelated high citation paper",
        source="openalex",
        cited_by_count=5000,
        doi="10.1234/unrelated",
    )

    score_relevance([paper], plan)

    assert paper.relevance_score == 0
    assert paper.relevance_reasons == []


def test_score_relevance_rewards_recent_matched_papers():
    plan = build_plan(
        "人工智能辅助文献检索",
        en_keywords=["artificial intelligence", "literature retrieval"],
    )
    paper = Paper(
        title="Artificial intelligence for literature retrieval",
        source="openalex",
        year=2025,
    )

    score_relevance([paper], plan, GeneralConfig(from_year=2022))

    assert paper.relevance_score is not None
    assert paper.relevance_score > 6
