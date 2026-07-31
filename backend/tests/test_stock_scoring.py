from app.services.stock_scoring import ScorableStock, rank_stocks


def _stock(
    ticker: str,
    pe_ratio: float | None = 20.0,
    dividend_yield: float | None = 1.0,
    debt_to_equity: float | None = 0.5,
    rolling_sentiment_score: float | None = 0.0,
    rolling_sentiment_label: str | None = "neutral",
) -> ScorableStock:
    return ScorableStock(
        ticker=ticker,
        company_name=f"{ticker} Ltd",
        pe_ratio=pe_ratio,
        dividend_yield=dividend_yield,
        debt_to_equity=debt_to_equity,
        rolling_sentiment_score=rolling_sentiment_score,
        rolling_sentiment_label=rolling_sentiment_label,
    )


def test_empty_followed_list_returns_empty_ranking():
    assert rank_stocks([], risk_profile=None, investment_style=None, constraints_text=None) == []


def test_conservative_persona_filters_out_high_debt_names():
    stocks = [
        _stock("SAFE", debt_to_equity=0.3),
        _stock("LEVERAGED", debt_to_equity=2.5),
    ]

    ranked = rank_stocks(stocks, risk_profile="conservative", investment_style=None, constraints_text=None)

    tickers = [r.ticker for r in ranked]
    assert "LEVERAGED" not in tickers
    assert "SAFE" in tickers


def test_avoid_high_debt_constraint_filters_regardless_of_risk_profile():
    stocks = [
        _stock("SAFE", debt_to_equity=0.3),
        _stock("LEVERAGED", debt_to_equity=2.5),
    ]

    ranked = rank_stocks(
        stocks,
        risk_profile=None,
        investment_style=None,
        constraints_text="I avoid high-debt companies",
    )

    tickers = [r.ticker for r in ranked]
    assert "LEVERAGED" not in tickers
    assert "SAFE" in tickers


def test_growth_persona_favors_positive_momentum_name():
    stocks = [
        _stock("MOMENTUM", rolling_sentiment_score=0.9, rolling_sentiment_label="positive"),
        _stock("LAGGARD", rolling_sentiment_score=-0.9, rolling_sentiment_label="negative"),
    ]

    ranked = rank_stocks(stocks, risk_profile=None, investment_style="growth-oriented", constraints_text=None)

    assert ranked[0].ticker == "MOMENTUM"
    assert ranked[0].composite_score > ranked[1].composite_score


def test_conservative_persona_favors_low_debt_high_dividend_name():
    stocks = [
        _stock("STABLE", debt_to_equity=0.2, dividend_yield=4.0),
        _stock("RISKIER", debt_to_equity=1.4, dividend_yield=0.5),
    ]

    ranked = rank_stocks(stocks, risk_profile="conservative", investment_style=None, constraints_text=None)

    assert ranked[0].ticker == "STABLE"


def test_reason_string_is_built_from_actual_numbers_not_a_placeholder():
    stocks = [_stock("RELIANCE", pe_ratio=24.5, debt_to_equity=0.41, dividend_yield=1.4)]

    ranked = rank_stocks(stocks, risk_profile=None, investment_style=None, constraints_text=None)

    reason = ranked[0].reason
    assert "24.5" in reason
    assert "0.41" in reason
    assert "1.4" in reason


def test_missing_fundamentals_do_not_crash_and_default_neutral():
    stocks = [_stock("UNKNOWN", pe_ratio=None, dividend_yield=None, debt_to_equity=None, rolling_sentiment_score=None)]

    ranked = rank_stocks(stocks, risk_profile=None, investment_style=None, constraints_text=None)

    assert len(ranked) == 1
    assert ranked[0].composite_score == 0.5
