from app.services.agent_graph import (
    _classify_intent,
    _extract_persona_via_keywords,
    _extract_ticker_mentions,
    _extract_unfollowed_ticker_mentions,
    _looks_research_related,
    _merge_text,
)


def test_classify_intent_recommend():
    assert _classify_intent("What should I buy this week?") == "recommend"
    assert _classify_intent("Recommend stocks for my profile") == "recommend"


def test_classify_intent_research():
    assert _classify_intent("What's the sentiment on TCS this week?") == "research"
    assert _classify_intent("Tell me the fundamentals") == "research"


def test_classify_intent_chitchat():
    assert _classify_intent("hello") == "chitchat"
    assert _classify_intent("") == "chitchat"
    assert _classify_intent("thanks!") == "chitchat"


def test_extract_ticker_mentions_only_matches_followed_tickers():
    followed = ["RELIANCE", "TCS"]
    assert _extract_ticker_mentions("What about RELIANCE and INFY?", followed) == ["RELIANCE"]
    assert _extract_ticker_mentions("no tickers here", followed) == []


def test_extract_unfollowed_ticker_mentions_flags_unfollowed_named_ticker():
    followed = ["RELIANCE"]
    assert _extract_unfollowed_ticker_mentions("What's the debt situation at INFY?", followed) == ["INFY"]


def test_extract_unfollowed_ticker_mentions_ignores_followed_tickers():
    followed = ["RELIANCE"]
    assert _extract_unfollowed_ticker_mentions("What's the debt situation at RELIANCE?", followed) == []


def test_extract_unfollowed_ticker_mentions_ignores_common_acronyms():
    followed = []
    assert _extract_unfollowed_ticker_mentions("What's the NSE IPO outlook in INR terms?", followed) == []


def test_looks_research_related():
    assert _looks_research_related("what's the debt situation") is True
    assert _looks_research_related("hello") is False
    assert _looks_research_related("") is False


def test_extract_persona_via_keywords_captures_avoid_constraint():
    result = _extract_persona_via_keywords("I'm a conservative, dividend-focused investor and I avoid high-debt companies.")
    assert result["risk_profile"] == "conservative"
    assert result["investment_style"] == "dividend-focused"
    assert "avoid" in result["constraint"].lower()
    assert result["summary_delta"]


def test_extract_persona_via_keywords_no_signal():
    result = _extract_persona_via_keywords("what's the weather like")
    assert result["risk_profile"] is None
    assert result["investment_style"] is None
    assert result["constraint"] is None
    assert result["summary_delta"] is None


def test_merge_text_appends_new_fact_without_losing_old_one():
    merged = _merge_text("Investor prefers conservative risk.", "Investor values growth.")
    assert "conservative" in merged
    assert "growth" in merged


def test_merge_text_does_not_duplicate_repeated_fact():
    existing = "Investor prefers conservative risk."
    merged = _merge_text(existing, "Investor prefers conservative risk.")
    assert merged == existing


def test_merge_text_truncates_to_max_length_keeping_recent_content():
    existing = "a" * 900
    merged = _merge_text(existing, "brand new fact", max_length=800)
    assert len(merged) <= 800
    assert "brand new fact" in merged
