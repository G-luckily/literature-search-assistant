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
    "计算机视觉": "computer vision",
    "强化学习": "reinforcement learning",
    "迁移学习": "transfer learning",
    "联邦学习": "federated learning",
    "知识蒸馏": "knowledge distillation",
    "多模态": "multimodal",
    "图神经网络": "graph neural network",
    "生成对抗网络": "generative adversarial network",
    "注意力机制": "attention mechanism",
    "情感分析": "sentiment analysis",
    "文本挖掘": "text mining",
    "数据分析": "data analysis",
    "数据挖掘": "data mining",
    "信息检索": "information retrieval",
    "知识管理": "knowledge management",
    "科学计量学": "scientometrics",
    "文献计量学": "bibliometrics",
    "学术搜索": "academic search",
    "研究工作流": "research workflow",
    "数字图书馆": "digital library",
    "本体工程": "ontology engineering",
    "语义网": "semantic web",
    "链接数据": "linked data",
    "社交网络分析": "social network analysis",
    "内容分析": "content analysis",
    "扎根理论": "grounded theory",
    "问卷调查": "questionnaire survey",
    "混合方法": "mixed methods",
    "案例研究": "case study",
    "纵向研究": "longitudinal study",
    "横截面研究": "cross-sectional study",
    "实验研究": "experimental study",
    "准实验": "quasi-experiment",
    "用户研究": "user study",
    "可用性评估": "usability evaluation",
    "信息技术": "information technology",
    "人机交互": "human-computer interaction",
    "计算机辅助": "computer-assisted",
    "决策支持": "decision support",
    "专家系统": "expert system",
    "数字孪生": "digital twin",
    "边缘计算": "edge computing",
    "云计算": "cloud computing",
    "区块链": "blockchain",
    "物联网": "internet of things",
    "社会计算": "social computing",
    "群智感知": "crowdsensing",
    "协同过滤": "collaborative filtering",
    "个性化推荐": "personalized recommendation",
    "对话系统": "dialogue system",
    "机器翻译": "machine translation",
    "信息抽取": "information extraction",
    "文本分类": "text classification",
    "图像识别": "image recognition",
    "语音识别": "speech recognition",
    "异常检测": "anomaly detection",
    "预测模型": "prediction model",
    "优化算法": "optimization algorithm",
    "仿真模拟": "simulation",
    "信号处理": "signal processing",
    "生物信息学": "bioinformatics",
    "计算社会科学": "computational social science",
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
    # 泛词（不可作为检索关键词）
    "一个",
    "一些",
    "一切",
    "以及",
    "以后",
    "以来",
    "以上",
    "以前",
    "任何",
    "可以",
    "可能",
    "各个",
    "同时",
    "因此",
    "方面",
    "是否",
    "最近",
    "有关",
    "本身",
    "体现",
    "作用",
    "具体",
    "关于",
    "其他",
    "其实",
    "具有",
    "出现",
    "分析",
    "分别",
    "利用",
    "包括",
    "参与",
    "发现",
    "发生",
    "发展",
    "变化",
    "各种",
    "对应",
    "影响",
    "机制",
    "经验",
    "问题",
    "现状",
    "对策",
    "策略",
    "模式",
    "关系",
    "路径",
    "特点",
    "特征",
    "差异",
    "比较",
    "框架",
    # 口语/研究语气残留
    "我想",
    "我希望",
    "想要",
    "希望",
    "我们",
    "我的",
    "本次",
    "这个",
    "此项",
    "这个选题",
    "这个主题",
    "这个关键词",
    "这个问题",
    "这个研究",
    "该项目",
    "项目",
    "需要",
    "需求",
    "重点关注",
    "探索",
    "探讨",
    "构建",
    "建构",
    "梳理",
    "综述",
    "回顾",
    # 上下文泛化词
    "相关",
    "研究",
    "进行",
    "基于",
    "针对",
    "通过",
    "关于",
    "以来",
    "以后",
    "不同",
}

