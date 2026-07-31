from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from xml.etree import ElementTree

import requests

from app.services.providers import NewsArticlePayload


RSS_FEEDS = [
    (
        "Economic Times Markets",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    ),
    (
        "LiveMint Markets",
        "https://www.livemint.com/rss/marketsRSS",
    ),
    (
        "Business Standard Markets",
        "https://www.business-standard.com/rss/markets-106.rss",
    ),
]

TICKER_ALIASES = {
    "RELIANCE": ["Reliance", "Reliance Industries"],
    "TCS": ["TCS", "Tata Consultancy Services"],
    "HDFCBANK": ["HDFC Bank", "HDFCBANK"],
}


class NewsProvider:
    def fetch_for_ticker(self, ticker: str, limit_per_feed: int = 8) -> list[NewsArticlePayload]:
        aliases = TICKER_ALIASES.get(ticker, [ticker])
        articles: list[NewsArticlePayload] = []

        for source_name, feed_url in RSS_FEEDS:
            try:
                response = requests.get(feed_url, timeout=15)
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
