from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import LLMConfig


class FileAnalysisError(RuntimeError):
    pass


@dataclass(slots=True)
class FileAnalysisResult:
    description: str
    keywords_zh: list[str]
    keywords_en: list[str]
    source_text: str = ""
    search_dimensions: list[dict] | None = None
    suggested_queries: dict[str, str] | None = None


def analyze_file(
    filename: str,
    content_base64: str,
    mime_type: str,
    llm_config: LLMConfig,
) -> FileAnalysisResult:
    ext = Path(filename).suffix.lower()
    is_image = mime_type.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp"}
    is_text = mime_type.startswith("text/") or ext in {".txt", ".csv", ".json", ".md", ".py", ".js", ".html", ".css"}
    is_pdf = mime_type == "application/pdf" or ext == ".pdf"

    if is_image:
        return _analyze_image(filename, content_base64, mime_type, llm_config)
    if is_text:
        return _analyze_text(content_base64)
    if is_pdf:
        return _analyze_pdf(content_base64, llm_config)

    raise FileAnalysisError(
        f"Unsupported file type: {mime_type} (.{ext}). "
        "Supported types: images (png, jpg, webp), text files, PDFs."
    )


def _analyze_image(
    filename: str,
    content_base64: str,
    mime_type: str,
    llm_config: LLMConfig,
) -> FileAnalysisResult:
    if not llm_config.api_key or not llm_config.enabled:
        raise FileAnalysisError(
            "LLM vision analysis requires a configured LLM provider with API key. "
            "Please configure it in Settings."
        )

    data_uri = f"data:{mime_type};base64,{content_base64}"
    payload = _vision_payload(llm_config.model, data_uri)
    headers = {
        "Authorization": f"Bearer {llm_config.api_key}",
        "Content-Type": "application/json",
    }

    try:
        if llm_config.provider == "deepseek":
            endpoint = _chat_completions_endpoint(llm_config.endpoint)
        else:
            endpoint = llm_config.endpoint

        with httpx.Client(timeout=min(llm_config.request_timeout_seconds * 2, 120)) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise FileAnalysisError(f"Vision analysis request failed: {exc}") from exc

    text = _extract_chat_text(data)
    if not text:
        raise FileAnalysisError("Vision analysis returned empty response.")

    return _parse_analysis(text)


def _analyze_text(content_base64: str) -> FileAnalysisResult:
    try:
        text = base64.b64decode(content_base64).decode("utf-8", errors="replace")
    except Exception as exc:
        raise FileAnalysisError(f"Failed to decode text file: {exc}") from exc

    text = text.strip()
    if not text:
        raise FileAnalysisError("Text file is empty.")

    words = re.findall(r"[a-zA-Z]{3,}", text)
    zh_chars = re.findall(r"[一-鿿]{2,}", text)
    # Heuristic: first 200 chars as description
    description = text[:600].strip()
    if len(text) > 600:
        description += "…"

    keywords_en = sorted(set(words))[:15] if words else []
    keywords_zh = sorted(set(zh_chars))[:15] if zh_chars else []

    return FileAnalysisResult(
        description=description,
        keywords_zh=keywords_zh,
        keywords_en=keywords_en,
        source_text=text,
    )


