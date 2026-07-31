from __future__ import annotations

import json

from app.services.gemini_service import GeminiService
from app.services.providers import NewsArticlePayload


POSITIVE_KEYWORDS = ["growth", "strong", "stable", "positive", "gain", "beat", "improve", "resilient"]
NEGATIVE_KEYWORDS = ["debt", "fall", "weak", "negative", "miss", "risk", "downgrade", "decline"]
HIGH_IMPACT_KEYWORDS = ["results", "earnings", "merger", "acquisition", "debt", "guidance", "regulation"]


class ArticleAnalysisService:
    def __init__(self) -> None:
        self.gemini_service = GeminiService()

    def analyze(self, ticker: str, article: NewsArticlePayload) -> dict[str, object]:
        if self.gemini_service.is_enabled():
            analysis = self._analyze_with_gemini(ticker, article)
            if analysis is not None:
                return analysis

        text = f"{article.title} {article.content}".lower()
        positive_hits = sum(keyword in text for keyword in POSITIVE_KEYWORDS)
        negative_hits = sum(keyword in text for keyword in NEGATIVE_KEYWORDS)
        score = max(-1.0, min(1.0, (positive_hits - negative_hits) / 3))

        if score > 0.15:
            sentiment_label = "positive"
        elif score < -0.15:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        impact_hits = sum(keyword in text for keyword in HIGH_IMPACT_KEYWORDS)
        impact_label = "high" if impact_hits >= 2 else "medium" if impact_hits == 1 else "low"
        event_type = self._infer_event_type(text)

        return {
            "sentiment_label": sentiment_label,
            "sentiment_score": round(score, 2),
            "impact_label": impact_label,
            "event_type": event_type,
            "mentioned_tickers": ticker,
            "metadata_json": json.dumps(
                {
                    "positive_hits": positive_hits,
                    "negative_hits": negative_hits,
                    "impact_hits": impact_hits,
                }
            ),
        }

    def _analyze_with_gemini(self, ticker: str, article: NewsArticlePayload) -> dict[str, object] | None:
        system_prompt = (
            "You tag Indian stock news for a retrieval system. "
            "Return only valid JSON with keys sentiment_label, sentiment_score, impact_label, event_type, "
            "mentioned_tickers, metadata_json. "
            "sentiment_label must be one of positive, neutral, negative. "
            "impact_label must be one of low, medium, high. "
            "event_type should be a short slug like earnings, guidance, regulation, balance-sheet, business-update, general. "
            "mentioned_tickers must be an array of NSE/BSE tickers or an empty array. "
            "sentiment_score must be a number from -1 to 1."
        )
        user_prompt = json.dumps(
            {
                "ticker": ticker,
                "title": article.title,
                "content": article.content,
                "source_name": article.source_name,
            }
        )
        result = self.gemini_service.chat_json(system_prompt, user_prompt)
        if not result:
            return None

        sentiment_label = str(result.get("sentiment_label") or "neutral").lower()
        if sentiment_label not in {"positive", "neutral", "negative"}:
            sentiment_label = "neutral"

        impact_label = str(result.get("impact_label") or "low").lower()
        if impact_label not in {"low", "medium", "high"}:
            impact_label = "low"

        event_type = str(result.get("event_type") or "general").lower()
        mentioned_tickers = result.get("mentioned_tickers") or [ticker]
        if isinstance(mentioned_tickers, list):
            mentioned_tickers = ",".join(
                str(item).strip().upper() for item in mentioned_tickers if str(item).strip()
            )
        elif not isinstance(mentioned_tickers, str):
            mentioned_tickers = ticker

        try:
            sentiment_score = float(result.get("sentiment_score"))
        except (TypeError, ValueError):
            sentiment_score = 0.0

        metadata_json = result.get("metadata_json")
        if not isinstance(metadata_json, str):
            metadata_json = json.dumps(result)

        return {
            "sentiment_label": sentiment_label,
            "sentiment_score": max(-1.0, min(1.0, sentiment_score)),
            "impact_label": impact_label,
            "event_type": event_type,
            "mentioned_tickers": mentioned_tickers,
            "metadata_json": metadata_json,
        }

    def _infer_event_type(self, text: str) -> str:
        if "earnings" in text or "results" in text or "quarter" in text:
            return "earnings"
        if "debt" in text or "borrowing" in text:
            return "balance-sheet"
        if "guidance" in text or "outlook" in text:
            return "guidance"
        if "regulation" in text or "approval" in text:
            return "regulatory"
        if "deal" in text or "order" in text or "contract" in text:
            return "business-update"
        return "general"
