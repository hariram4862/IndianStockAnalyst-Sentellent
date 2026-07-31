from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatRequest, ChatResponse, ChatSessionSummary, PersonaResponse
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research", tags=["Research"])
research_service = ResearchService()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return research_service.chat(db, current_user, payload)


@router.get("/sessions", response_model=list[ChatSessionSummary])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return research_service.list_sessions(db, current_user)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return research_service.get_session_messages(db, current_user, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/persona", response_model=PersonaResponse)
def get_persona(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return research_service.get_persona(db, current_user)
