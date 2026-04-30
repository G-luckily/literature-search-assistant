from litassist.planner import build_plan, _extract_research_structure


def test_build_plan_extracts_known_bilingual_terms():
    plan = build_plan("我想研究人工智能辅助文献检索与Zotero协同管理")

    assert "人工智能" in plan.zh_keywords
    assert "文献检索" in plan.zh_keywords
    assert "artificial intelligence" in plan.en_keywords
    assert "literature retrieval" in plan.en_keywords
    assert "TS=(" in plan.queries["web_of_science"]
    assert len(plan.query_rounds["openalex"]) >= 2
    assert len(plan.query_rounds["semantic_scholar"]) >= 2
    assert any(
        query.startswith("TS=(") for query in plan.query_rounds["web_of_science"]
    )


def test_build_plan_accepts_manual_keywords():
    plan = build_plan(
        "研究需求",
        zh_keywords=["文献计量"],
        en_keywords=["bibliometrics"],
    )

    assert plan.zh_keywords[0] == "文献计量"
    assert plan.en_keywords[0] == "bibliometrics"
    assert plan.query_rounds["openalex"][0] == plan.queries["openalex"]


def test_extract_research_structure_elderly_ai():
    """Test structured parsing of a multi-dimensional research need."""
    struct = _extract_research_structure("我想研究人工智能如何为老年人提供情感陪伴")
    assert "人工智能" in struct["technology"] or "AI" in struct["technology"]
    assert any("老年" in t for t in struct["population"])
    assert any("陪伴" in t or "情感" in t for t in struct["phenomenon"])


def test_build_plan_structured_queries():
    """Test that structured queries combine dimensions for better precision."""
    plan = build_plan("人工智能对老年人情感陪伴的影响")
    query = plan.queries.get("openalex", "")
    # Should include terms from at least two different research dimensions
    assert any(term in query for term in ["人工智能", "AI", "artificial"])
    assert any(term in query for term in ["老年", "elderly"])
    assert any(term in query for term in ["陪伴", "companion", "情感"])


def test_build_plan_query_rounds_strategy_buckets():
    """Test that query rounds include strategy buckets beyond flat keyword lists."""
    plan = build_plan("人工智能与老年人心理健康")
    rounds = plan.query_rounds.get("openalex", [])
    # Should have at least the primary query plus some strategy buckets
    assert len(rounds) >= 3
    # At least one round should combine multiple dimensions
    dimension_terms = [
        "artificial",
        "intelligence",
        "elderly",
        "older",
        "mental",
        "health",
    ]
    has_combined = any(
        sum(term in rq.lower() for term in dimension_terms) >= 2 for rq in rounds
    )
    assert has_combined, f"No round combines multiple dimensions: {rounds}"
