from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.stock import UserPersonaMemory
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionSummary,
    ChatSessionUpdate,
    CitationResponse,
    PersonaResponse,
    RankedStockResponse,
)
from app.services.agent_graph import AgentGraph

MAX_AUTO_TITLE_LENGTH = 60


class ResearchService:
    """Thin adapter between the HTTP layer and the LangGraph agent brain
    (app.services.agent_graph.AgentGraph) — persists the chat transcript and
    maps the graph's result onto the API's response contract, which is
    unchanged from before the LangGraph migration.
    """

    def chat(self, db: Session, user: User, payload: ChatRequest) -> ChatResponse:
        session = self._get_or_create_session(db, user.id, payload.session_id, payload.message)
        user_message = ChatMessage(session_id=session.id, role="user", content=payload.message)
        db.add(user_message)
        db.flush()

        result = AgentGraph(db, user).run(payload.message)
        answer = result["answer"]
        citations = result.get("citations", [])
        intent = result.get("intent", "chitchat")
        ranked_stocks = [_ranked_stock_response(pick) for pick in result.get("ranked_stocks") or []]

        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            citations_json=json.dumps(_encode_message_envelope(citations, intent, ranked_stocks)),
        )
        db.add(assistant_message)
        session.updated_at = func.now()

        db.commit()

        return ChatResponse(
            session_id=session.id,
            answer=answer,
            citations=citations,
            intent=intent,
            ranked_stocks=ranked_stocks,
            persona_summary=result.get("persona_summary"),
        )

    def list_sessions(self, db: Session, user: User) -> list[ChatSessionSummary]:
        sessions = db.execute(
            select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc())
        ).scalars().all()
        return [
            ChatSessionSummary(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
            for session in sessions
        ]

    def get_session_messages(self, db: Session, user: User, session_id: int) -> list[ChatMessageResponse]:
        session = self._get_owned_session(db, user.id, session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        messages = db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        ).scalars().all()
        result = []
        for message in messages:
            citations, intent, ranked_stocks = _decode_message_envelope(message.citations_json)
            result.append(
                ChatMessageResponse(
                    role=message.role,
                    content=message.content,
                    citations=citations,
                    intent=intent,
                    ranked_stocks=ranked_stocks,
                    created_at=message.created_at,
                )
            )
        return result

    def rename_session(self, db: Session, user: User, session_id: int, payload: ChatSessionUpdate) -> ChatSessionSummary:
        session = self._get_owned_session(db, user.id, session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.title = payload.title.strip()[:MAX_AUTO_TITLE_LENGTH] or session.title
        db.commit()
        db.refresh(session)
        return ChatSessionSummary(
            id=session.id, title=session.title, created_at=session.created_at, updated_at=session.updated_at
        )

    def delete_session(self, db: Session, user: User, session_id: int) -> None:
        session = self._get_owned_session(db, user.id, session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        db.delete(session)
        db.commit()

    def _get_owned_session(self, db: Session, user_id: int, session_id: int) -> ChatSession | None:
        return db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        ).scalar_one_or_none()

    def reset_persona(self, db: Session, user: User) -> PersonaResponse:
        persona = db.execute(
            select(UserPersonaMemory).where(UserPersonaMemory.user_id == user.id)
        ).scalar_one_or_none()
        if persona is not None:
            db.delete(persona)
            db.commit()
        return PersonaResponse(
            summary=None, risk_profile=None, investment_style=None, constraints_text=None, updated_at=None
        )

    def get_persona(self, db: Session, user: User) -> PersonaResponse:
        persona = db.execute(
            select(UserPersonaMemory).where(UserPersonaMemory.user_id == user.id)
        ).scalar_one_or_none()
        if persona is None:
            return PersonaResponse(
                summary=None, risk_profile=None, investment_style=None, constraints_text=None, updated_at=None
            )
        return PersonaResponse(
            summary=persona.summary or None,
            risk_profile=persona.risk_profile,
            investment_style=persona.investment_style,
            constraints_text=persona.constraints_text,
            updated_at=persona.updated_at,
        )

    def _get_or_create_session(
        self, db: Session, user_id: int, session_id: int | None, first_message: str
    ) -> ChatSession:
        if session_id is not None:
            session = db.execute(
                select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            ).scalar_one_or_none()
            if session is not None:
                return session

        title = first_message.strip()[:MAX_AUTO_TITLE_LENGTH] or "New Research Session"
        session = ChatSession(user_id=user_id, title=title)
        db.add(session)
        db.flush()
        return session


def _ranked_stock_response(pick) -> RankedStockResponse:
    return RankedStockResponse(
        ticker=pick.ticker,
        company_name=pick.company_name,
        composite_score=pick.composite_score,
        value_score=pick.value_score,
        stability_score=pick.stability_score,
        momentum_score=pick.momentum_score,
        reason=pick.reason,
    )


def _encode_message_envelope(
    citations: list[CitationResponse], intent: str, ranked_stocks: list[RankedStockResponse]
) -> dict:
    """Pack citations + intent + ranked_stocks into the single JSON blob stored in
    ChatMessage.citations_json, so replaying session history can still render
    recommendation cards without a schema migration for new columns."""
    return {
        "citations": [citation.model_dump(mode="json") for citation in citations],
        "intent": intent,
        "ranked_stocks": [pick.model_dump(mode="json") for pick in ranked_stocks],
    }


def _decode_message_envelope(
    citations_json: str | None,
) -> tuple[list[CitationResponse], str | None, list[RankedStockResponse]]:
    if not citations_json:
        return [], None, []

    raw = json.loads(citations_json)
    if isinstance(raw, list):
        # Pre-envelope rows: citations_json was just a bare list of citations.
        return [CitationResponse(**c) for c in raw], None, []

    citations = [CitationResponse(**c) for c in raw.get("citations", [])]
    ranked_stocks = [RankedStockResponse(**p) for p in raw.get("ranked_stocks", [])]
    return citations, raw.get("intent"), ranked_stocks
