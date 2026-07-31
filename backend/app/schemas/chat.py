from datetime import datetime

from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    ticker: str
    title: str
    source_type: str
    url: str | None
    published_at: datetime | None
    snippet: str
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    impact_label: str | None = None
    event_type: str | None = None
    similarity_score: float | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    citations: list[CitationResponse]
    persona_summary: str | None = None
