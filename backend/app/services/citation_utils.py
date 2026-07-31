from __future__ import annotations

from app.models.document import SourceDocument
from app.models.stock import StockEntity
from app.schemas.chat import CitationResponse


def build_citation(
    stock: StockEntity,
    document: SourceDocument,
    snippet: str,
    similarity_score: float | None,
) -> CitationResponse:
    """Map a (stock, source document) pair into the API's citation shape.

    Shared by the chat agent's retrieval nodes and the stock-detail endpoint
    so every place that surfaces a source document to the client formats it
    identically.
    """
    return CitationResponse(
        ticker=stock.ticker,
        title=f"{stock.ticker}: {document.title}",
        source_type=document.source_type,
        url=document.url,
        published_at=document.published_at,
        snippet=snippet[:220],
        sentiment_label=document.sentiment_label,
        sentiment_score=float(document.sentiment_score) if document.sentiment_score is not None else None,
        impact_label=document.impact_label,
        event_type=document.event_type,
        similarity_score=round(similarity_score, 3) if similarity_score is not None else None,
    )