def _analyze_pdf(content_base64: str, llm_config: LLMConfig) -> FileAnalysisResult:
    """Extract text from PDF using PyMuPDF (all pages), then analyze."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise FileAnalysisError(
            "Cannot process PDF: PyMuPDF (fitz) is not installed. "
            "Install it with: pip install PyMuPDF"
        )

    pdf_bytes = base64.b64decode(content_base64)
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            raise FileAnalysisError("PDF file has no pages.")

        all_text: list[str] = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            page_text = page.get_text().strip()
            if page_text:
                all_text.append(page_text)

        total_pages = doc.page_count
        doc.close()
    except Exception as exc:
        raise FileAnalysisError(f"Failed to read PDF: {exc}") from exc

    full_text = "\n".join(all_text).strip()

    # If PyMuPDF extracted meaningful text, use it directly
    # Threshold is low (20 chars) because PyMuPDF is a proper PDF parser —
    # any extracted text is legitimate content, unlike the old UTF-8 decode.
    if len(full_text) > 20:
        # LLM-based analysis produces richer understanding and more precise keywords
        if llm_config.api_key and llm_config.enabled:
            try:
                return _analyze_text_with_llm(full_text, llm_config, total_pages)
            except FileAnalysisError:
                pass  # fall through to regex

        description = full_text[:600].strip()
        if len(full_text) > 600:
            description += "…"
        words = re.findall(r"[a-zA-Z]{3,}", full_text)
        zh_chars = re.findall(r"[一-鿿]{2,}", full_text)
        return FileAnalysisResult(
            description=f"[{total_pages}页PDF] {description}",
            keywords_zh=sorted(set(zh_chars))[:15],
            keywords_en=sorted(set(words))[:15],
            source_text=full_text,
        )

    # PDF is image-based (scanned) — render pages to images for vision LLM
    if not (llm_config.api_key and llm_config.enabled):
        raise FileAnalysisError(
            "This PDF appears to be a scanned document (no extractable text). "
            "Enable LLM vision in Settings for AI-based analysis."
        )

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        # Render up to first 3 pages as a combined analysis
        import io

        pages_to_render = min(doc.page_count, 3)
        rendered_pages: list[str] = []
        for page_num in range(pages_to_render):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            rendered_pages.append(base64.b64encode(img_bytes).decode())
        doc.close()

        vision_desc_parts: list[str] = []
        vision_zh: set[str] = set()
        vision_en: set[str] = set()
        for i, img_b64 in enumerate(rendered_pages):
            try:
                result = _analyze_image(f"page_{i+1}.png", img_b64, "image/png", llm_config)
                if result.description:
                    vision_desc_parts.append(f"[第{i+1}页] {result.description}")
                vision_zh.update(result.keywords_zh)
                vision_en.update(result.keywords_en)
            except FileAnalysisError:
                vision_desc_parts.append(f"[第{i+1}页] 分析失败")

        combined_desc = " ".join(vision_desc_parts)
        return FileAnalysisResult(
            description=combined_desc[:1000] if len(combined_desc) > 1000 else combined_desc,
            keywords_zh=sorted(vision_zh)[:15],
            keywords_en=sorted(vision_en)[:15],
            source_text=combined_desc,
        )
    except Exception as exc:
        raise FileAnalysisError(f"Failed to analyze scanned PDF: {exc}") from exc


def _analyze_text_with_llm(
    text: str,
    llm_config: LLMConfig,
    total_pages: int = 0,
) -> FileAnalysisResult:
    """Send extracted text to LLM for deep research analysis.

    Produces a bilingual summary, precise search keywords, and research
    questions — far richer than regex-based extraction.
    """
    if not llm_config.api_key or not llm_config.enabled:
        raise FileAnalysisError(
            "LLM text analysis requires a configured LLM provider with API key."
        )

    max_chars = 8000
    truncated = text[:max_chars]
    if len(text) > max_chars:
        truncated += f"\n\n[Document truncated at {max_chars} characters; full text preserved in source_text for downstream planning.]"

    page_prefix = f"[{total_pages}页PDF] " if total_pages else ""

    payload = {
        "model": llm_config.model,
        "messages": [
            {"role": "system", "content": _text_analysis_prompt()},
            {"role": "user", "content": f"Research paper text:\n\n{truncated}"},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {llm_config.api_key}",
        "Content-Type": "application/json",
    }

    try:
        if llm_config.provider == "deepseek":
            endpoint = _chat_completions_endpoint(llm_config.endpoint)
        else:
            endpoint = llm_config.endpoint

        with httpx.Client(timeout=min(llm_config.request_timeout_seconds * 2, 120)) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise FileAnalysisError(f"Text analysis request failed: {exc}") from exc

    result_text = _extract_chat_text(data)
    if not result_text:
        raise FileAnalysisError("Text analysis returned empty response.")

    parsed = _parse_analysis(result_text)
    parsed.source_text = text  # keep the full original text
    parsed.description = page_prefix + parsed.description
    return parsed


def _text_analysis_prompt() -> str:
    return (
        "You are a research paper analyst. Deeply analyze the provided research paper text "
        "and extract actionable information for literature search.\n\n"
        "## Analysis Requirements\n"
        "Identify:\n"
        "- Research domain and sub-domain\n"
        "- Core problem the paper addresses\n"
        "- Methodology, models, and techniques used\n"
        "- Key findings and contributions\n"
        "- Application scenarios, datasets, and evaluation metrics\n\n"
        "## Output Format\n"
        "Return a JSON object with these fields:\n"
        '- "description": A bilingual summary (Chinese first, then English, 2-3 sentences each) '
        "covering the research problem, methodology, and key findings.\n"
        '- "keywords_zh": Array of 8-15 Chinese keywords optimized for CNKI/Google Scholar search. '
        "Include Chinese translations of key technical terms.\n"
        '- "keywords_en": Array of 8-15 English keywords optimized for OpenAlex/Crossref/Semantic Scholar. '
        "Use precise technical terms and canonical research phrases. "
        "Include specific model names (e.g., ResNet, BERT), dataset names, technique names.\n"
        '- "research_questions": Array of 2-4 research questions this paper addresses.\n'
        '- "search_dimensions": Array of 3-5 search dimensions, each with:\n'
        "  - name (Chinese dimension name, e.g. '技术方法', '应用场景', '评估指标')\n"
        "  - name_en (English dimension name, e.g. 'Technical Methods')\n"
        "  - zh_terms (4-8 Chinese search terms for this dimension)\n"
        "  - en_terms (4-8 English search terms for this dimension)\n"
        '- "suggested_queries": Dictionary with database-specific query strings for:\n'
        "  - openalex: natural language keyword combinations with AND/OR\n"
        "  - crossref: concise keyword query\n"
        "  - semantic_scholar: keyword query\n"
        "  - google_scholar: concise keyword phrase\n"
        "  - cnki: Chinese keyword combination\n\n"
        "## Keyword Quality Guidelines\n"
        "- Prefer multi-word phrases over single words for precision (e.g. 'transfer learning' not 'learning')\n"
        "- Include domain-specific terminology that would retrieve closely related papers\n"
        "- Exclude generic words: study, paper, research, method, approach, based, using, novel\n"
        "- Include variant phrasings that appear in the literature (e.g. 'multi-modal' and 'multimodal')\n\n"
        "## Search Dimension Guidelines\n"
        "- Dimensions must be meaningfully distinct from each other\n"
        "- Each dimension should capture a different facet: technology, application, population, evaluation, etc.\n"
        "- Terms within each dimension should be precise and domain-specific\n"
        "- These dimensions will be used to build database queries, so terms should be search-engine friendly\n\n"
        "Return ONLY valid JSON. No markdown fences, no additional text."
    )


def _vision_payload(model: str, data_uri: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a research assistant analyzing an image. "
                    "Extract the research topic, key concepts, and search terms. "
                    "Respond in JSON format with fields: "
                    "description (str), keywords_zh (list of str), keywords_en (list of str)."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image and extract the research topic. "
                            "If it contains text (e.g., a paper, screenshot, or notes), "
                            "extract the key research questions and concepts. "
                            "If it's a diagram or figure, describe what it suggests "
                            "as a research direction."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                ],
            },
        ],
        "temperature": 0.2,
        "max_tokens": 1500,
    }


def _extract_chat_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list):
        return ""
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text") or part.get("content") or ""
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return " ".join(parts)
    return ""


def _parse_analysis(text: str) -> FileAnalysisResult:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = _extract_json_block(stripped)
    else:
        payload = _extract_json_block(stripped)

    if isinstance(payload, dict):
        desc = str(payload.get("description") or payload.get("analysis") or payload.get("text") or text[:500])
        zh = _strings(payload.get("keywords_zh") or [])
        en = _strings(payload.get("keywords_en") or payload.get("keywords") or [])
        dimensions = _parse_search_dimensions(payload.get("search_dimensions"))
        queries = _parse_suggested_queries(payload.get("suggested_queries"))
        return FileAnalysisResult(
            description=desc,
            keywords_zh=zh,
            keywords_en=en,
            source_text=text,
            search_dimensions=dimensions,
            suggested_queries=queries,
        )

    return FileAnalysisResult(description=text[:500], keywords_zh=[], keywords_en=[], source_text=text)


def _extract_json_block(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if item and str(item).strip()]


def _parse_search_dimensions(value: Any) -> list[dict] | None:
    if not isinstance(value, list):
        return None
    dims: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if not name:
            continue
        dims.append({
            "name": name,
            "name_en": str(item.get("name_en") or ""),
            "zh_terms": _strings(item.get("zh_terms")),
            "en_terms": _strings(item.get("en_terms")),
        })
    return dims if dims else None


def _parse_suggested_queries(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    queries: dict[str, str] = {}
    for key in ("openalex", "crossref", "semantic_scholar", "google_scholar", "web_of_science", "cnki"):
        v = value.get(key)
        if isinstance(v, str) and v.strip():
            queries[key] = v.strip()
    return queries if queries else None


def _chat_completions_endpoint(endpoint: str) -> str:
    clean = endpoint.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    return f"{clean}/chat/completions"
