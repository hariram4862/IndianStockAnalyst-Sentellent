from sqlalchemy import select

from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.gemini_service import GeminiService
from app.services.research_service import ResearchService


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Sessions Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def _disable_llm(monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)


def test_list_sessions_orders_by_most_recently_active(db_session, monkeypatch):
    _disable_llm(monkeypatch)
    user = _get_or_create_test_user(db_session, "sessions-order@example.com")
    service = ResearchService()

    first = service.chat(db_session, user, ChatRequest(message="hello"))
    second = service.chat(db_session, user, ChatRequest(message="hi there"))
    # Bump the first session's activity again -- it should now sort ahead of the second.
    service.chat(db_session, user, ChatRequest(message="one more", session_id=first.session_id))

    sessions = service.list_sessions(db_session, user)
    session_ids_in_order = [s.id for s in sessions]

    assert session_ids_in_order.index(first.session_id) < session_ids_in_order.index(second.session_id)


def test_session_title_is_derived_from_first_message(db_session, monkeypatch):
    _disable_llm(monkeypatch)
    user = _get_or_create_test_user(db_session, "sessions-title@example.com")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="What's the sentiment on RELIANCE?"))
    sessions = service.list_sessions(db_session, user)
    session = next(s for s in sessions if s.id == response.session_id)

    assert session.title == "What's the sentiment on RELIANCE?"


def test_get_session_messages_returns_full_transcript_with_citations(db_session, monkeypatch):
    _disable_llm(monkeypatch)
    user = _get_or_create_test_user(db_session, "sessions-messages@example.com")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="hello"))
    messages = service.get_session_messages(db_session, user, response.session_id)

    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "hello"
    assert messages[1].citations == []


def test_get_session_messages_raises_for_another_users_session(db_session, monkeypatch):
    _disable_llm(monkeypatch)
    owner = _get_or_create_test_user(db_session, "sessions-owner@example.com")
    intruder = _get_or_create_test_user(db_session, "sessions-intruder@example.com")
    service = ResearchService()

    response = service.chat(db_session, owner, ChatRequest(message="private research"))

    try:
        service.get_session_messages(db_session, intruder, response.session_id)
        assert False, "expected ValueError for a session the user does not own"
    except ValueError:
        pass
