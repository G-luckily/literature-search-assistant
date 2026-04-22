from __future__ import annotations

import re
from collections import Counter

from .models import ResearchPlan


COMMON_TRANSLATIONS = {
    "人工智能": "artificial intelligence",
    "机器学习": "machine learning",
    "深度学习": "deep learning",
    "自然语言处理": "natural language processing",
    "大语言模型": "large language model",
    "生成式人工智能": "generative AI",
    "文献检索": "literature retrieval",
    "文献管理": "reference management",
    "知识图谱": "knowledge graph",
    "推荐系统": "recommender system",
    "系统综述": "systematic review",
    "元分析": "meta-analysis",
    "教育": "education",
    "医学": "medicine",
    "公共卫生": "public health",
    "心理健康": "mental health",
    "数字人文": "digital humanities",
    "可视化": "visualization",
    "科研工作流": "research workflow",
    "开放获取": "open access",
    "引用分析": "citation analysis",
    "自动化": "automation",
    "协同管理": "collaborative management",
}

EN_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "based",
    "for",
    "from",
    "how",
    "into",
    "literature",
    "need",
    "needs",
    "of",
    "on",
    "or",
    "research",
    "study",
    "that",
    "the",
    "this",
    "to",
    "use",
    "using",
    "with",
}

ZH_STOPWORDS = {
    "一个",
    "一些",
    "以及",
    "以后",
    "可以",
    "对应",
    "希望",
    "我们",
    "我的",
    "本次",
    "相关",
    "研究",
    "进行",
    "这个",
    "项目",
    "需要",
    "需求",
}


def build_plan(
    need: str,
    zh_keywords: list[str] | None = None,
    en_keywords: list[str] | None = None,
) -> ResearchPlan:
    zh = _dedupe((zh_keywords or []) + _extract_zh_keywords(need))
    en = _dedupe((en_keywords or []) + _extract_en_keywords(need) + _translate_zh(zh))

    main_terms = en[:6] or zh[:6] or [need]
    crossref_query = " ".join(main_terms[:8])
    openalex_query = " ".join(main_terms[:8])
    semantic_query = " ".join(main_terms[:8])
    google_scholar_query = " ".join(main_terms[:8])

    wos_terms = en[:8] + zh[:4]
    wos_query = "TS=(" + " OR ".join(f'"{term}"' for term in wos_terms[:10]) + ")"
    cnki_query = " OR ".join(zh[:10] + en[:5])

    notes = []
    if not zh_keywords and not en_keywords:
        notes.append(
            "Current keyword extraction is deterministic. Add --zh-keyword or --en-keyword for precise control."
        )
    if "google scholar" in need.lower() or "谷歌学术" in need:
        notes.append(
            "Google Scholar is best handled as a low-frequency assisted source, not as a bulk automated API."
        )
    if "知网" in need or "cnki" in need.lower():
        notes.append(
            "CNKI integration should prefer citation export and Zotero translators over bulk full-text download."
        )

    return ResearchPlan(
        need=need,
        zh_keywords=zh[:20],
        en_keywords=en[:20],
        queries={
            "openalex": openalex_query,
            "crossref": crossref_query,
            "semantic_scholar": semantic_query,
            "google_scholar": google_scholar_query,
            "web_of_science": wos_query,
            "cnki": cnki_query,
        },
        notes=notes,
        planner="rules",
        research_questions=[need],
        core_concepts=_concepts(zh, en),
        inclusion_criteria=[],
        exclusion_criteria=[],
        search_strategy=[
            "Use API-friendly sources first, then confirm platform-specific searches manually.",
            "Review high-relevance records before importing to Zotero.",
        ],
    )


def _extract_en_keywords(text: str) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text)
        if word.lower() not in EN_STOPWORDS
    ]
    phrases = re.findall(r'"([^"]{3,80})"', text)
    candidates = phrases + words
    counts = Counter(candidates)
    return [term for term, _ in counts.most_common(20)]


def _extract_zh_keywords(text: str) -> list[str]:
    candidates: list[str] = []
    for known in COMMON_TRANSLATIONS:
        if known in text:
            candidates.append(known)

    chunks = re.findall(r"[\u4e00-\u9fff]{2,16}", text)
    for chunk in chunks:
        chunk = re.sub(r"^(我想|我希望|希望|请|需要|想要|研究|探索|分析)", "", chunk)
        for piece in re.split(r"[的和与及或在对将能可后前中]", chunk):
            piece = piece.strip()
            piece = re.sub(r"^(我想|我希望|希望|请|需要|想要|研究|探索|分析)", "", piece)
            piece = re.sub(r"(相关|方面|领域|项目)$", "", piece)
            if any(stop in piece for stop in ("我想", "我希望", "想要")):
                continue
            if any(piece != candidate and piece in candidate for candidate in candidates):
                continue
            if 2 <= len(piece) <= 8 and piece not in ZH_STOPWORDS:
                candidates.append(piece)

    counts = Counter(candidates)
    return [term for term, _ in counts.most_common(20)]


def _translate_zh(terms: list[str]) -> list[str]:
    translated = []
    for term in terms:
        if term in COMMON_TRANSLATIONS:
            translated.append(COMMON_TRANSLATIONS[term])
    return translated


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _concepts(zh_terms: list[str], en_terms: list[str]) -> list[dict[str, str]]:
    concepts = []
    for index, zh_term in enumerate(zh_terms[:8]):
        en_term = COMMON_TRANSLATIONS.get(zh_term)
        if not en_term and index < len(en_terms):
            en_term = en_terms[index]
        concepts.append({"label_zh": zh_term, "label_en": en_term or ""})
    return concepts
