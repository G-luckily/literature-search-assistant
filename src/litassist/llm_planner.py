from __future__ import annotations

import json
from typing import Any

import httpx

from .config import LLMConfig
from .models import ResearchPlan
from .planner import build_plan, build_query_rounds


class LLMPlannerError(RuntimeError):
    pass


def build_llm_plan(
    need: str,
    config: LLMConfig,
    zh_keywords: list[str] | None = None,
    en_keywords: list[str] | None = None,
) -> ResearchPlan:
    provider = config.provider.strip().lower()
    seed = build_plan(need, zh_keywords=zh_keywords, en_keywords=en_keywords)
    if provider == "openai":
        return _build_openai_plan(need, config, seed)
    if provider == "deepseek":
        return _build_deepseek_plan(need, config, seed)
    raise LLMPlannerError(f"Unsupported LLM provider: {config.provider}")


def _build_openai_plan(
    need: str,
    config: LLMConfig,
    seed: ResearchPlan,
) -> ResearchPlan:
    if not config.api_key:
        raise LLMPlannerError("OPENAI_API_KEY is required for LLM planning.")

    payload = {
        "model": config.model,
        "input": [
            {
                "role": "system",
                "content": _system_prompt(),
            },
            {
                "role": "user",
                "content": json.dumps(_seed_payload(need, seed), ensure_ascii=False),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "literature_search_plan",
                "strict": True,
                "schema": _schema(),
            }
        },
        "max_output_tokens": 2500,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=config.request_timeout_seconds) as client:
            response = client.post(config.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise LLMPlannerError(f"OpenAI planning request failed: {exc}") from exc

    parsed = _extract_json(data)
    return _plan_from_payload(need, parsed, seed)


def _build_deepseek_plan(
    need: str,
    config: LLMConfig,
    seed: ResearchPlan,
) -> ResearchPlan:
    if not config.api_key:
        raise LLMPlannerError("DEEPSEEK_API_KEY is required for LLM planning.")

    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": _deepseek_system_prompt(),
            },
            {
                "role": "user",
                "content": json.dumps(_seed_payload(need, seed), ensure_ascii=False),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 2500,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=config.request_timeout_seconds) as client:
            response = client.post(
                _chat_completions_endpoint(config.endpoint),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise LLMPlannerError(f"DeepSeek planning request failed: {exc}") from exc

    parsed = _extract_chat_json(data)
    return _plan_from_payload(need, parsed, seed)


def _seed_payload(need: str, seed: ResearchPlan) -> dict[str, Any]:
    return {
        "need": need,
        "seed_zh_keywords": seed.zh_keywords,
        "seed_en_keywords": seed.en_keywords,
        "seed_queries": seed.queries,
    }


def _system_prompt() -> str:
    return (
        "You are an expert research librarian and literature search strategist. "
        "Your task is to deeply decompose the user's research need into multiple "
        "search dimensions, and produce a rigorous bilingual literature search plan.\n\n"
        "## Core Process\n"
        "1. Analyze the research need and identify 3-5 core search dimensions "
        "(e.g., technology/method, application scenario, population, evaluation, "
        "theoretical framework, context/domain).\n"
        "2. For each dimension, generate precise Chinese and English search terms "
        "including core terms, synonyms, broader/narrower terms.\n"
        "3. Combine terms across dimensions to build effective per-database queries.\n\n"
        "## Search Dimension Requirements\n"
        "- Dimensions must have meaningful distinction from each other (minimal overlap)\n"
        "- Each dimension must have at least 3 terms in both languages\n"
        "- Terms should include: core concepts, synonyms, broader/narrower terms\n\n"
        "## Database Query Requirements\n"
        "- OpenAlex / Crossref / Semantic Scholar: natural language keyword combinations, "
        "use AND/OR operators and quoted phrases for precision\n"
        "- Web of Science: use TS=() Boolean syntax\n"
        "- CNKI: use Chinese subject heading combinations\n"
        "- Google Scholar: concise keyword phrases that work well for broad recall\n"
        "- Each database query should combine terms from MULTIPLE dimensions "
        "to maximize precision\n\n"
        "## Output Rules\n"
        "- Return only structured JSON matching the provided schema\n"
        "- Keep term lists comprehensive yet distinct (max 25 per language)\n"
        "- Do not invent unavailable databases or fake citations\n"
        "- zh_keywords and en_keywords should be the union of all dimension terms"
    )


def _deepseek_system_prompt() -> str:
    return (
        f"{_system_prompt()}\n"
        "Return a single valid JSON object only, with no Markdown fences or prose. "
        "The JSON object must follow this contract: "
        f"{json.dumps(_schema(), ensure_ascii=False)}"
    )


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "research_questions",
            "core_concepts",
            "search_dimensions",
            "zh_keywords",
            "en_keywords",
            "inclusion_criteria",
            "exclusion_criteria",
            "search_strategy",
            "queries",
            "notes",
        ],
        "properties": {
            "research_questions": {"type": "array", "items": {"type": "string"}},
            "core_concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "label_zh",
                        "label_en",
                        "synonyms_zh",
                        "synonyms_en",
                    ],
                    "properties": {
                        "label_zh": {"type": "string"},
                        "label_en": {"type": "string"},
                        "synonyms_zh": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "synonyms_en": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "search_dimensions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "zh_terms", "en_terms"],
                    "properties": {
                        "name": {"type": "string"},
                        "name_en": {"type": "string"},
                        "zh_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "en_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "zh_keywords": {"type": "array", "items": {"type": "string"}},
            "en_keywords": {"type": "array", "items": {"type": "string"}},
            "inclusion_criteria": {"type": "array", "items": {"type": "string"}},
            "exclusion_criteria": {"type": "array", "items": {"type": "string"}},
            "search_strategy": {"type": "array", "items": {"type": "string"}},
            "queries": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "openalex",
                    "crossref",
                    "semantic_scholar",
                    "google_scholar",
                    "web_of_science",
                    "cnki",
                ],
                "properties": {
                    "openalex": {"type": "string"},
                    "crossref": {"type": "string"},
                    "semantic_scholar": {"type": "string"},
                    "google_scholar": {"type": "string"},
                    "web_of_science": {"type": "string"},
                    "cnki": {"type": "string"},
                },
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
    }