# 前缀语气剥离模式 —— 在关键词提取前剥离
FRAMING_PREFIXES = [
    r"^我想研究",
    r"^我想了解",
    r"^我想探讨",
    r"^我想分析",
    r"^我希望研究",
    r"^我希望了解",
    r"^研究",
    r"^探讨",
    r"^分析",
    r"^基于",
    r"^关于",
    r"^重点关注",
    r"^近年来",
]

# 通用弱词：仅在作为复合词/短语的一部分时才保留
GENERIC_WEAK_WORDS = {
    "资源",
    "影响",
    "机制",
    "经验",
    "问题",
    "现状",
    "对策",
    "策略",
    "模式",
    "路径",
    "数据",
    "信息",
    "分析",
    "研究",
    "方法",
    "实践",
    "应用",
    "工具",
    "系统",
    "技术",
    "发展",
    "建设",
    "管理",
    "服务",
    "支持",
    "评估",
}


def build_plan(
    need: str,
    zh_keywords: list[str] | None = None,
    en_keywords: list[str] | None = None,
) -> ResearchPlan:
    clean_need = _strip_framing(need)
    zh = _dedupe((zh_keywords or []) + _extract_zh_keywords(clean_need))
    en = _dedupe((en_keywords or []) + _extract_en_keywords(need) + _translate_zh(zh))

    structure = _extract_research_structure(need)
    research_questions = _build_research_questions(need, structure)
    core_concepts_list = _build_core_concepts(structure, zh, en)
    notes = _build_notes(structure, zh_keywords, en_keywords, need)

    queries = build_primary_queries(zh, en, need, structure)
    query_rounds = build_query_rounds(zh, en, queries, structure)

    # Strip sources without a Searcher implementation so the plan only lists runnable sources
    NOT_IMPLEMENTED = {"cnki"}
    queries = {k: v for k, v in queries.items() if k not in NOT_IMPLEMENTED}
    query_rounds = {k: v for k, v in query_rounds.items() if k not in NOT_IMPLEMENTED}

    # Build search_dimensions from structure for rule-based plans
    search_dimensions = _build_search_dimensions(structure, zh, en)

    return ResearchPlan(
        need=need,
        zh_keywords=zh[:20],
        en_keywords=en[:20],
        queries=queries,
        query_rounds=query_rounds,
        notes=notes,
        planner="rules",
        research_questions=research_questions,
        core_concepts=core_concepts_list,
        inclusion_criteria=_build_inclusion_criteria(structure),
        exclusion_criteria=_build_exclusion_criteria(),
        search_strategy=[
            "Use API-friendly sources first, then add focused expansion rounds to recover missed records.",
            "Keep the first round broad for recall, then review high-relevance records before importing to Zotero.",
        ],
        search_dimensions=search_dimensions,
    )


