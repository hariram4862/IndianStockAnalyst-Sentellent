from app.services.agent_graph import (
    _carry_forward_ticker,
    _classify_intent,
    _extract_persona_via_keywords,
    _extract_ticker_mentions,
    _extract_unfollowed_ticker_mentions,
    _looks_research_related,
    _merge_text,
    _trim_history_for_prompt,
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


def test_classify_intent_memory():
    assert _classify_intent("What do you know about me?") == "memory"
    assert _classify_intent("What's my investor profile?") == "memory"
    assert _classify_intent("What's my profile") == "memory"


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


def test_carry_forward_ticker_finds_last_mentioned_followed_ticker():
    followed = ["RELIANCE", "TCS"]
    history = [
        ("user", "What's the sentiment on TCS this week?"),
        ("assistant", "TCS sentiment is positive per [1]."),
    ]
    assert _carry_forward_ticker(history, followed) == ["TCS"]


def test_carry_forward_ticker_prefers_the_most_recent_mention():
    followed = ["RELIANCE", "TCS"]
    history = [
        ("user", "What's the sentiment on RELIANCE?"),
        ("assistant", "RELIANCE sentiment is neutral per [1]."),
        ("user", "And TCS?"),
        ("assistant", "TCS sentiment is positive per [1]."),
    ]
    assert _carry_forward_ticker(history, followed) == ["TCS"]


def test_carry_forward_ticker_returns_empty_when_nothing_mentioned():
    followed = ["RELIANCE"]
    history = [("user", "hello"), ("assistant", "Hi! Ask me about a stock you follow.")]
    assert _carry_forward_ticker(history, followed) == []


def test_carry_forward_ticker_returns_empty_for_no_history():
    assert _carry_forward_ticker([], ["RELIANCE"]) == []


def test_trim_history_for_prompt_caps_message_count_and_length():
    history = [("user", f"message {i}") for i in range(20)]
    trimmed = _trim_history_for_prompt(history)
    assert len(trimmed) <= 8
    assert trimmed[-1] == ("user", "message 19")


def test_trim_history_for_prompt_caps_each_message_length():
    history = [("user", "x" * 5000)]
    trimmed = _trim_history_for_prompt(history)
    assert len(trimmed[0][1]) <= 600


def test_extract_persona_via_keywords_captures_avoid_constraint():
    result = _extract_persona_via_keywords("I'm a conservative, dividend-focused investor and I avoid high-debt companies.")
    assert result["risk_profile"] == "conservative"
    assert result["investment_style"] == "dividend-focused"
    assert "avoid" in result["constraint"].lower()
    assert result["summary_delta"]


def test_extract_persona_via_keywords_ignores_questions_sharing_a_trait_word():
    """Regression: "and its dividend yield?" must not be read as a
    "dividend-focused" persona statement just because it contains the word
    "dividend" -- it's a question about a stock, not a self-declaration."""
    result = _extract_persona_via_keywords("and its dividend yield?")
    assert result["investment_style"] is None
    assert result["summary_delta"] is None


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
