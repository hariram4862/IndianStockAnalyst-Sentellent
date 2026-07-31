from app.services import fundamentals_provider as module
from app.services.fundamentals_provider import FundamentalsProvider


class _FakeInstrument:
    def __init__(self, info):
        self.info = info


def _fake_yf(info_by_symbol):
    class _FakeYFModule:
        @staticmethod
        def Ticker(symbol):
            return _FakeInstrument(info_by_symbol.get(symbol, {}))

    return _FakeYFModule()


def test_fetch_returns_none_for_invalid_ticker(monkeypatch):
    module._fundamentals_cache.clear()
    monkeypatch.setattr(module, "yf", _fake_yf({}))

    provider = FundamentalsProvider()
    assert provider.fetch("NOTATICKER") is None


def test_fetch_works_for_any_valid_nse_symbol_not_just_the_original_three(monkeypatch):
    module._fundamentals_cache.clear()
    monkeypatch.setattr(
        module,
        "yf",
        _fake_yf(
            {
                "INFY.NS": {
                    "longName": "Infosys Limited",
                    "sector": "Information Technology",
                    "industry": "IT Services",
                    "marketCap": 5_000_000_000_000,
                    "currentPrice": 1500.0,
                    "trailingPE": 22.0,
                    "dividendYield": 0.025,
                    "debtToEquity": 0.1,
                    "isin": "INE009A01021",
                }
            }
        ),
    )

    provider = FundamentalsProvider()
    payload = provider.fetch("INFY")

    assert payload is not None
    assert payload.company_name == "Infosys Limited"
    assert payload.ticker == "INFY"


def test_fetch_caches_within_ttl_and_does_not_refetch(monkeypatch):
    module._fundamentals_cache.clear()
    call_count = {"n": 0}

    class _CountingYF:
        @staticmethod
        def Ticker(symbol):
            call_count["n"] += 1
            return _FakeInstrument({"longName": "Test Co"})

    monkeypatch.setattr(module, "yf", _CountingYF())

    provider = FundamentalsProvider()
    provider.fetch("TESTCO")
    provider.fetch("TESTCO")

    assert call_count["n"] == 1
