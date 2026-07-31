from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_graph import AgentGraph


class ResearchService:
    """Thin adapter between the HTTP layer and the LangGraph agent brain
    (app.services.agent_graph.AgentGraph) — persists the chat transcript and
    maps the graph's result onto the API's response contract, which is
    unchanged from before the LangGraph migration.
    """

    def chat(self, db: Session, user: User, payload: ChatRequest) -> ChatResponse:
        session = self._get_or_create_session(db, user.id, payload.session_id)
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

        db.commit()

        return ChatResponse(
            session_id=session.id,
            answer=answer,
            citations=citations,
            persona_summary=result.get("persona_summary"),
        )

    def _get_or_create_session(self, db: Session, user_id: int, session_id: int | None) -> ChatSession:
        if session_id is not None:
            session = db.execute(
                select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            ).scalar_one_or_none()
            if session is not None:
                return session

        session = ChatSession(user_id=user_id)
        db.add(session)
        db.flush()
        return session
