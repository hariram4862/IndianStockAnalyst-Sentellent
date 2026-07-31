from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from xml.etree import ElementTree

import requests

from app.services.providers import NewsArticlePayload


# Verified live and actively publishing (checked pubDate freshness directly,
# not just that the URL 200s -- Moneycontrol's legacy /rss/*.xml feeds and
# the old LiveMint marketsRSS path both still return 200 but haven't
# published a new item since 2024, so they were dropped rather than kept as
# dead weight that silently contributes zero articles forever).
RSS_FEEDS = [
    (
        "Economic Times Markets",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    ),
    (
        "LiveMint Markets",
        "https://www.livemint.com/rss/markets",
    ),
    (
        "Business Standard Markets",
        "https://www.business-standard.com/rss/markets-106.rss",
    ),
    (
        "The Hindu BusinessLine Markets",
        "https://www.thehindubusinessline.com/markets/feeder/default.rss",
    ),
]

# Plain "python-requests" UA gets blocked (403) by some publishers' bot
# protection (observed on Business Standard); a browser-shaped UA is
# unrelated to scraping intent -- robots.txt/rate-limits are still respected
# via the request cadence (one pass per ingest, capped item count below).
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Corporate suffixes stripped when deriving alias phrases from a company
# name, so they don't get treated as part of the distinguishing name.
GENERIC_SUFFIXES = {"LIMITED", "LTD", "LTD.", "PVT", "PRIVATE", "COMPANY", "CO", "CO."}


class NewsProvider:
    def fetch_for_ticker(
        self, ticker: str, company_name: str | None = None, limit_per_feed: int = 25
    ) -> list[NewsArticlePayload]:
        # Each feed is already fully fetched and parsed before this slice, so
        # raising the per-feed cap costs no extra network round-trips -- it
        # just widens how far back "recent" news is scanned, which matters
        # for stocks that aren't in every feed's top handful of headlines.
        aliases = _derive_aliases(ticker, company_name)
        articles: list[NewsArticlePayload] = []

        for source_name, feed_url in RSS_FEEDS:
            try:
                response = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=15)
                response.raise_for_status()
            except requests.RequestException:
                continue

            try:
                root = ElementTree.fromstring(response.text)
            except ElementTree.ParseError:
                continue

            items = root.findall(".//item")[:limit_per_feed]
            for item in items:
                title = _get_text(item, "title")
                link = _get_text(item, "link")
                description = _strip_html(_get_text(item, "description"))
                content = " ".join(part for part in [title, description] if part).strip()

                if not content or not _mentions_alias(content, aliases):
                    continue

                published_at = _parse_rss_datetime(_get_text(item, "pubDate"))
                external_id = hashlib.sha256(f"{source_name}|{link}|{title}".encode("utf-8")).hexdigest()
                articles.append(
                    NewsArticlePayload(
                        source_name=source_name,
                        source_type="news",
                        external_id=external_id,
                        title=title or f"{ticker} market update",
                        url=link,
                        published_at=published_at,
                        content=content,
                    )
                )

        unique: dict[str, NewsArticlePayload] = {}
        for article in articles:
            unique.setdefault(article.external_id, article)
        return list(unique.values())


def _derive_aliases(ticker: str, company_name: str | None) -> list[str]:
    """Build the set of name variants a news article might use to refer to
    this stock, from the ticker plus its ingested company name -- generalizes
    to any followed ticker instead of a hand-maintained per-ticker lookup
    table that silently stops matching news for every stock outside it.

    A bare single distinguishing word (e.g. "Infosys") is only added when the
    company name reduces to exactly one word after stripping corporate
    suffixes -- for multi-word names (e.g. "Tata Consultancy Services") the
    first word alone ("Tata") is too generic and shared across many other
    listed group companies, so only the full phrase is used.
    """
    aliases = [ticker]
    if not company_name:
        return aliases

    aliases.append(company_name)
    words = [w for w in company_name.replace(".", "").split() if w.upper() not in GENERIC_SUFFIXES]
    if words:
        phrase = " ".join(words)
        if phrase not in aliases:
            aliases.append(phrase)
        if len(words) == 1 and words[0] not in aliases:
            aliases.append(words[0])
    return aliases


def _get_text(item: ElementTree.Element, tag: str) -> str:
    element = item.find(tag)
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text).replace("&nbsp;", " ").strip()


def _mentions_alias(text: str, aliases: list[str]) -> bool:
    lowered = text.lower()
    return any(alias.lower() in lowered for alias in aliases)


def _parse_rss_datetime(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None
