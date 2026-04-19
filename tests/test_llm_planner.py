from litassist.config import AppConfig
from litassist.llm_planner import _extract_json, _plan_from_payload
from litassist.pipeline import _build_search_plan
from litassist.planner import build_plan


def test_extract_json_from_responses_output_text():
    payload = _extract_json({"output_text": '{"zh_keywords":["文献检索"]}'})

    assert payload == {"zh_keywords": ["文献检索"]}


def test_plan_from_payload_builds_structured_plan():
    seed = build_plan("人工智能辅助文献检索")
    payload = {
        "research_questions": ["AI 如何辅助文献检索？"],
        "core_concepts": [
            {
                "label_zh": "人工智能",
                "label_en": "artificial intelligence",
                "synonyms_zh": ["AI"],
                "synonyms_en": ["AI"],
            }
        ],
        "zh_keywords": ["人工智能", "文献检索"],
        "en_keywords": ["artificial intelligence", "literature retrieval"],
        "inclusion_criteria": ["同行评议研究"],
        "exclusion_criteria": ["非学术评论"],
        "search_strategy": ["先宽后窄"],
        "queries": {
            "openalex": "artificial intelligence literature retrieval",
            "crossref": "artificial intelligence literature retrieval",
            "semantic_scholar": "artificial intelligence literature retrieval",
            "web_of_science": 'TS=("artificial intelligence")',
            "cnki": "人工智能 OR 文献检索",
        },
        "notes": ["测试"],
    }

    plan = _plan_from_payload("人工智能辅助文献检索", payload, seed)

    assert plan.planner == "llm"
    assert plan.research_questions == ["AI 如何辅助文献检索？"]
    assert plan.queries["cnki"] == "人工智能 OR 文献检索"


def test_build_search_plan_falls_back_without_api_key():
    plan = _build_search_plan(
        "人工智能辅助文献检索",
        config=AppConfig(),
        zh_keywords=None,
        en_keywords=None,
        use_llm=True,
    )

    assert plan.planner == "rules"
    assert any("LLM planning unavailable" in note for note in plan.notes)
