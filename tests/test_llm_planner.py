from litassist.config import AppConfig, load_config
from litassist.llm_planner import (
    _chat_completions_endpoint,
    _extract_chat_json,
    _extract_json,
    _plan_from_payload,
)
from litassist.pipeline import _build_search_plan
from litassist.planner import build_plan


def test_extract_json_from_responses_output_text():
    payload = _extract_json({"output_text": '{"zh_keywords":["文献检索"]}'})

    assert payload == {"zh_keywords": ["文献检索"]}


def test_extract_chat_json_from_deepseek_choice():
    payload = _extract_chat_json(
        {"choices": [{"message": {"content": '{"zh_keywords":["文献检索"]}'}}]}
    )

    assert payload == {"zh_keywords": ["文献检索"]}


def test_extract_chat_json_strips_markdown_fence():
    payload = _extract_chat_json(
        {"choices": [{"message": {"content": '```json\n{"zh_keywords":["AI"]}\n```'}}]}
    )

    assert payload == {"zh_keywords": ["AI"]}


def test_chat_completions_endpoint_normalizes_base_url():
    assert (
        _chat_completions_endpoint("https://api.deepseek.com/v1")
        == "https://api.deepseek.com/v1/chat/completions"
    )
    assert (
        _chat_completions_endpoint(
            "https://api.deepseek.com/v1/chat/completions/"
        )
        == "https://api.deepseek.com/v1/chat/completions"
    )


def test_load_config_uses_deepseek_environment(monkeypatch):
    monkeypatch.setenv("LITASSIST_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    config = load_config("missing-config.toml")

    assert config.llm.provider == "deepseek"
    assert config.llm.api_key == "secret"
    assert config.llm.model == "deepseek-chat"
    assert config.llm.endpoint == "https://api.deepseek.com/v1"


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
