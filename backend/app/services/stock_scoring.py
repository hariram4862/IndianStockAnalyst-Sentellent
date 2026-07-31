from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# Conservative persona / "avoid high-debt" constraint hard-filter threshold.
# Debt-to-equity above this excludes a stock from recommendations entirely
# rather than merely down-weighting it — matches the challenge's own example
# ("I avoid high-debt companies" -> screen out the high-debt names).
CONSERVATIVE_DEBT_TO_EQUITY_LIMIT = 1.5

DEFAULT_WEIGHTS = {"value": 0.30, "stability": 0.35, "momentum": 0.35}


@dataclass(frozen=True)
class ScorableStock:
    ticker: str
    company_name: str
    pe_ratio: float | None
    dividend_yield: float | None
    debt_to_equity: float | None
    rolling_sentiment_score: float | None
    rolling_sentiment_label: str | None


@dataclass(frozen=True)
class RankedStock:
    ticker: str
    company_name: str
    composite_score: float
    value_score: float
    stability_score: float
    momentum_score: float
    reason: str


def from_stock_entity(stock: object) -> ScorableStock:
    """Adapt an app.models.stock.StockEntity (or any duck-typed equivalent) into
    the plain, DB-independent shape this module scores against."""
    return ScorableStock(
        ticker=stock.ticker,
        company_name=stock.company_name,
        pe_ratio=_as_float(stock.pe_ratio),
        dividend_yield=_as_float(stock.dividend_yield),
        debt_to_equity=_as_float(stock.debt_to_equity),
        rolling_sentiment_score=_as_float(stock.rolling_sentiment_score),
        rolling_sentiment_label=stock.rolling_sentiment_label,
    )


def rank_stocks(
    stocks: Sequence[ScorableStock],
    risk_profile: str | None,
    investment_style: str | None,
    constraints_text: str | None,
) -> list[RankedStock]:
    """Deterministic, testable persona-based ranking — no LLM call per stock.

    Scores each stock against the user's *own followed set* (no external peer
    database is available or needed) across three normalized 0-1 dimensions,
    then combines them with persona-dependent weights. A conservative persona
    or an explicit "avoid high debt" constraint hard-filters high-leverage
    names out entirely rather than just down-weighting them.
    """
    if not stocks:
        return []

    apply_debt_filter = risk_profile == "conservative" or _mentions_avoid_high_debt(constraints_text)
    candidates = [
        stock
        for stock in stocks
        if not (
            apply_debt_filter
            and stock.debt_to_equity is not None
            and stock.debt_to_equity > CONSERVATIVE_DEBT_TO_EQUITY_LIMIT
        )
    ]
    if not candidates:
        return []

    value_scores = _min_max_normalize([s.pe_ratio for s in candidates], invert=True)
    stability_scores = _stability_scores(candidates)
    momentum_scores = [_sentiment_to_unit(s.rolling_sentiment_score) for s in candidates]

    weights = _persona_weights(risk_profile, investment_style)

    ranked = [
        RankedStock(
            ticker=stock.ticker,
            company_name=stock.company_name,
            composite_score=round(
                value_scores[i] * weights["value"]
                + stability_scores[i] * weights["stability"]
                + momentum_scores[i] * weights["momentum"],
                4,
            ),
            value_score=round(value_scores[i], 4),
            stability_score=round(stability_scores[i], 4),
            momentum_score=round(momentum_scores[i], 4),
            reason=_build_reason(stock),
        )
        for i, stock in enumerate(candidates)
    ]

    ranked.sort(key=lambda r: r.composite_score, reverse=True)
    return ranked


def _persona_weights(risk_profile: str | None, investment_style: str | None) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)

    if risk_profile == "conservative":
        _shift(weights, take_from="momentum", give_to="stability", amount=0.15)
    elif risk_profile == "aggressive":
        _shift(weights, take_from="stability", give_to="momentum", amount=0.15)

    if investment_style == "dividend-focused":
        _shift(weights, take_from="momentum", give_to="stability", amount=0.15)
    elif investment_style == "growth-oriented":
        _shift(weights, take_from="stability", give_to="momentum", amount=0.15)

    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def _shift(weights: dict[str, float], take_from: str, give_to: str, amount: float) -> None:
    moved = min(amount, weights[take_from])
    weights[take_from] -= moved
    weights[give_to] += moved


def _stability_scores(stocks: Sequence[ScorableStock]) -> list[float]:
    debt_scores = _min_max_normalize([s.debt_to_equity for s in stocks], invert=True)
    dividend_scores = _min_max_normalize([s.dividend_yield for s in stocks], invert=False)
    return [(debt_scores[i] + dividend_scores[i]) / 2 for i in range(len(stocks))]


def _sentiment_to_unit(score: float | None) -> float:
    if score is None:
        return 0.5
    return max(0.0, min(1.0, (score + 1) / 2))


def _min_max_normalize(values: Sequence[float | None], invert: bool) -> list[float]:
    known = [v for v in values if v is not None]
    if not known or max(known) == min(known):
        return [0.5 for _ in values]

    lo, hi = min(known), max(known)
    result = []
    for value in values:
        if value is None:
            result.append(0.5)
            continue
        normalized = (value - lo) / (hi - lo)
        result.append(1 - normalized if invert else normalized)
    return result


def _mentions_avoid_high_debt(constraints_text: str | None) -> bool:
    if not constraints_text:
        return False
    lowered = constraints_text.lower()
    return "avoid" in lowered and "debt" in lowered


def _build_reason(stock: ScorableStock) -> str:
    parts = []
    parts.append(f"P/E {stock.pe_ratio:.1f}" if stock.pe_ratio is not None else "P/E n/a")
    parts.append(f"D/E {stock.debt_to_equity:.2f}" if stock.debt_to_equity is not None else "D/E n/a")
    parts.append(
        f"dividend yield {stock.dividend_yield:.1f}%" if stock.dividend_yield is not None else "dividend yield n/a"
    )
    sentiment_label = stock.rolling_sentiment_label or "neutral"
    sentiment_score = f"{stock.rolling_sentiment_score:+.2f}" if stock.rolling_sentiment_score is not None else "n/a"
    parts.append(f"news sentiment {sentiment_label} ({sentiment_score})")
    return ", ".join(parts) + "."


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
