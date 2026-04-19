from litassist.dedupe import dedupe_papers
from litassist.models import Paper


def test_dedupe_merges_by_doi():
    papers = [
        Paper(title="A Paper", source="openalex", doi="https://doi.org/10.1/ABC"),
        Paper(
            title="A Paper",
            source="crossref",
            doi="10.1/abc",
            pdf_url="https://example.org/a.pdf",
        ),
    ]

    result = dedupe_papers(papers)

    assert len(result) == 1
    assert result[0].pdf_url == "https://example.org/a.pdf"
    assert result[0].sources == ["crossref", "openalex"]


def test_dedupe_falls_back_to_title():
    papers = [
        Paper(title="Same Title!", source="openalex"),
        Paper(title="same title", source="semantic_scholar"),
    ]

    assert len(dedupe_papers(papers)) == 1


def test_dedupe_ranking_keeps_zero_relevance_below_matches():
    papers = [
        Paper(
            title="High source score but no query match",
            source="openalex",
            score=99,
            relevance_score=0,
        ),
        Paper(
            title="Relevant paper",
            source="openalex",
            score=1,
            relevance_score=2,
        ),
    ]

    assert dedupe_papers(papers)[0].title == "Relevant paper"
