from datetime import datetime, timezone

from app.services import news_provider as module
from app.services.news_provider import NewsProvider

FEED_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
{items}
</channel></rss>
"""

ITEM_TEMPLATE = """
<item>
  <title>{title}</title>
  <link>{link}</link>
  <pubDate>{pub_date}</pubDate>
</item>
"""


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        pass


def _feed_bytes(items: list[tuple[str, str, str]]) -> bytes:
    items_xml = "".join(
        ITEM_TEMPLATE.format(title=title, link=link, pub_date=pub_date) for title, link, pub_date in items
    )
    return FEED_TEMPLATE.format(items=items_xml).encode("utf-8")


def test_fetch_market_headlines_has_no_ticker_filtering_and_dedups_by_link(monkeypatch):
    module._market_headlines_cache = None

    responses = {
        module.RSS_FEEDS[0][1]: _feed_bytes(
            [
                ("Unrelated market wrap", "https://example.com/a", "Fri, 31 Jul 2026 10:00:00 +0530"),
                ("Duplicate across feeds", "https://example.com/dup", "Fri, 31 Jul 2026 09:00:00 +0530"),
            ]
        ),
        module.RSS_FEEDS[1][1]: _feed_bytes(
            [("Duplicate across feeds", "https://example.com/dup", "Fri, 31 Jul 2026 09:00:00 +0530")]
        ),
    }

    def _fake_get(url, headers=None, timeout=None):
        return _FakeResponse(responses.get(url, _feed_bytes([])))

    monkeypatch.setattr(module.requests, "get", _fake_get)

    headlines = NewsProvider().fetch_market_headlines(limit=10)
    links = [h["url"] for h in headlines]

    assert links.count("https://example.com/dup") == 1
    assert "https://example.com/a" in links
    # No ticker/company filtering -- an entirely generic headline still appears.
    assert any(h["title"] == "Unrelated market wrap" for h in headlines)


def test_fetch_market_headlines_sorted_by_recency(monkeypatch):
    module._market_headlines_cache = None

    responses = {
        module.RSS_FEEDS[0][1]: _feed_bytes(
            [
                ("Older", "https://example.com/old", "Fri, 31 Jul 2026 08:00:00 +0530"),
                ("Newer", "https://example.com/new", "Fri, 31 Jul 2026 12:00:00 +0530"),
            ]
        ),
    }

    def _fake_get(url, headers=None, timeout=None):
        return _FakeResponse(responses.get(url, _feed_bytes([])))

    monkeypatch.setattr(module.requests, "get", _fake_get)

    headlines = NewsProvider().fetch_market_headlines(limit=10)

    assert headlines[0]["title"] == "Newer"
    assert headlines[1]["title"] == "Older"


def test_fetch_market_headlines_caches_within_ttl(monkeypatch):
    module._market_headlines_cache = None
    call_count = {"n": 0}

    def _fake_get(url, headers=None, timeout=None):
        call_count["n"] += 1
        return _FakeResponse(_feed_bytes([("Title", "https://example.com/x", "Fri, 31 Jul 2026 08:00:00 +0530")]))

    monkeypatch.setattr(module.requests, "get", _fake_get)

    provider = NewsProvider()
    provider.fetch_market_headlines()
    provider.fetch_market_headlines()

    assert call_count["n"] == len(module.RSS_FEEDS)  # one pass only, not two
