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
    CitationResponse,
    PersonaResponse,
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

        assistant_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            citations_json=json.dumps([citation.model_dump(mode="json") for citation in citations]),
        )
        db.add(assistant_message)
        session.updated_at = func.now()

        db.commit()

        return ChatResponse(
            session_id=session.id,
            answer=answer,
            citations=citations,
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
        session = db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
        ).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        messages = db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        ).scalars().all()
        return [
            ChatMessageResponse(
                role=message.role,
                content=message.content,
                citations=[CitationResponse(**c) for c in json.loads(message.citations_json)]
                if message.citations_json
                else [],
                created_at=message.created_at,
            )
            for message in messages
        ]

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
