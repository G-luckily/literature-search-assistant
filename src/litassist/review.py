from __future__ import annotations

import json
from typing import Any

import httpx

from .config import LLMConfig


class ReviewGenerationError(RuntimeError):
    pass


def generate_review(
    need: str,
    papers: list[dict[str, Any]],
    config: LLMConfig,
) -> str:
    if not config.enabled or not config.api_key:
        raise ReviewGenerationError(
            "LLM is not configured. Please set up a provider and API key in Settings."
        )

    papers_text = _format_papers(papers)
    provider = config.provider.strip().lower()

    if provider == "openai":
        return _openai_review(need, papers_text, config)
    if provider == "deepseek":
        return _deepseek_review(need, papers_text, config)
    raise ReviewGenerationError(f"Unsupported LLM provider: {config.provider}")


def _format_papers(papers: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, p in enumerate(papers, start=1):
        authors = "; ".join(p.get("authors", []) or [])
        title = p.get("title") or "Untitled"
        year = p.get("year") or "unknown"
        venue = p.get("venue") or ""
        abstract = (p.get("abstract") or "")[:800]
        lines.append(
            f"### Paper {i}\n"
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Year: {year}\n"
            f"Venue: {venue}\n"
            f"Abstract: {abstract}\n"
        )
    return "\n".join(lines)


def _call_llm(
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ReviewGenerationError(f"LLM request failed: {exc}") from exc


def _openai_review(
    need: str, papers_text: str, config: LLMConfig
) -> str:
    system_prompt = (
        "You are an expert academic research analyst. Your task is to synthesize "
        "a collection of academic papers into a structured literature review.\n\n"
        "Analyze the papers and produce a review with these sections:\n"
        "1. **Research Themes**: Identify 2-4 major thematic clusters. For each, "
        "list which papers belong and summarize their collective findings.\n"
        "2. **Key Findings**: Cross-cutting findings that emerge across multiple papers.\n"
        "3. **Methodological Approaches**: Common methodologies and notable innovations.\n"
        "4. **Research Gaps**: What is not addressed or remains unresolved.\n"
        "5. **Future Directions**: Suggested next steps based on the gap analysis.\n\n"
        "Use markdown headings. Reference papers by their number (e.g., Paper 1, Paper 2).\n"
        "Be specific and cite evidence from the abstracts. If the paper set is small "
        "or diverse, acknowledge limitations in generalizability."
    )
    user_prompt = f"## Research Need\n{need}\n\n## Papers\n{papers_text}"

    payload = {
        "model": config.model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": 3000,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    data = _call_llm(config.endpoint, headers, payload, config.request_timeout_seconds)

    try:
        return data["output"][0]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise ReviewGenerationError("Failed to parse LLM response.")


def _deepseek_review(
    need: str, papers_text: str, config: LLMConfig
) -> str:
    system_prompt = (
        "You are an expert academic research analyst. Synthesize the following "
        "papers into a structured literature review covering:\n"
        "1. Research Themes\n2. Key Findings\n3. Methodological Approaches\n"
        "4. Research Gaps\n5. Future Directions\n\n"
        "Use markdown headings. Reference papers by number. Be specific."
    )
    user_prompt = f"## Research Need\n{need}\n\n## Papers\n{papers_text}"

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 3000,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    endpoint = _chat_completions_endpoint(config.endpoint)
    data = _call_llm(endpoint, headers, payload, config.request_timeout_seconds)

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ReviewGenerationError("Failed to parse LLM response.")


def _chat_completions_endpoint(base: str) -> str:
    if base.rstrip("/").endswith("/chat/completions"):
        return base
    return base.rstrip("/") + "/chat/completions"