def _extract_json(response: dict[str, Any]) -> dict[str, Any]:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return _loads_json_object(output_text)

    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return _loads_json_object(text)

    raise LLMPlannerError("OpenAI response did not include JSON output text.")


def _extract_chat_json(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list):
        raise LLMPlannerError("DeepSeek response did not include choices.")

    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return _loads_json_object(content)
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text") or part.get("content")
                if isinstance(text, str) and text.strip():
                    return _loads_json_object(text)

    raise LLMPlannerError("DeepSeek response did not include JSON content.")


def _loads_json_object(text: str) -> dict[str, Any]:
    stripped = _strip_json_fence(text.strip())
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(stripped[start : end + 1])
            except json.JSONDecodeError as nested_exc:
                raise LLMPlannerError(
                    "LLM response was not valid JSON."
                ) from nested_exc
        else:
            raise LLMPlannerError("LLM response was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise LLMPlannerError("LLM response JSON was not an object.")
    return payload


def _strip_json_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _chat_completions_endpoint(endpoint: str) -> str:
    clean = endpoint.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    return f"{clean}/chat/completions"


def _plan_from_payload(
    need: str,
    payload: dict[str, Any],
    seed: ResearchPlan,
) -> ResearchPlan:
    zh_keywords = _strings(payload.get("zh_keywords")) or seed.zh_keywords
    en_keywords = _strings(payload.get("en_keywords")) or seed.en_keywords
    queries_payload = (
        payload.get("queries") if isinstance(payload.get("queries"), dict) else {}
    )
    queries = {
        key: str(queries_payload.get(key) or seed.queries[key]) for key in seed.queries
    }
    notes = _strings(payload.get("notes"))
    notes.append(
        "Plan generated with LLM structured output and rule-based fallback fields."
    )

    # Parse search dimensions
    dimensions = _dimensions(payload.get("search_dimensions"))

    # Build richer query_rounds from dimensions if available
    if dimensions:
        query_rounds = _build_dimension_query_rounds(dimensions, queries, en_keywords, zh_keywords)
    else:
        query_rounds = build_query_rounds(zh_keywords[:30], en_keywords[:30], queries)

    return ResearchPlan(
        need=need,
        zh_keywords=zh_keywords[:30],
        en_keywords=en_keywords[:30],
        queries=queries,
        query_rounds=query_rounds,
        notes=notes,
        planner="llm",
        research_questions=_strings(payload.get("research_questions")) or [need],
        core_concepts=_concepts(payload.get("core_concepts")),
        inclusion_criteria=_strings(payload.get("inclusion_criteria")),
        exclusion_criteria=_strings(payload.get("exclusion_criteria")),
        search_strategy=_strings(payload.get("search_strategy")),
        search_dimensions=dimensions,
    )


def _build_dimension_query_rounds(
    dimensions: list[dict[str, Any]],
    base_queries: dict[str, str],
    en_keywords: list[str],
    zh_keywords: list[str],
) -> dict[str, list[str]]:
    """Build per-source query rounds from search dimensions.

    Each dimension contributes its terms as an expansion round.
    Additionally, pairwise combinations of dimensions are created for precision.
    """
    rounds: dict[str, list[str]] = {}

    # Collect all dimension term sets
    en_sets: list[list[str]] = []
    zh_sets: list[list[str]] = []
    for dim in dimensions:
        en_terms = _strings(dim.get("en_terms"))
        zh_terms = _strings(dim.get("zh_terms"))
        if en_terms:
            en_sets.append(en_terms)
        if zh_terms:
            zh_sets.append(zh_terms)

    for source in base_queries:
        source_rounds: list[str] = []

        # Round 1: the LLM-generated primary query
        if base_queries[source]:
            source_rounds.append(base_queries[source])

        # Rounds 2+: dimension-specific queries
        # Each dimension's top terms as a standalone query
        for terms in en_sets:
            query = " AND ".join(terms[:3])
            if query and query not in source_rounds:
                source_rounds.append(query)

        # Pairwise dimension combinations for precision
        for i in range(len(en_sets)):
            for j in range(i + 1, len(en_sets)):
                combo = " AND ".join(en_sets[i][:2] + en_sets[j][:2])
                if combo and combo not in source_rounds:
                    source_rounds.append(combo)

        # Chinese term queries for sources that benefit from them
        if zh_sets and source in ("cnki", "google_scholar"):
            for terms in zh_sets:
                query = " ".join(terms[:4])
                if query and query not in source_rounds:
                    source_rounds.append(query)

        # Keyword-based fallback rounds (use remaining keywords not in dimensions)
        used_en = {t for s in en_sets for t in s}
        remaining_en = [k for k in en_keywords if k not in used_en]
        for i in range(0, len(remaining_en), 3):
            chunk = remaining_en[i : i + 3]
            if chunk:
                q = " ".join(chunk)
                if q and q not in source_rounds:
                    source_rounds.append(q)

        rounds[source] = source_rounds[:8]  # max 8 rounds per source

    return rounds


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _dimensions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    dims = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if not name:
            continue
        dims.append(
            {
                "name": name,
                "name_en": str(item.get("name_en") or ""),
                "zh_terms": _strings(item.get("zh_terms")),
                "en_terms": _strings(item.get("en_terms")),
            }
        )
    return dims


def _concepts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    concepts = []
    for item in value:
        if not isinstance(item, dict):
            continue
        concepts.append(
            {
                "label_zh": str(item.get("label_zh") or ""),
                "label_en": str(item.get("label_en") or ""),
                "synonyms_zh": _strings(item.get("synonyms_zh")),
                "synonyms_en": _strings(item.get("synonyms_en")),
            }
        )
    return concepts
