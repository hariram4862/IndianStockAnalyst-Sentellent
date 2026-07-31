import pandas as pd

from app.services import market_data_service as module
from app.services.market_data_service import MarketDataService


class _FakeInstrument:
    def __init__(self, info=None, history_df=None):
        self.info = info or {}
        self._history_df = history_df

    def history(self, period=None, interval=None):
        return self._history_df


class _FakeTickers:
    def __init__(self, tickers_by_symbol):
        self.tickers = tickers_by_symbol


def _clear_caches():
    module._index_cache = None
    module._intraday_cache.clear()
    module._all_intraday_cache = None
    module._movers_cache = None


def test_get_index_quotes_computes_change_from_previous_close(monkeypatch):
    _clear_caches()

    fake_tickers = _FakeTickers(
        {
            "^NSEI": _FakeInstrument({"regularMarketPrice": 24400.0, "regularMarketPreviousClose": 24300.0}),
            "^BSESN": _FakeInstrument({"regularMarketPrice": 100.0, "regularMarketPreviousClose": 100.0}),
            "^NSMIDCP": _FakeInstrument({}),  # missing data -- must be skipped, not crash
            "^CNXIT": _FakeInstrument({"regularMarketPrice": 500.0, "regularMarketPreviousClose": 1000.0}),
        }
    )

    class _FakeYFModule:
        @staticmethod
        def Tickers(symbols):
            return fake_tickers

    monkeypatch.setattr(module, "yf", _FakeYFModule())

    quotes = MarketDataService().get_index_quotes()
    by_symbol = {q["symbol"]: q for q in quotes}

    assert by_symbol["^NSEI"]["change"] == 100.0
    assert round(by_symbol["^NSEI"]["change_percent"], 2) == round((100.0 / 24300.0) * 100, 2)
    assert by_symbol["^BSESN"]["change_percent"] == 0.0
    assert by_symbol["^CNXIT"]["change_percent"] == -50.0
    assert "^NSMIDCP" not in by_symbol


def test_get_index_quotes_caches_within_ttl(monkeypatch):
    _clear_caches()
    call_count = {"n": 0}

    class _CountingYF:
        @staticmethod
        def Tickers(symbols):
            call_count["n"] += 1
            return _FakeTickers(
                {symbol: _FakeInstrument({"regularMarketPrice": 1.0, "regularMarketPreviousClose": 1.0}) for symbol in symbols.split()}
            )

    monkeypatch.setattr(module, "yf", _CountingYF())

    service = MarketDataService()
    service.get_index_quotes()
    service.get_index_quotes()

    assert call_count["n"] == 1


def test_get_market_movers_ranks_gainers_and_losers(monkeypatch):
    _clear_caches()

    # Two constituents' worth of fake 2-day close data, shaped like yfinance's
    # group_by="ticker" MultiIndex download output.
    frame = pd.DataFrame(
        {
            ("RELIANCE.NS", "Close"): [100.0, 110.0],  # +10%
            ("TCS.NS", "Close"): [200.0, 180.0],  # -10%
        }
    )
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)

    class _FakeYFModule:
        @staticmethod
        def download(*args, **kwargs):
            return frame

    monkeypatch.setattr(module, "yf", _FakeYFModule())
    monkeypatch.setattr(module, "NIFTY50_CONSTITUENTS", ["RELIANCE", "TCS"])

    movers = MarketDataService().get_market_movers(limit=5)

    assert movers["gainers"][0]["ticker"] == "RELIANCE"
    assert movers["gainers"][0]["change_percent"] == 10.0
    assert movers["losers"][0]["ticker"] == "TCS"
    assert movers["losers"][0]["change_percent"] == -10.0


def test_get_market_movers_skips_tickers_with_missing_data(monkeypatch):
    _clear_caches()

    frame = pd.DataFrame({("RELIANCE.NS", "Close"): [100.0, 105.0]})
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)

    class _FakeYFModule:
        @staticmethod
        def download(*args, **kwargs):
            return frame

    monkeypatch.setattr(module, "yf", _FakeYFModule())
    monkeypatch.setattr(module, "NIFTY50_CONSTITUENTS", ["RELIANCE", "DELISTEDCO"])

    movers = MarketDataService().get_market_movers(limit=5)
    tickers = {m["ticker"] for m in movers["gainers"] + movers["losers"]}

    assert "DELISTEDCO" not in tickers
    assert "RELIANCE" in tickers


def test_get_all_index_intraday_returns_one_series_per_index(monkeypatch):
    _clear_caches()

    symbols = ["^NSEI", "^BSESN"]
    monkeypatch.setattr(module, "INDEX_SYMBOLS", [("NIFTY 50", "^NSEI"), ("SENSEX", "^BSESN")])

    frame = pd.DataFrame(
        {
            ("^NSEI", "Close"): [24300.0, 24400.0],
            ("^BSESN", "Close"): [78000.0, 78100.0],
        },
        index=pd.to_datetime(["2026-07-31 09:15", "2026-07-31 09:20"]),
    )
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)

    class _FakeYFModule:
        @staticmethod
        def download(*args, **kwargs):
            return frame

    monkeypatch.setattr(module, "yf", _FakeYFModule())

    series = MarketDataService().get_all_index_intraday(limit=30)

    assert set(series.keys()) == set(symbols)
    assert series["^NSEI"][-1]["price"] == 24400.0
    assert series["^BSESN"][-1]["price"] == 78100.0


def test_get_all_index_intraday_degrades_missing_symbol_to_empty_list(monkeypatch):
    _clear_caches()

    monkeypatch.setattr(module, "INDEX_SYMBOLS", [("NIFTY 50", "^NSEI"), ("SENSEX", "^BSESN")])

    frame = pd.DataFrame(
        {("^NSEI", "Close"): [24300.0, 24400.0]},
        index=pd.to_datetime(["2026-07-31 09:15", "2026-07-31 09:20"]),
    )
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)

    class _FakeYFModule:
        @staticmethod
        def download(*args, **kwargs):
            return frame

    monkeypatch.setattr(module, "yf", _FakeYFModule())

    series = MarketDataService().get_all_index_intraday(limit=30)

    assert series["^NSEI"][-1]["price"] == 24400.0
    assert series["^BSESN"] == []


def test_get_index_intraday_returns_recent_closes(monkeypatch):
    _clear_caches()

    history_df = pd.DataFrame(
        {"Close": [100.0, 101.0, 102.0]}, index=pd.to_datetime(["2026-07-31 09:15", "2026-07-31 09:20", "2026-07-31 09:25"])
    )

    class _FakeYFModule:
        @staticmethod
        def Ticker(symbol):
            return _FakeInstrument(history_df=history_df)

    monkeypatch.setattr(module, "yf", _FakeYFModule())

    points = MarketDataService().get_index_intraday("^NSEI", limit=2)

    assert len(points) == 2
    assert points[-1]["price"] == 102.0
