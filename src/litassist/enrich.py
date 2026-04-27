from __future__ import annotations

from typing import Any

import httpx

from .config import GeneralConfig
from .models import Paper, ResearchPlan

PDF_HINTS = (".pdf", "/pdf", "type=printable", "format=pdf")
BAD_PDF_HINTS = (".jpg", ".jpeg", ".png", ".gif", ".svg", "image/")

# === 相关性评分术语分类 ===

# 核心技术/AI 相关词
CORE_TECH_TERMS = [
    "artificial intelligence",
    "ai",
    "machine learning",
    "deep learning",
    "natural language processing",
    "large language model",
    "llm",
    "chatbot",
    "chatgpt",
    "conversational ai",
    "intelligent agent",
    "social robot",
    "companion robot",
    "virtual assistant",
    "recommender system",
    "knowledge graph",
    "generative ai",
    "virtual companion",
    "digital companion",
    "embodied agent",
    "人工智能",
    "ai",
    "智能",
    "聊天机器人",
    "大语言模型",
    "机器学习",
    "深度学习",
    "自然语言处理",
    "推荐系统",
    "虚拟助手",
    "虚拟伴侣",
    "陪伴机器人",
    "社交机器人",
    "数字人",
    "智能体",
    "ai陪伴",
    "智能陪伴",
]

# 研究对象 / Population 相关词
POPULATION_TERMS = [
    "older adult",
    "elderly",
    "aging",
    "aged",
    "old age",
    "senior citizen",
    "nursing home",
    "老年",
    "老人",
    "老年人",
    "独居老人",
    "高龄",
    "老龄化",
    "长者",
    "young adult",
    "youth",
    "adolescent",
    "teenager",
    "student",
    "青年",
    "青少年",
    "大学生",
    "年轻人",
    "child",
    "children",
    "patient",
    "worker",
    "teacher",
    "儿童",
    "患者",
    "工人",
    "教师",
    "中年人",
    "中老年",
]

# 情感/社会支持相关词
PHENOMENON_TERMS = [
    "companionship",
    "emotional support",
    "social support",
    "loneliness",
    "social isolation",
    "emotional well-being",
    "mental health",
    "social connectedness",
    "social interaction",
    "intergenerational",
    "digital companionship",
    "emotional bond",
    "attachment",
    "solitude",
    "social robot acceptance",
    "caregiving",
    "情感陪伴",
    "情感支持",
    "社会支持",
    "孤独感",
    "孤独",
    "心理健康",
    "情感",
    "陪伴",
    "代际",
    "代际补偿",
    "社会交往",
    "社交互动",
    "数字陪伴",
    "虚拟陪伴",
    "情感资本",
    "情感劳动",
    "情绪劳动",
    "社会参与",
    "养老",
    "居家养老",
    "智慧养老",
]

# 明确无关领域 —— 命中即重罚
IRRELEVANT_DOMAIN_MARKERS = [
    "智慧校园",
    "智慧课堂",
    "智慧教育",
    "智能教育",
    "教育信息化",
    "中小学",
    "k-12",
    "k12",
    "基础教育",
    "语文教学",
    "英语教学",
    "学科教学",
    "课程设计",
    "教学设计",
    "教学模式",
    "自动驾驶",
    "目标检测",
    "图像识别",
    "目标追踪",
    "语义分割",
    "推荐算法",
    "协同过滤",
    "异常检测",
    "入侵检测",
    "智能制造",
    "工业",
    "农业",
    "作物",
    "遥感",
    "气象",
    "医学影像",
    "医疗影像",
    "病理",
    "药物发现",
    "分子",
    "智能电网",
    "电力",
    "能源",
    "交通流",
    "solar cell",
    "battery",
    "material",
    "catalyst",
    "smart campus",
    "smart classroom",
    "education technology",
    "object detection",
    "image segmentation",
    "autonomous driving",
]

IRRELEVANT_DOMAIN_THRESHOLD = (
    5  # 如果标题/摘要命中 IRRELEVANT_DOMAIN_MARKERS 超过此阈值，强力降权
)


def enrich_papers(
    papers: list[Paper],
    plan: ResearchPlan,
    config: GeneralConfig,
    use_unpaywall: bool = True,
) -> list[Paper]:
    score_relevance(papers, plan, config)
    clean_pdf_links(papers)
    if use_unpaywall:
        enrich_open_access_links(papers, config)
    return papers