def build_primary_queries(
    zh_keywords: list[str],
    en_keywords: list[str],
    need: str,
    structure: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    struct = structure or {}
    tech_terms = struct.get("technology", [])
    pop_terms = struct.get("population", [])
    phen_terms = struct.get("phenomenon", [])

    # Build a precision query combining multiple research dimensions
    precision_parts = []
    if tech_terms:
        precision_parts.extend(tech_terms[:2])
    if pop_terms:
        precision_parts.extend(pop_terms[:2])
    if phen_terms:
        precision_parts.extend(phen_terms[:1])

    if precision_parts:
        # Also add English translations
        en_precision = [
            COMMON_TRANSLATIONS[t] for t in precision_parts if t in COMMON_TRANSLATIONS
        ]
        precision_parts.extend(en_precision)

    precision_query = " ".join(precision_parts[:8]) if precision_parts else ""
    broad_query = " ".join(en_keywords[:8] or zh_keywords[:8] or [need])

    # Use precision query when available, fall back to broad
    openalex_query = precision_query or broad_query
    crossref_query = precision_query or broad_query
    ss_query = precision_query or broad_query
    gs_query = precision_query or broad_query

    wos_terms = _dedupe(en_keywords[:8] + zh_keywords[:4])
    wos_query = "TS=(" + " OR ".join(f'"{term}"' for term in wos_terms[:10]) + ")"
    return {
        "openalex": openalex_query,
        "crossref": crossref_query,
        "semantic_scholar": ss_query,
        "zotero": precision_query or broad_query,
        "google_scholar": gs_query,
        "web_of_science": wos_query,
    }


def build_query_rounds(
    zh_keywords: list[str],
    en_keywords: list[str],
    primary_queries: dict[str, str],
    structure: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    struct = structure or {}
    tech_terms = struct.get("technology", [])
    pop_terms = struct.get("population", [])
    phen_terms = struct.get("phenomenon", [])
    method_terms = struct.get("method", [])

    # Translate structure terms to English for query use
    tech_en = [COMMON_TRANSLATIONS.get(t, t) for t in tech_terms[:3]]
    pop_en = [COMMON_TRANSLATIONS.get(t, t) for t in pop_terms[:3]]
    phen_en = [COMMON_TRANSLATIONS.get(t, t) for t in phen_terms[:3]]
    method_en = [COMMON_TRANSLATIONS.get(t, t) for t in method_terms[:2]]

    # Strategy buckets for more targeted queries
    buckets = []
    # Bucket 1: Tech + population core combination
    core = _dedupe(tech_en[:2] + pop_en[:2])
    if core:
        buckets.append(" ".join(core))
    # Bucket 2: Social/phenomenon + population
    social = _dedupe(pop_en[:2] + phen_en[:2])
    if social:
        buckets.append(" ".join(social))
    # Bucket 3: All three dimensions together
    all_dims = _dedupe(tech_en[:2] + pop_en[:2] + phen_en[:2])
    if all_dims:
        buckets.append(" ".join(all_dims[:8]))
    # Bucket 4: Method-specific
    if method_terms and method_en:
        buckets.append(" ".join(method_en + method_terms[:2]))

    # Diverse mid-range terms not in the primary top-6
    english_mid = en_keywords[4:10]
    en_alternates = [
        " ".join(en_keywords[i : i + 3])
        for i in range(0, min(len(en_keywords), 9), 3)
        if en_keywords[i : i + 3]
    ]
    zh_alternates = [
        " ".join(zh_keywords[i : i + 3])
        for i in range(0, min(len(zh_keywords), 9), 3)
        if zh_keywords[i : i + 3]
    ]

    rounds = {
        "openalex": _query_round_list(
            primary_queries.get("openalex", ""),
            [
                *buckets,
                *en_alternates,
                *zh_alternates,
            ],
        ),
        "crossref": _query_round_list(
            primary_queries.get("crossref", ""),
            [
                *buckets[:3],
                *en_alternates[:2],
            ],
        ),
        "semantic_scholar": _query_round_list(
            primary_queries.get("semantic_scholar", ""),
            [
                *buckets,
                " ".join(english_mid[:5]) if english_mid else "",
                *en_alternates[:2],
            ],
        ),
        "google_scholar": _query_round_list(
            primary_queries.get("google_scholar", ""),
            [
                " ".join(f'"{term}"' for term in (en_keywords[:3] or zh_keywords[:3])),
                *(buckets[1:3] if len(buckets) > 1 else []),
            ],
        ),
        "web_of_science": _query_round_list(
            primary_queries.get("web_of_science", ""),
            [
                _wos_and_query(
                    buckets[0].split() if buckets else en_keywords[:3], zh_keywords[:2]
                ),
                _wos_or_query(en_keywords[3:7], zh_keywords[2:5]),
            ],
        ),
        "zotero": _query_round_list(
            primary_queries.get("zotero", ""),
            [
                " ".join(zh_keywords[:6]),
                " ".join(en_keywords[:6]),
                " ".join(zh_keywords[:3] + en_keywords[:3]),
            ],
        ),
    }
    return {source: values for source, values in rounds.items() if values}


def _strip_framing(text: str) -> str:
    """Remove leading research framing phrases from the input text."""
    result = text.strip()
    for pattern in FRAMING_PREFIXES:
        result = re.sub(pattern, "", result).strip()
    return result


def _extract_research_structure(text: str) -> dict[str, list[str]]:
    """Parse a research need into structured fields: population, technology, phenomenon, etc."""
    structure: dict[str, list[str]] = {
        "population": [],
        "technology": [],
        "phenomenon": [],
        "concept": [],
        "method": [],
        "context": [],
    }
    lower = text.lower()

    # Population patterns
    pop_patterns = [
        (
            ["老年人", "老人", "独居老人", "老年群体", "老龄化"],
            ["老年人", "老年人", "独居老人", "老年群体", "老年人"],
        ),
        (
            ["青年", "青年群体", "大学生", "青少年"],
            ["青年", "青年", "大学生", "青少年"],
        ),
        (["儿童", "幼儿", "未成年人"], ["儿童", "幼儿", "未成年人"]),
        (["患者", "病人", "临床"], ["患者", "患者", "临床"]),
        (["教师", "学生", "学习者"], ["教师", "学生", "学习者"]),
    ]
    for keywords, labels in pop_patterns:
        for kw, label in zip(keywords, labels):
            if kw in text:
                if label not in structure["population"]:
                    structure["population"].append(label)

    # Technology patterns
    tech_patterns = [
        "人工智能",
        "AI",
        "智能",
        "聊天机器人",
        "大语言模型",
        "机器学习",
        "深度学习",
        "自然语言处理",
        "推荐系统",
        "知识图谱",
        "虚拟现实",
        "增强现实",
        "数字人",
        "虚拟伴侣",
    ]
    for tech in tech_patterns:
        if tech in text or tech in lower:
            if tech not in structure["technology"]:
                structure["technology"].append(tech)

    # Phenomenon patterns
    phen_patterns = [
        (
            ["情感陪伴", "陪伴", "情感支持", "社会支持"],
            ["情感陪伴", "陪伴", "情感支持", "社会支持"],
        ),
        (["孤独", "孤独感", "社会孤立"], ["孤独感", "孤独感", "社会孤立"]),
        (
            ["代际补偿", "代际关系", "代际", "家庭支持"],
            ["代际补偿", "代际关系", "代际", "家庭支持"],
        ),
        (
            ["数字陪伴", "数字亲密", "虚拟陪伴"],
            ["数字陪伴", "数字亲密关系", "虚拟陪伴"],
        ),
        (["情感资本", "情绪劳动", "情感劳动"], ["情感资本", "情绪劳动", "情感劳动"]),
    ]
    for keywords, labels in phen_patterns:
        for kw, label in zip(keywords, labels):
            if kw in text:
                if label not in structure["phenomenon"]:
                    structure["phenomenon"].append(label)

    # Method patterns
    method_patterns = [
        ("文本分析", "文本分析"),
        ("内容分析", "内容分析"),
        ("网络文本", "网络文本分析"),
        ("网络民族志", "网络民族志"),
        ("扎根理论", "扎根理论"),
        ("案例分析", "案例分析"),
        ("问卷调查", "问卷调查"),
        ("深度访谈", "深度访谈"),
    ]
    for kw, label in method_patterns:
        if kw in text:
            structure["method"].append(label)

    # Context patterns
    context_patterns = [
        ("养老", "养老"),
        ("老龄化", "老龄化"),
        ("教育", "教育"),
        ("就业", "就业"),
        ("医疗", "医疗"),
        ("社会参与", "社会参与"),
        ("社会政策", "社会政策"),
        ("公共服务", "公共服务"),
    ]
    for kw, label in context_patterns:
        if kw in text:
            structure["context"].append(label)

    # Deduplicate
    for key in structure:
        structure[key] = _dedupe(structure[key])
    return structure


def _build_research_questions(need: str, structure: dict[str, list[str]]) -> list[str]:
    """Generate structured research questions from the parsed structure."""
    questions = [need]
    parts = []
    if structure["technology"]:
        parts.append("以" + "、".join(structure["technology"][:3]) + "为技术对象")
    if structure["population"]:
        parts.append("以" + "、".join(structure["population"][:3]) + "为研究对象")
    if structure["phenomenon"]:
        parts.append("关注" + "、".join(structure["phenomenon"][:3]))
    if structure["method"]:
        parts.append("采用" + "、".join(structure["method"][:3]) + "等方法")
    if parts:
        questions.append("研究问题解析：" + "，".join(parts))
    if structure["concept"]:
        questions.append("理论视角：" + "、".join(structure["concept"][:3]))
    return questions


def _build_core_concepts(
    structure: dict[str, list[str]],
    zh_terms: list[str],
    en_terms: list[str],
) -> list[dict[str, str]]:
    """Build core_concepts list from structured fields and keyword lists."""
    concepts = []
    seen = set()

    for role, label in [
        ("technology", "核心技术"),
        ("population", "研究对象"),
        ("phenomenon", "核心现象"),
        ("concept", "理论概念"),
        ("method", "研究方法"),
        ("context", "研究场景"),
    ]:
        items = structure.get(role, [])
        for item in items[:3]:
            if item in seen:
                continue
            seen.add(item)
            en_term = COMMON_TRANSLATIONS.get(item, "")
            if not en_term and item in zh_terms:
                idx = zh_terms.index(item)
                if idx < len(en_terms):
                    en_term = en_terms[idx]
            concepts.append({"label_zh": item, "label_en": en_term or ""})

    # Fall back to old concept logic if structure was empty
    if not concepts:
        for index, zh_term in enumerate(zh_terms[:8]):
            if zh_term in seen:
                continue
            seen.add(zh_term)
            en_term = COMMON_TRANSLATIONS.get(zh_term)
            if not en_term and index < len(en_terms):
                en_term = en_terms[index]
            concepts.append({"label_zh": zh_term, "label_en": en_term or ""})

    return concepts


def _build_notes(
    structure: dict[str, list[str]],
    zh_keywords: list[str] | None,
    en_keywords: list[str] | None,
    need: str,
) -> list[str]:
    notes = []
    if not zh_keywords and not en_keywords:
        notes.append(
            "Current keyword extraction is deterministic. Add --zh-keyword or --en-keyword for precise control."
        )
    if structure["population"] and structure["technology"]:
        notes.append(
            f"Combined {structure['technology'][0]} AND {structure['population'][0]} for precision."
        )
    if "google scholar" in need.lower() or "谷歌学术" in need:
        notes.append(
            "Google Scholar is best handled as a low-frequency assisted source, not as a bulk automated API."
        )
    if "知网" in need or "cnki" in need.lower():
        notes.append(
            "CNKI integration should prefer citation export and Zotero translators over bulk full-text download."
        )
    return notes


def _build_inclusion_criteria(structure: dict[str, list[str]]) -> list[str]:
    criteria = []
    if structure["population"]:
        criteria.append(
            f"Population: must involve {' / '.join(structure['population'][:3])}"
        )
    if structure["technology"]:
        criteria.append(
            f"Technology: must involve {' / '.join(structure['technology'][:3])}"
        )
    if structure["method"]:
        criteria.append(f"Method: studies using {' / '.join(structure['method'][:3])}")
    return criteria


def _build_exclusion_criteria() -> list[str]:
    return [
        "Studies that mention AI only in passing without human/social focus",
        "Purely technical/algorithmic AI research without human subjects or social context",
        "Educational technology papers about smart campus/infrastructure without social science framing",
    ]


def _build_search_dimensions(
    structure: dict[str, list[str]],
    zh_terms: list[str],
    en_terms: list[str],
) -> list[dict[str, Any]]:
    """Build search_dimensions from the parsed research structure for rule-based plans."""
    dims: list[dict[str, Any]] = []
    seen_zh: set[str] = set()

    if structure.get("technology"):
        tech = structure["technology"][:5]
        tech_en = [COMMON_TRANSLATIONS.get(t, t) for t in tech]
        dims.append({
            "name": "技术/方法",
            "name_en": "Technology/Method",
            "zh_terms": tech,
            "en_terms": tech_en,
        })
        seen_zh.update(tech)

    if structure.get("population"):
        pop = structure["population"][:5]
        pop_en = [COMMON_TRANSLATIONS.get(p, p) for p in pop]
        dims.append({
            "name": "研究对象",
            "name_en": "Population",
            "zh_terms": pop,
            "en_terms": pop_en,
        })
        seen_zh.update(pop)

    if structure.get("phenomenon"):
        phen = structure["phenomenon"][:5]
        phen_en = [COMMON_TRANSLATIONS.get(p, p) for p in phen]
        dims.append({
            "name": "核心现象",
            "name_en": "Phenomenon",
            "zh_terms": phen,
            "en_terms": phen_en,
        })
        seen_zh.update(phen)

    if structure.get("method"):
        method = structure["method"][:5]
        method_en = [COMMON_TRANSLATIONS.get(m, m) for m in method]
        dims.append({
            "name": "研究方法",
            "name_en": "Research Method",
            "zh_terms": method,
            "en_terms": method_en,
        })
        seen_zh.update(method)

    if structure.get("context"):
        ctx = structure["context"][:5]
        ctx_en = [COMMON_TRANSLATIONS.get(c, c) for c in ctx]
        dims.append({
            "name": "研究场景",
            "name_en": "Context",
            "zh_terms": ctx,
            "en_terms": ctx_en,
        })
        seen_zh.update(ctx)

    # Add remaining keywords as a general dimension if they exist
    remaining = [z for z in zh_terms[:8] if z not in seen_zh]
    if remaining:
        rem_en = [COMMON_TRANSLATIONS.get(r, r) for r in remaining]
        dims.append({
            "name": "综合关键词",
            "name_en": "General Keywords",
            "zh_terms": remaining,
            "en_terms": rem_en,
        })

    return dims


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
        chunk = re.sub(
            r"^(我想研究|我想了解|我想探讨|我希望研究|研究|探索|分析)", "", chunk
        )
        for piece in re.split(r"[的和与及或在对将能可后前中]", chunk):
            piece = piece.strip()
            piece = re.sub(
                r"^(我想研究|我想了解|我想探讨|我希望研究|研究|探索|分析)", "", piece
            )
            piece = re.sub(
                r"(相关|方面|领域|项目|这个选题|这个主题|这个关键词)$", "", piece
            )
            if any(
                stop in piece
                for stop in ("我想", "我希望", "想要", "这个选题", "这个主题")
            ):
                continue
            if piece in GENERIC_WEAK_WORDS:
                continue
            if any(
                piece != candidate and piece in candidate for candidate in candidates
            ):
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


def _query_round_list(primary: str, candidates: list[str]) -> list[str]:
    rounds = []
    for query in [primary, *candidates]:
        normalized = " ".join(query.split())
        if not normalized or normalized in rounds:
            continue
        rounds.append(normalized)
    return rounds


def _wos_or_query(en_terms: list[str], zh_terms: list[str]) -> str:
    terms = _dedupe(en_terms + zh_terms)
    if not terms:
        return ""
    return "TS=(" + " OR ".join(f'"{term}"' for term in terms[:8]) + ")"


def _wos_and_query(en_terms: list[str], zh_terms: list[str]) -> str:
    terms = _dedupe(en_terms + zh_terms)
    if not terms:
        return ""
    return "TS=(" + " AND ".join(f'"{term}"' for term in terms[:5]) + ")"


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
