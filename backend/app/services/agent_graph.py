from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk, SourceDocument
from app.models.stock import FollowedStock, StockEntity, UserPersonaMemory
from app.models.user import User
from app.schemas.chat import CitationResponse
from app.services.embedding_service import EmbeddingService
from app.services.gemini_service import GeminiService
from app.services.stock_scoring import RankedStock, from_stock_entity, rank_stocks

RECOMMEND_KEYWORDS = [
    "recommend",
    "what should i buy",
    "what should i invest",
    "suggest a stock",
    "suggest stocks",
    "pick a stock",
    "picks for my profile",
    "buy this week",
    "invest in",
]

RESEARCH_KEYWORDS = [
    "sentiment",
    "fundamental",
    "fundamentals",
    "news",
    "price",
    "dividend",
    "debt",
    "risk",
    "buy",
    "sell",
    "hold",
    "analysis",
    "outlook",
    "earnings",
    "results",
]

GREETING_KEYWORDS = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]

# Ticker-like uppercase tokens, used to notice when a message names a specific
# stock the user doesn't follow (see _extract_unfollowed_ticker_mentions).
TICKER_TOKEN_RE = re.compile(r"\b[A-Z]{2,10}\b")
# Common capitalized finance-context acronyms that are not stock tickers, kept
# out of the unfollowed-ticker check to avoid false-positive refusals.
NON_TICKER_ACRONYMS = {"NSE", "BSE", "INR", "IPO", "GDP", "CEO", "CFO", "USA", "OK", "IT", "AI", "RAG"}

PERSONA_RISK_PROFILES = {"conservative", "aggressive", "moderate"}
PERSONA_INVESTMENT_STYLES = {"dividend-focused", "growth-oriented", "value-focused", "momentum-focused"}

MIN_VECTOR_SIMILARITY = 0.25
MAX_CITATIONS = 3
MAX_RECOMMEND_PICKS = 5
MAX_PERSONA_SUMMARY_LENGTH = 800


class AgentState(TypedDict, total=False):
    message: str
    intent: str  # "recommend" | "research" | "chitchat"
    stock_mentions: list[str]
    unfollowed_ticker_mentions: list[str]
    persona_summary: str | None
    risk_profile: str | None
    investment_style: str | None
    constraints_text: str | None
    ranked_stocks: list[RankedStock]
    citations: list[CitationResponse]
    answer: str


