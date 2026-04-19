from litassist.planner import build_plan


def test_build_plan_extracts_known_bilingual_terms():
    plan = build_plan("我想研究人工智能辅助文献检索与Zotero协同管理")

    assert "人工智能" in plan.zh_keywords
    assert "文献检索" in plan.zh_keywords
    assert "artificial intelligence" in plan.en_keywords
    assert "literature retrieval" in plan.en_keywords
    assert "TS=(" in plan.queries["web_of_science"]


def test_build_plan_accepts_manual_keywords():
    plan = build_plan(
        "研究需求",
        zh_keywords=["文献计量"],
        en_keywords=["bibliometrics"],
    )

    assert plan.zh_keywords[0] == "文献计量"
    assert plan.en_keywords[0] == "bibliometrics"
