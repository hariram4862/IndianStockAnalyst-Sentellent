from app.services.news_provider import _derive_aliases, _mentions_alias


def test_single_word_company_name_adds_bare_word_alias():
    # "Infosys Limited" -> "Infosys" alone is safe to match on since it's the
    # one distinguishing word left after stripping "Limited".
    aliases = _derive_aliases("INFY", "Infosys Limited")
    assert "INFY" in aliases
    assert "Infosys" in aliases
    assert _mentions_alias("Infosys posts strong Q1 results", aliases)


def test_multi_word_company_name_does_not_add_generic_first_word_alone():
    # "Tata Consultancy Services Limited" -> the bare first word "Tata" is
    # shared by many unrelated listed Tata group companies, so it must not
    # be added as a standalone alias (would cause false-positive matches).
    aliases = _derive_aliases("TCS", "Tata Consultancy Services Limited")
    assert "Tata" not in aliases
    assert "Tata Consultancy Services" in aliases
    assert not _mentions_alias("Tata Motors launches new EV lineup", aliases)
    assert _mentions_alias("Tata Consultancy Services wins big deal", aliases)


def test_ticker_alone_still_matches_without_company_name():
    aliases = _derive_aliases("RELIANCE", None)
    assert aliases == ["RELIANCE"]
    assert _mentions_alias("RELIANCE shares rally", aliases)


def test_known_hardcoded_tickers_still_match_as_before():
    aliases = _derive_aliases("HDFCBANK", "HDFC Bank Limited")
    assert _mentions_alias("HDFC Bank reports steady deposit growth", aliases)
    assert _mentions_alias("HDFCBANK hits new high", aliases)