class AgentGraph:
    """LangGraph-based agent brain: extract intent/tickers -> update investor
    persona memory -> (recommend: rank stocks first) -> retrieve grounded
    sources -> generate a cited answer, refusing to answer ungrounded claims.
    """

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.embedding_service = EmbeddingService()
        self.gemini_service = GeminiService()
        self._graph = self._build_graph()

    def run(self, message: str) -> AgentState:
        return self._graph.invoke({"message": message})

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("extract_intent_and_tickers", self._extract_intent_and_tickers)
        graph.add_node("update_persona", self._update_persona)
        graph.add_node("rank_stocks", self._rank_stocks)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("generate_answer", self._generate_answer)

        graph.set_entry_point("extract_intent_and_tickers")
        graph.add_edge("extract_intent_and_tickers", "update_persona")
        graph.add_conditional_edges(
            "update_persona",
            lambda state: "rank_stocks" if state["intent"] == "recommend" else "retrieve",
            {"rank_stocks": "rank_stocks", "retrieve": "retrieve"},
        )
        graph.add_edge("rank_stocks", "retrieve")
        graph.add_edge("retrieve", "generate_answer")
        graph.add_edge("generate_answer", END)
        return graph.compile()

    # --- Node 1: intent + ticker extraction -------------------------------

    def _extract_intent_and_tickers(self, state: AgentState) -> AgentState:
        message = state["message"]
        followed_tickers = self._followed_tickers()
        return {
            "stock_mentions": _extract_ticker_mentions(message, followed_tickers),
            "unfollowed_ticker_mentions": _extract_unfollowed_ticker_mentions(message, followed_tickers),
            "intent": _classify_intent(message),
        }

    def _followed_tickers(self) -> list[str]:
        rows = self.db.execute(
            select(StockEntity.ticker)
            .join(FollowedStock, FollowedStock.stock_id == StockEntity.id)
            .where(FollowedStock.user_id == self.user.id, FollowedStock.is_active.is_(True))
        ).all()
        return [row[0] for row in rows]

    # --- Node 2: persona memory --------------------------------------------

    def _update_persona(self, state: AgentState) -> AgentState:
        persona = self._fetch_persona()
        message = state["message"]

        extracted = (
            self._extract_persona_via_llm(message)
            if self.gemini_service.is_enabled()
            else _extract_persona_via_keywords(message)
        )
        has_signal = any(extracted.get(key) for key in ("risk_profile", "investment_style", "constraint", "summary_delta"))

        if has_signal:
            if persona is None:
                persona = UserPersonaMemory(user_id=self.user.id, summary="")
                self.db.add(persona)
                self.db.flush()

            if extracted.get("risk_profile"):
                persona.risk_profile = extracted["risk_profile"]
            if extracted.get("investment_style"):
                persona.investment_style = extracted["investment_style"]
            if extracted.get("constraint"):
                persona.constraints_text = _merge_text(persona.constraints_text, extracted["constraint"])
            if extracted.get("summary_delta"):
                persona.summary = _merge_text(
                    persona.summary, extracted["summary_delta"], max_length=MAX_PERSONA_SUMMARY_LENGTH
                )

        return {
            "persona_summary": persona.summary if persona else None,
            "risk_profile": persona.risk_profile if persona else None,
            "investment_style": persona.investment_style if persona else None,
            "constraints_text": persona.constraints_text if persona else None,
        }

    def _fetch_persona(self) -> UserPersonaMemory | None:
        return self.db.execute(
            select(UserPersonaMemory).where(UserPersonaMemory.user_id == self.user.id)
        ).scalar_one_or_none()

    def _extract_persona_via_llm(self, message: str) -> dict[str, str | None]:
        system_prompt = (
            "Extract investor-persona facts from a single chat message for a stock-research app. "
            "Return only JSON with keys risk_profile, investment_style, constraint, summary_delta. "
            "risk_profile must be one of conservative, aggressive, moderate, or null if not stated. "
            "investment_style must be one of dividend-focused, growth-oriented, value-focused, "
            "momentum-focused, or null. "
            "constraint is a short free-text investing rule/exclusion the user stated "
            "(e.g. 'avoid high-debt companies'), or null. "
            "summary_delta is a short one-sentence factual note capturing what this message reveals "
            "about the investor, or null if it reveals nothing new. "
            "Never guess — use null for anything not clearly stated in the message."
        )
        result = self.gemini_service.chat_json(system_prompt, message)
        if not result:
            return _extract_persona_via_keywords(message)

        risk_profile = _clean_enum(result.get("risk_profile"), PERSONA_RISK_PROFILES)
        investment_style = _clean_enum(result.get("investment_style"), PERSONA_INVESTMENT_STYLES)
        constraint = _clean_str(result.get("constraint"))
        summary_delta = _clean_str(result.get("summary_delta"))

        if not any([risk_profile, investment_style, constraint, summary_delta]):
            return _extract_persona_via_keywords(message)

        return {
            "risk_profile": risk_profile,
            "investment_style": investment_style,
            "constraint": constraint,
            "summary_delta": summary_delta,
        }

    # --- Node 3: persona-based ranking (recommend intent only) -------------

    def _rank_stocks(self, state: AgentState) -> AgentState:
        followed = self.db.execute(
            select(StockEntity)
            .join(FollowedStock, FollowedStock.stock_id == StockEntity.id)
            .where(FollowedStock.user_id == self.user.id, FollowedStock.is_active.is_(True))
        ).scalars().all()

        ranked = rank_stocks(
            [from_stock_entity(stock) for stock in followed],
            risk_profile=state.get("risk_profile"),
            investment_style=state.get("investment_style"),
            constraints_text=state.get("constraints_text"),
        )
        return {"ranked_stocks": ranked}

    # --- Node 4: retrieval ---------------------------------------------------

    def _retrieve(self, state: AgentState) -> AgentState:
        if state["intent"] == "chitchat":
            return {"citations": []}

        ranked = state.get("ranked_stocks") or []
        target_tickers = [pick.ticker for pick in ranked[:MAX_RECOMMEND_PICKS]] if ranked else state.get(
            "stock_mentions", []
        )

        if not target_tickers and not _looks_research_related(state["message"]):
            return {"citations": []}

        # The message names a specific ticker the user doesn't follow (e.g. "INFY"
        # when only RELIANCE is followed): refuse rather than silently substituting
        # a different followed stock's data, which the generic fallback below would
        # otherwise do (it has no concept of "the wrong stock").
        if not target_tickers and state.get("unfollowed_ticker_mentions"):
            return {"citations": []}

        citations = self._retrieve_vector_ranked_citations(state["message"], target_tickers)
        if not citations:
            citations = self._retrieve_fallback_citations(state["message"], target_tickers)
        return {"citations": citations}

    def _followed_stock_ids_subquery(self):
        return select(FollowedStock.stock_id).where(
            FollowedStock.user_id == self.user.id,
            FollowedStock.is_active.is_(True),
        )

    def _retrieve_vector_ranked_citations(self, message: str, target_tickers: list[str]) -> list[CitationResponse]:
        query_embedding = self.embedding_service.embed_text(message)
        distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(DocumentChunk, SourceDocument, StockEntity, distance_expr.label("distance"))
            .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
            .join(StockEntity, StockEntity.id == SourceDocument.stock_id)
            .where(
                and_(
                    SourceDocument.stock_id.in_(self._followed_stock_ids_subquery()),
                    DocumentChunk.embedding.is_not(None),
                )
            )
            .order_by(distance_expr.asc(), SourceDocument.published_at.desc().nullslast())
        )
        if target_tickers:
            stmt = stmt.where(StockEntity.ticker.in_(target_tickers))

        try:
            rows = self.db.execute(stmt.limit(5)).all()
        except Exception:
            return []

        citations: list[CitationResponse] = []
        seen_documents: set[int] = set()
        for chunk, document, stock, distance in rows:
            if document.id in seen_documents:
                continue
            seen_documents.add(document.id)
            similarity_score = max(0.0, min(1.0, 1 - float(distance)))
            if similarity_score < MIN_VECTOR_SIMILARITY and not target_tickers:
                continue
            citations.append(_to_citation(stock, document, chunk.content, similarity_score))
            if len(citations) == MAX_CITATIONS:
                break
        return citations

    def _retrieve_fallback_citations(self, message: str, target_tickers: list[str]) -> list[CitationResponse]:
        stmt = (
            select(SourceDocument, StockEntity)
            .join(StockEntity, StockEntity.id == SourceDocument.stock_id)
            .where(SourceDocument.stock_id.in_(self._followed_stock_ids_subquery()))
            .order_by(SourceDocument.published_at.desc().nullslast(), SourceDocument.created_at.desc())
        )
        if target_tickers:
            stmt = stmt.where(StockEntity.ticker.in_(target_tickers))
        else:
            stmt = stmt.where(
                (SourceDocument.content.ilike(f"%{message.strip()}%"))
                | (SourceDocument.title.ilike(f"%{message.strip()}%"))
            )

        rows = self.db.execute(stmt.limit(MAX_CITATIONS)).all()
        citations = [_to_citation(stock, document, document.content[:220], None) for document, stock in rows]
        if citations or target_tickers:
            return citations

        # Last resort: most recent items across followed stocks regardless of match.
        rows = self.db.execute(
            select(SourceDocument, StockEntity)
            .join(StockEntity, StockEntity.id == SourceDocument.stock_id)
            .where(SourceDocument.stock_id.in_(self._followed_stock_ids_subquery()))
            .order_by(SourceDocument.published_at.desc().nullslast(), SourceDocument.created_at.desc())
            .limit(MAX_CITATIONS)
        ).all()
        return [_to_citation(stock, document, document.content[:220], None) for document, stock in rows]

    # --- Node 5: answer generation (anti-hallucination guard) --------------

    def _generate_answer(self, state: AgentState) -> AgentState:
        intent = state["intent"]

        if intent == "chitchat":
            return {
                "answer": (
                    'Hi! Ask me about a stock you follow (e.g. its sentiment or fundamentals), or say '
                    '"recommend stocks for my profile" once you\'re following a few.'
                )
            }

        if intent == "recommend":
            ranked = state.get("ranked_stocks") or []
            if not ranked:
                return {"answer": "You are not following any stocks yet, so I have nothing to rank. Follow a ticker first."}
            return {"answer": self._build_recommend_answer(state)}

        # intent == "research": never call the LLM without grounded sources.
        citations = state.get("citations", [])
        if not citations:
            return {
                "answer": (
                    "I do not have that in the ingested data yet. Follow a supported ticker first so I can "
                    "ground the answer with stored fundamentals and news."
                )
            }
        return {"answer": self._build_research_answer(state)}

    def _build_recommend_answer(self, state: AgentState) -> str:
        ranked: list[RankedStock] = state["ranked_stocks"][:MAX_RECOMMEND_PICKS]
        citations = state.get("citations", [])

        lines = ["Ranked picks from your followed stocks, matched to your investor profile:"]
        for pick in ranked:
            lines.append(f"- {pick.ticker} ({pick.company_name}): score {pick.composite_score:.2f}. {pick.reason}")
        if citations:
            lines.append("Supporting sources:")
            for index, citation in enumerate(citations, start=1):
                lines.append(f"[{index}] {citation.title} ({citation.source_type}).")
        if state.get("persona_summary"):
            lines.append(f"Investor memory applied: {state['persona_summary']}")
        fallback_text = "\n".join(lines)

        if not self.gemini_service.is_enabled():
            return fallback_text

        system_prompt = (
            "You are a grounded Indian stock research assistant writing a short recommendation summary. "
            "Only reference the ranked picks and sources given below — never invent a ticker, number, or "
            "source that isn't listed. All figures must be in INR (Rs.) where relevant. Cite sources as "
            "[1], [2] matching the given list. Keep it concise: one line per pick plus a short closing note."
        )
        user_prompt = json.dumps(
            {
                "persona_summary": state.get("persona_summary"),
                "ranked_picks": [asdict(pick) for pick in ranked],
                "sources": [_citation_to_prompt_dict(index, citation) for index, citation in enumerate(citations, start=1)],
            }
        )
        return self.gemini_service.chat_text(system_prompt, user_prompt) or fallback_text

    def _build_research_answer(self, state: AgentState) -> str:
        citations = state["citations"]
        llm_answer = self._build_research_answer_with_gemini(state)
        if llm_answer:
            return llm_answer

        stock_mentions = state.get("stock_mentions", [])
        lines = [f"Grounded read for {', '.join(stock_mentions)}:" if stock_mentions else "Grounded read from your followed-stock corpus:"]
        for citation in citations:
            prefix = "Fundamentals" if citation.source_type == "fundamentals" else "News"
            metadata_parts = []
            if citation.sentiment_label:
                metadata_parts.append(f"sentiment {citation.sentiment_label}")
            if citation.impact_label:
                metadata_parts.append(f"impact {citation.impact_label}")
            if citation.event_type:
                metadata_parts.append(f"event {citation.event_type}")
            if citation.similarity_score is not None:
                metadata_parts.append(f"relevance {citation.similarity_score:.2f}")
            metadata_suffix = f" ({', '.join(metadata_parts)})" if metadata_parts else ""
            lines.append(f"{prefix}: {citation.title}{metadata_suffix}. Evidence: {citation.snippet}")

        if state.get("persona_summary"):
            lines.append(f"Investor memory applied: {state['persona_summary']}")
        lines.append(
            "I have only used the ingested corpus above. If you need a fresher or broader answer, I should "
            "refresh the stock data first."
        )
        return "\n".join(lines)

    def _build_research_answer_with_gemini(self, state: AgentState) -> str | None:
        if not self.gemini_service.is_enabled():
            return None

        citations = state["citations"]
        sources = [_citation_to_prompt_dict(index, citation) for index, citation in enumerate(citations, start=1)]

        system_prompt = (
            "You are a grounded Indian stock research assistant. Answer only from the provided sources. "
            "If the sources do not contain enough information, say so plainly. Keep the answer concise, in "
            "INR where values are mentioned, and reference source ids like [1], [2]. Do not invent numbers "
            "or unsupported claims."
        )
        user_prompt = json.dumps(
            {
                "question": state["message"],
                "persona_summary": state.get("persona_summary"),
                "sources": sources,
            }
        )
        return self.gemini_service.chat_text(system_prompt, user_prompt)


