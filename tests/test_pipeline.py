from datetime import date

from litassist.models import Paper
from litassist.pipeline import _filter_by_year, _filter_low_relevance


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
