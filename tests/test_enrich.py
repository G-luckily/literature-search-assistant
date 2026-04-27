from litassist.config import GeneralConfig
from litassist.enrich import clean_pdf_links, filter_low_quality, score_relevance
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
    assert paper.relevance_score >= 3.0
    assert any("核心技术(标题)" in r for r in paper.relevance_reasons)


def test_score_relevance_does_not_reward_unmatched_citation_count():
    plan = build_plan("人工智能辅助文献检索")
    paper = Paper(
        title="Unrelated high citation paper",
        source="openalex",
        cited_by_count=5000,
        doi="10.1234/unrelated",
    )

    score_relevance([paper], plan)

    assert paper.relevance_score is not None
    assert paper.relevance_score >= 0  # clamped to 0, but reasons exist


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
    assert paper.relevance_score >= 3.0


def test_score_relevance_multi_category_combined():
    """Test that papers matching tech + population + phenomenon get a bonus."""
    plan = build_plan(
        "人工智能对老年人情感陪伴的影响",
        en_keywords=["artificial intelligence", "older adult", "companionship"],
    )
    paper = Paper(
        title="AI companionship for older adults: a review",
        source="openalex",
        abstract="This review examines how artificial intelligence provides emotional support "
        "and companionship for elderly people through social robots.",
        doi="10.1234/multi",
    )

    score_relevance([paper], plan)

    assert paper.relevance_score is not None
    assert paper.relevance_score >= 8.0
    assert any("交叉匹配" in r for r in paper.relevance_reasons)
    assert any("综合匹配" in r for r in paper.relevance_reasons)


def test_score_relevance_penalizes_irrelevant_domain():
    """Test that smart campus / education tech papers get penalized."""
    plan = build_plan("人工智能辅助文献检索")
    paper = Paper(
        title="Research on smart campus and intelligent education system based on AI",
        source="openalex",
        abstract="This paper discusses smart campus, intelligent education, "
        "and teaching model design using artificial intelligence.",
    )

    score_relevance([paper], plan)

    assert paper.relevance_score is not None
    assert any("降权" in r or "惩罚" in r for r in paper.relevance_reasons)


def test_filter_low_quality_removes_zero_score():
    """Papers with relevance_score <= 0 are removed."""
    papers = [
        Paper(title="Good paper", source="openalex", relevance_score=5.0),
        Paper(title="Bad paper", source="openalex", relevance_score=0),
    ]

    result = filter_low_quality(papers)

    assert len(result) == 1
    assert result[0].title == "Good paper"


def test_filter_low_quality_removes_short_title():
    """Papers with very short titles are removed."""
    papers = [
        Paper(title="A", source="crossref", relevance_score=2.0),
        Paper(title="Good paper", source="crossref", relevance_score=2.0),
    ]

    result = filter_low_quality(papers)

    assert len(result) == 1
    assert result[0].title == "Good paper"


def test_filter_low_quality_keeps_matched_low_score():
    """Papers with title match and score >= 1.0 are kept."""
    papers = [
        Paper(
            title="AI for elderly care",
            source="crossref",
            relevance_score=1.0,
            relevance_reasons=["核心技术(标题):1"],
        ),
    ]

    result = filter_low_quality(papers)

    assert len(result) == 1