# --- Module-level pure helpers (kept free of DB/LLM access for testability) ---


def _classify_intent(message: str) -> str:
    lowered = message.lower().strip()
    if not lowered or lowered in GREETING_KEYWORDS:
        return "chitchat"
    if any(keyword in lowered for keyword in RECOMMEND_KEYWORDS):
        return "recommend"
    if any(keyword in lowered for keyword in RESEARCH_KEYWORDS):
        return "research"
    return "chitchat"


def _looks_research_related(message: str) -> bool:
    lowered = message.lower().strip()
    return bool(lowered) and lowered not in GREETING_KEYWORDS and any(k in lowered for k in RESEARCH_KEYWORDS)


def _extract_ticker_mentions(message: str, followed_tickers: list[str]) -> list[str]:
    uppercase_message = message.upper()
    return [ticker for ticker in followed_tickers if ticker in uppercase_message]


def _extract_unfollowed_ticker_mentions(message: str, followed_tickers: list[str]) -> list[str]:
    """Ticker-like uppercase tokens in the message that aren't in the user's
    followed set — a signal that the user asked about a specific stock we
    have no ingested data for, so the answer must refuse rather than
    substitute a different followed stock's data."""
    followed_set = set(followed_tickers)
    candidates = TICKER_TOKEN_RE.findall(message)
    return [
        token
        for token in dict.fromkeys(candidates)
        if token not in followed_set and token not in NON_TICKER_ACRONYMS
    ]


