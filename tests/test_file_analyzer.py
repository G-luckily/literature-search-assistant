from __future__ import annotations

import base64

import pytest

from litassist.config import LLMConfig
from litassist.file_analyzer import (
    FileAnalysisError,
    FileAnalysisResult,
    _analyze_text,
    _analyze_text_with_llm,
    _parse_search_dimensions,
    _parse_suggested_queries,
    _text_analysis_prompt,
    analyze_file,
)


def test_analyze_text_file():
    text = "This is a research paper about artificial intelligence and machine learning for elderly care."
    content = base64.b64encode(text.encode()).decode()
    result = _analyze_text(content)
    assert isinstance(result, FileAnalysisResult)
    assert "artificial intelligence" in result.description
    assert "research" in result.keywords_en
    assert "machine" in result.keywords_en


def test_analyze_text_chinese():
    text = "本文研究人工智能在老年人情感陪伴中的应用，探讨大语言模型与社交机器人的交互效果。"
    content = base64.b64encode(text.encode()).decode()
    result = _analyze_text(content)
    assert isinstance(result, FileAnalysisResult)
    assert "人工智能" in result.description or "人工智能" in result.keywords_zh


def test_analyze_empty_text():
    content = base64.b64encode(b"").decode()
    with pytest.raises(Exception, match="empty"):
        _analyze_text(content)


def test_analyze_text_truncated():
    long_text = "Hello world. " * 200
    content = base64.b64encode(long_text.encode()).decode()
    result = _analyze_text(content)
    assert len(result.description) <= 610  # 600 + ellipsis
    assert result.description.endswith("…")


def test_analyze_unsupported_format():
    content = base64.b64encode(b"test").decode()
    config = LLMConfig()
    with pytest.raises(Exception, match="Unsupported"):
        analyze_file("test.bin", content, "application/octet-stream", config)


def test_file_analysis_result_dataclass():
    result = FileAnalysisResult(
        description="Test description",
        keywords_zh=["人工智能", "机器学习"],
        keywords_en=["AI", "ML"],
        source_text="full text here",
    )
    assert result.description == "Test description"
    assert result.keywords_zh == ["人工智能", "机器学习"]
    assert result.keywords_en == ["AI", "ML"]
    assert result.source_text == "full text here"


def test_text_analysis_prompt_is_well_formed():
    prompt = _text_analysis_prompt()
    assert len(prompt) > 200
    assert "description" in prompt
    assert "keywords_zh" in prompt
    assert "keywords_en" in prompt
    assert "research_questions" in prompt


def test_analyze_text_with_llm_raises_without_api_key():
    config = LLMConfig()
    config.enabled = True
    config.api_key = ""
    with pytest.raises(FileAnalysisError, match="LLM text analysis requires"):
        _analyze_text_with_llm("some research text", config)


def test_analyze_pdf_falls_through_to_regex_without_llm():
    """PDF with extractable text should work via regex when LLM is unavailable."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 100),
        "Deep Learning for Medical Image Segmentation using Transformer Architectures",
        fontsize=14,
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    content = base64.b64encode(pdf_bytes).decode()
    config = LLMConfig()
    config.enabled = False
    config.api_key = ""

    result = analyze_file("test.pdf", content, "application/pdf", config)
    assert isinstance(result, FileAnalysisResult)
    assert "Deep Learning" in result.description
    assert result.keywords_en


def test_parse_search_dimensions_valid():
    dims = [
        {
            "name": "技术方法",
            "name_en": "Technical Methods",
            "zh_terms": ["深度学习", "卷积神经网络"],
            "en_terms": ["deep learning", "CNN"],
        },
        {
            "name": "应用场景",
            "name_en": "Application",
            "zh_terms": ["医学影像", "病理分析"],
            "en_terms": ["medical imaging"],
        },
    ]
    result = _parse_search_dimensions(dims)
    assert result is not None
    assert len(result) == 2
    assert result[0]["name"] == "技术方法"
    assert result[0]["en_terms"] == ["deep learning", "CNN"]
    assert result[1]["zh_terms"] == ["医学影像", "病理分析"]


def test_parse_search_dimensions_invalid():
    assert _parse_search_dimensions(None) is None
    assert _parse_search_dimensions("not a list") is None
    assert _parse_search_dimensions([{"no_name": "test"}]) is None
    assert _parse_search_dimensions([{"name": ""}]) is None


def test_parse_suggested_queries_valid():
    queries = {
        "openalex": "deep learning medical imaging",
        "cnki": "深度学习 医学影像",
        "crossref": "deep learning medical",
    }
    result = _parse_suggested_queries(queries)
    assert result is not None
    assert result["openalex"] == "deep learning medical imaging"
    assert result["cnki"] == "深度学习 医学影像"
    assert "web_of_science" not in result


def test_parse_suggested_queries_invalid():
    assert _parse_suggested_queries(None) is None
    assert _parse_suggested_queries({}) is None
    assert _parse_suggested_queries({"openalex": ""}) is None


def test_text_analysis_prompt_includes_search_dimensions():
    prompt = _text_analysis_prompt()
    assert "search_dimensions" in prompt
    assert "suggested_queries" in prompt
    assert "zh_terms" in prompt
    assert "en_terms" in prompt
