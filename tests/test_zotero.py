from __future__ import annotations

from litassist.config import ZoteroConfig
from litassist.models import Paper
from litassist.zotero import ZoteroImportResult, _extra, _paper_to_zotero_item, import_papers


def test_paper_to_zotero_item_minimal():
    paper = Paper(title="Test Paper", source="openalex")
    item = _paper_to_zotero_item(paper)
    assert item["itemType"] == "journalArticle"
    assert item["title"] == "Test Paper"
    assert item["creators"] == []
    assert item["abstractNote"] == ""
    assert item["DOI"] == ""
    assert item["collections"] == []


def test_paper_to_zotero_item_full():
    paper = Paper(
        title="Deep Learning Survey",
        source="crossref",
        authors=["Alice Zhang", "Bob Li"],
        year=2024,
        venue="Nature AI",
        abstract="A comprehensive survey.",
        doi="10.1234/abc",
        url="https://example.com/paper",
        pdf_url="https://example.com/paper.pdf",
        external_id="EXTERNAL-001",
        cited_by_count=42,
        score=0.95,
        relevance_score=8.5,
        oa_status="gold",
        relevance_reasons=["核心技术", "交叉匹配"],
        tags=["tag1", "tag2"],
        sources=["crossref", "openalex"],
    )
    item = _paper_to_zotero_item(paper, collection_key="MY-COLLECTION")
    assert item["itemType"] == "journalArticle"
    assert item["title"] == "Deep Learning Survey"
    assert len(item["creators"]) == 2
    assert item["creators"][0] == {"creatorType": "author", "name": "Alice Zhang"}
    assert item["abstractNote"] == "A comprehensive survey."
    assert item["publicationTitle"] == "Nature AI"
    assert item["date"] == "2024"
    assert item["DOI"] == "10.1234/abc"
    assert item["url"] == "https://example.com/paper"
    assert item["collections"] == ["MY-COLLECTION"]
    tags = {t["tag"] for t in item["tags"]}
    assert "tag1" in tags
    assert "tag2" in tags
    assert "crossref" in tags
    assert "openalex" in tags


def test_paper_to_zotero_item_extra():
    paper = Paper(
        title="Test",
        source="semantic_scholar",
        pdf_url="https://example.com/paper.pdf",
        external_id="EXT-001",
        cited_by_count=10,
        score=0.9,
        relevance_score=7.2,
        oa_status="hybrid",
        relevance_reasons=["核心技术"],
    )
    result = _extra(paper)
    assert "PDF URL: https://example.com/paper.pdf" in result
    assert "External ID: EXT-001" in result
    assert "Cited by: 10" in result
    assert "Search score: 0.9" in result
    assert "Relevance score: 7.2" in result
    assert "OA status: hybrid" in result
    assert "Matched terms: 核心技术" in result


def test_import_papers_dry_run():
    papers = [
        Paper(title="Paper 1", source="openalex"),
        Paper(title="Paper 2", source="crossref"),
        Paper(title="Paper 3", source="openalex"),
    ]
    config = ZoteroConfig(library_id="123", api_key="secret")
    result = import_papers(papers, config, apply=False)
    assert isinstance(result, ZoteroImportResult)
    assert result.created == 0
    assert result.skipped == 3
    assert result.errors == []


def test_import_papers_dry_run_with_limit():
    papers = [
        Paper(title="Paper 1", source="openalex"),
        Paper(title="Paper 2", source="crossref"),
    ]
    config = ZoteroConfig(library_id="123", api_key="secret")
    result = import_papers(papers, config, limit=1, apply=False)
    assert result.skipped == 1


def test_import_papers_missing_config():
    papers = [Paper(title="Paper 1", source="openalex")]
    config = ZoteroConfig()
    result = import_papers(papers, config, apply=True)
    assert result.created == 0
    assert result.skipped == 0
    assert len(result.errors) == 1
    assert "library_id and api_key are required" in result.errors[0]


def test_paper_to_zotero_item_with_collection_key():
    paper = Paper(title="Test", source="openalex")
    item = _paper_to_zotero_item(paper, collection_key="MYCOL")
    assert item["collections"] == ["MYCOL"]


def test_paper_to_zotero_item_without_collection():
    paper = Paper(title="Test", source="openalex")
    item = _paper_to_zotero_item(paper, collection_key="")
    assert item["collections"] == []


def test_zotero_import_result_dataclass():
    result = ZoteroImportResult(created=5, skipped=2, errors=["err1"])
    assert result.created == 5
    assert result.skipped == 2
    assert result.errors == ["err1"]
