from __future__ import annotations

import time

from app.services.providers import FundamentalsPayload

try:
    import yfinance as yf
except Exception:  # pragma: no cover - handled by runtime fallback
    yf = None


# Every ingest_ticker() call (a manual follow, a scheduled refresh, the
# migration smoke test, ...) would otherwise re-hit yfinance even when nothing
# could plausibly have changed since the last fetch a few minutes ago. This
# in-process cache avoids that redundant network round-trip; it deliberately
# does not need to be shared across processes since a stale cache just means
# one extra live fetch, never incorrect data (the DB row is always what's
# actually persisted).
FUNDAMENTALS_CACHE_TTL_SECONDS = 300
_fundamentals_cache: dict[str, tuple[float, FundamentalsPayload | None]] = {}


class FundamentalsProvider:
    def fetch(self, ticker: str) -> FundamentalsPayload | None:
        cached = _fundamentals_cache.get(ticker)
        if cached is not None and time.monotonic() - cached[0] < FUNDAMENTALS_CACHE_TTL_SECONDS:
            return cached[1]

        payload = self._fetch_live(ticker)
        _fundamentals_cache[ticker] = (time.monotonic(), payload)
        return payload

    def _fetch_live(self, ticker: str) -> FundamentalsPayload | None:
        # No hard-coded ticker map: any valid NSE symbol works by construction
        # (ticker + ".NS"), so following a new stock doesn't require a code
        # change. yfinance doesn't raise for an unknown symbol — it returns a
        # near-empty info dict — so validity is checked below instead.
        if yf is None:
            return None

        try:
            instrument = yf.Ticker(f"{ticker}.NS")
            info = instrument.info
        except Exception:
            return None

        if not info or not (info.get("longName") or info.get("shortName")):
            return None

        company_name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector")
        industry = info.get("industry")
        market_cap = _to_float(info.get("marketCap"))
        current_price = _to_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        pe_ratio = _to_float(info.get("trailingPE"))
        dividend_yield = _yield_to_percent(info.get("dividendYield"))
        debt_to_equity = _to_float(info.get("debtToEquity"))
        exchange = "NSE"
        summary = (
            f"{company_name} is listed on the {exchange}. "
            f"Sector: {sector or 'unknown'}. Industry: {industry or 'unknown'}. "
            f"Current price: {format_inr(current_price)}. "
            f"Market cap: {format_inr(market_cap)}. "
            f"P/E: {format_number(pe_ratio)}. Dividend yield: {format_percent(dividend_yield)}. "
            f"Debt to equity: {format_number(debt_to_equity)}."
        )

        return FundamentalsPayload(
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            sector=sector,
            industry=industry,
            isin=info.get("isin"),
            market_cap_inr=market_cap,
            current_price_inr=current_price,
            pe_ratio=pe_ratio,
            dividend_yield=dividend_yield,
            debt_to_equity=debt_to_equity,
            fundamentals_summary=summary,
        )


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _yield_to_percent(value: object) -> float | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return numeric * 100


def format_inr(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"Rs. {value:,.2f}"


def format_number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"