def score_relevance(
    papers: list[Paper],
    plan: ResearchPlan,
    config: GeneralConfig | None = None,
) -> None:
    for paper in papers:
        title = (paper.title or "").lower()
        abstract = (paper.abstract or "").lower()

        score = 0.0
        matched_reasons: list[str] = []

        # --- 核心技术匹配 ---
        tech_title_hits = _count_term_hits(title, CORE_TECH_TERMS)
        tech_abstract_hits = _count_term_hits(abstract, CORE_TECH_TERMS)
        if tech_title_hits > 0:
            score += tech_title_hits * 3.0
            matched_reasons.append(f"核心技术(标题):{tech_title_hits}")
        if tech_abstract_hits > 0:
            score += tech_abstract_hits * 1.5
            matched_reasons.append(f"核心技术(摘要):{tech_abstract_hits}")

        has_tech_match = tech_title_hits > 0 or tech_abstract_hits > 0

        # --- 研究对象匹配 ---
        pop_title_hits = _count_term_hits(title, POPULATION_TERMS)
        pop_abstract_hits = _count_term_hits(abstract, POPULATION_TERMS)
        if pop_title_hits > 0:
            score += pop_title_hits * 3.0
            matched_reasons.append(f"研究对象(标题):{pop_title_hits}")
        if pop_abstract_hits > 0:
            score += pop_abstract_hits * 1.5
            matched_reasons.append(f"研究对象(摘要):{pop_abstract_hits}")

        has_pop_match = pop_title_hits > 0 or pop_abstract_hits > 0

        # --- 核心现象/情感支持匹配 ---
        phen_title_hits = _count_term_hits(title, PHENOMENON_TERMS)
        phen_abstract_hits = _count_term_hits(abstract, PHENOMENON_TERMS)
        if phen_title_hits > 0:
            score += phen_title_hits * 3.0
            matched_reasons.append(f"核心现象(标题):{phen_title_hits}")
        if phen_abstract_hits > 0:
            score += phen_abstract_hits * 1.5
            matched_reasons.append(f"核心现象(摘要):{phen_abstract_hits}")

        has_phen_match = phen_title_hits > 0 or phen_abstract_hits > 0

        # --- 无关领域惩罚 ---
        irrelevant_title_hits = _count_term_hits(title, IRRELEVANT_DOMAIN_MARKERS)
        if irrelevant_title_hits >= IRRELEVANT_DOMAIN_THRESHOLD:
            score -= 10.0
            matched_reasons.append(f"无关领域惩罚:{irrelevant_title_hits}")
        elif irrelevant_title_hits > 0:
            score -= irrelevant_title_hits * 2.0
            matched_reasons.append(f"无关领域降权:{irrelevant_title_hits}")

        # --- 综合过滤规则 ---
        # 如果同时匹配了技术 + 研究对象，加权
        if has_tech_match and has_pop_match:
            score += 1.5
            matched_reasons.append("交叉匹配:技术+对象")
        # 如果同时匹配了技术 + 研究对象 + 现象，高分
        if has_tech_match and has_pop_match and has_phen_match:
            score += 2.0
            matched_reasons.append("综合匹配:技术+对象+现象")

        # --- 元数据加分 ---
        if paper.doi:
            score += 0.25
        if paper.pdf_url:
            score += 0.25
        if paper.cited_by_count:
            score += min(paper.cited_by_count / 500, 1.5)
        if (
            paper.year
            and config
            and config.from_year
            and paper.year >= config.from_year
        ):
            score += min((paper.year - config.from_year + 1) / 10, 0.75)
        if has_tech_match and has_pop_match and paper.year and paper.year >= 2020:
            score += 0.5  # 近年且交叉匹配

        # --- 严重不相关惩罚 ---
        if not has_tech_match and not has_pop_match:
            score -= 5.0
            matched_reasons.append("无技术/对象匹配:强降权")

        paper.relevance_score = round(max(score, 0), 3)
        paper.relevance_reasons = matched_reasons[:12]


def clean_pdf_links(papers: list[Paper]) -> None:
    for paper in papers:
        if paper.pdf_url and not looks_like_pdf_url(paper.pdf_url):
            paper.raw["discarded_pdf_url"] = paper.pdf_url
            paper.pdf_url = None


def enrich_open_access_links(papers: list[Paper], config: GeneralConfig) -> None:
    dois = sorted({paper.doi for paper in papers if paper.doi})
    if not dois:
        return
    headers = {"User-Agent": config.user_agent}
    params = {}
    if config.contact_email:
        params["email"] = config.contact_email

    try:
        with httpx.Client(
            timeout=config.request_timeout_seconds, headers=headers
        ) as client:
            for doi in dois:
                response = client.get(
                    f"https://api.unpaywall.org/v2/{doi}",
                    params=params,
                )
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                payload = response.json()
                _apply_unpaywall(papers, doi, payload)
    except httpx.HTTPError:
        return


def looks_like_pdf_url(url: str) -> bool:
    lowered = url.lower()
    if any(hint in lowered for hint in BAD_PDF_HINTS):
        return False
    return any(hint in lowered for hint in PDF_HINTS)


def _apply_unpaywall(papers: list[Paper], doi: str, payload: dict[str, Any]) -> None:
    best = payload.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf") or best.get("url")
    landing_url = best.get("url_for_landing_page")
    is_oa = payload.get("is_oa")
    oa_status = payload.get("oa_status")
    for paper in papers:
        if not paper.doi or paper.doi.lower() != doi.lower():
            continue
        if oa_status:
            paper.oa_status = oa_status
        elif is_oa is not None:
            paper.oa_status = "oa" if is_oa else "closed"
        if pdf_url and looks_like_pdf_url(pdf_url):
            paper.pdf_url = paper.pdf_url or pdf_url
        if landing_url:
            paper.url = paper.url or landing_url


def filter_low_quality(papers: list[Paper]) -> list[Paper]:
    """Remove low-quality records before they reach the user.

    A paper is removed if:
    - Has a relevance_score of 0 AND no title match with any term
    - Title is shorter than 3 characters
    - Has no abstract AND relevance_score < 2.0 (weak evidence)
    """
    result = []
    for paper in papers:
        title = (paper.title or "").strip()
        if len(title) < 3:
            continue
        score = paper.relevance_score or 0
        if score <= 0:
            continue
        has_title_match = bool(
            paper.relevance_reasons
            and any("标题" in r for r in paper.relevance_reasons)
        )
        if not has_title_match and score < 1.0:
            continue
        result.append(paper)
    return result


def _count_term_hits(text: str, term_list: list[str]) -> int:
    """Count how many distinct terms from term_list appear in text."""
    if not text:
        return 0
    hits = 0
    for term in term_list:
        if term in text:
            hits += 1
    return hits
