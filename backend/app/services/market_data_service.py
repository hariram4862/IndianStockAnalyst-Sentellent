from __future__ import annotations

import time

try:
    import yfinance as yf
except Exception:  # pragma: no cover - handled by runtime fallback
    yf = None

# No free tick-by-tick NSE/BSE feed exists; this service auto-refreshes on a
# short interval instead of streaming, using the same yfinance source the
# rest of the app already relies on -- one extra provider, not a second one.
INDEX_SYMBOLS = [
    ("NIFTY 50", "^NSEI"),
    ("SENSEX", "^BSESN"),
    ("NIFTY BANK", "^NSEBANK"),
    ("NIFTY NEXT 50", "^NSMIDCP"),
    ("NIFTY IT", "^CNXIT"),
    ("NIFTY AUTO", "^CNXAUTO"),
    ("NIFTY PHARMA", "^CNXPHARMA"),
    ("NIFTY FMCG", "^CNXFMCG"),
    ("INDIA VIX", "^INDIAVIX"),
]

# Fixed, well-known Nifty 50 constituent list (index membership changes only a
# few times a year) used as the scan universe for market-wide movers -- one
# batched yfinance call over ~50 tickers, not a live "all NSE stocks" pull.
NIFTY50_CONSTITUENTS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
    "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM",
    "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO",
    "HINDUNILVR", "ICICIBANK", "ITC", "INDUSINDBK", "INFY",
    "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI",
    "NTPC", "NESTLEIND", "ONGC", "POWERGRID", "RELIANCE",
    "SBILIFE", "SHRIRAMFIN", "SBIN", "SUNPHARMA", "TCS",
    "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN",
    "TRENT", "ULTRACEMCO", "WIPRO",
]

INDEX_CACHE_TTL_SECONDS = 60
INTRADAY_CACHE_TTL_SECONDS = 60
MOVERS_CACHE_TTL_SECONDS = 300

_index_cache: tuple[float, list[dict]] | None = None
_intraday_cache: dict[str, tuple[float, list[dict]]] = {}
_all_intraday_cache: tuple[float, dict[str, list[dict]]] | None = None
_movers_cache: tuple[float, dict] | None = None


class MarketDataService:
    def get_index_quotes(self) -> list[dict]:
        global _index_cache
        if _index_cache is not None and time.monotonic() - _index_cache[0] < INDEX_CACHE_TTL_SECONDS:
            return _index_cache[1]

        quotes = self._fetch_index_quotes()
        _index_cache = (time.monotonic(), quotes)
        return quotes

    def _fetch_index_quotes(self) -> list[dict]:
        if yf is None:
            return []

        symbols = [symbol for _name, symbol in INDEX_SYMBOLS]
        try:
            tickers = yf.Tickers(" ".join(symbols))
        except Exception:
            return []

        quotes = []
        for name, symbol in INDEX_SYMBOLS:
            try:
                info = tickers.tickers[symbol].info
                price = _to_float(info.get("regularMarketPrice") or info.get("currentPrice"))
                previous_close = _to_float(info.get("regularMarketPreviousClose") or info.get("previousClose"))
            except Exception:
                price, previous_close = None, None

            if price is None or previous_close is None or previous_close == 0:
                continue

            change = price - previous_close
            quotes.append(
                {
                    "name": name,
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": round((change / previous_close) * 100, 2),
                }
            )
        return quotes

    def get_index_intraday(self, symbol: str, limit: int = 60) -> list[dict]:
        cached = _intraday_cache.get(symbol)
        if cached is not None and time.monotonic() - cached[0] < INTRADAY_CACHE_TTL_SECONDS:
            return cached[1]

        points = self._fetch_index_intraday(symbol, limit)
        _intraday_cache[symbol] = (time.monotonic(), points)
        return points

    def _fetch_index_intraday(self, symbol: str, limit: int) -> list[dict]:
        if yf is None:
            return []
        try:
            history = yf.Ticker(symbol).history(period="1d", interval="5m")
        except Exception:
            return []
        if history is None or history.empty:
            return []

        closes = history["Close"].tail(limit)
        return [{"time": ts.isoformat(), "price": round(float(value), 2)} for ts, value in closes.items()]

    def get_all_index_intraday(self, limit: int = 30) -> dict[str, list[dict]]:
        global _all_intraday_cache
        if _all_intraday_cache is not None and time.monotonic() - _all_intraday_cache[0] < INTRADAY_CACHE_TTL_SECONDS:
            return _all_intraday_cache[1]

        series = self._fetch_all_index_intraday(limit)
        _all_intraday_cache = (time.monotonic(), series)
        return series

    def _fetch_all_index_intraday(self, limit: int) -> dict[str, list[dict]]:
        symbols = [symbol for _name, symbol in INDEX_SYMBOLS]
        if yf is None:
            return {symbol: [] for symbol in symbols}

        try:
            data = yf.download(
                symbols, period="1d", interval="5m", group_by="ticker", progress=False, threads=True
            )
        except Exception:
            return {symbol: [] for symbol in symbols}

        series: dict[str, list[dict]] = {}
        for symbol in symbols:
            try:
                closes = data[symbol]["Close"].dropna().tail(limit)
                series[symbol] = [
                    {"time": ts.isoformat(), "price": round(float(value), 2)} for ts, value in closes.items()
                ]
            except Exception:
                series[symbol] = []
        return series

    def get_market_movers(self, limit: int = 5) -> dict:
        global _movers_cache
        if _movers_cache is not None and time.monotonic() - _movers_cache[0] < MOVERS_CACHE_TTL_SECONDS:
            return _movers_cache[1]

        movers = self._fetch_market_movers(limit)
        _movers_cache = (time.monotonic(), movers)
        return movers

    def _fetch_market_movers(self, limit: int) -> dict:
        if yf is None:
            return {"gainers": [], "losers": []}

        yf_symbols = [f"{ticker}.NS" for ticker in NIFTY50_CONSTITUENTS]
        try:
            data = yf.download(
                yf_symbols, period="2d", interval="1d", group_by="ticker", progress=False, threads=True
            )
        except Exception:
            return {"gainers": [], "losers": []}

        changes: list[dict] = []
        for ticker, yf_symbol in zip(NIFTY50_CONSTITUENTS, yf_symbols):
            try:
                closes = data[yf_symbol]["Close"].dropna()
                if len(closes) < 2:
                    continue
                previous_close, price = float(closes.iloc[-2]), float(closes.iloc[-1])
                if previous_close == 0:
                    continue
                change_percent = ((price - previous_close) / previous_close) * 100
                changes.append(
                    {
                        "ticker": ticker,
                        "price": round(price, 2),
                        "change_percent": round(change_percent, 2),
                    }
                )
            except Exception:
                continue

        ranked = sorted(changes, key=lambda item: item["change_percent"], reverse=True)
        return {"gainers": ranked[:limit], "losers": list(reversed(ranked[-limit:])) if ranked else []}


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