def _extract_persona_via_keywords(message: str) -> dict[str, str | None]:
    lowered = message.lower()
    result: dict[str, str | None] = {
        "risk_profile": None,
        "investment_style": None,
        "constraint": None,
        "summary_delta": None,
    }
    notes = []

    if "conservative" in lowered:
        result["risk_profile"] = "conservative"
        notes.append("Investor prefers conservative risk.")
    if "aggressive" in lowered:
        result["risk_profile"] = "aggressive"
        notes.append("Investor accepts aggressive risk.")
    if "dividend" in lowered:
        result["investment_style"] = "dividend-focused"
        notes.append("Investor prefers dividend-focused ideas.")
    if "growth" in lowered:
        result["investment_style"] = "growth-oriented"
        notes.append("Investor values growth.")
    if "avoid" in lowered:
        result["constraint"] = message.strip()
        notes.append(f"Constraint captured: {message.strip()}")

    if notes:
        result["summary_delta"] = " ".join(notes)
    return result


def _merge_text(existing: str | None, new_fact: str, max_length: int = 800) -> str:
    if not existing:
        return new_fact
    if new_fact.lower() in existing.lower():
        return existing
    merged = f"{existing} {new_fact}".strip()
    if len(merged) <= max_length:
        return merged
    return merged[-max_length:]


def _clean_enum(value: object, allowed: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned if cleaned in allowed else None


def _clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _to_citation(
    stock: StockEntity,
    document: SourceDocument,
    snippet: str,
    similarity_score: float | None,
) -> CitationResponse:
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


def _citation_to_prompt_dict(index: int, citation: CitationResponse) -> dict[str, object]:
    return {
        "id": index,
        "ticker": citation.ticker,
        "title": citation.title,
        "source_type": citation.source_type,
        "published_at": citation.published_at.isoformat() if citation.published_at else None,
        "sentiment_label": citation.sentiment_label,
        "sentiment_score": citation.sentiment_score,
        "impact_label": citation.impact_label,
        "event_type": citation.event_type,
        "similarity_score": citation.similarity_score,
        "snippet": citation.snippet,
    }
