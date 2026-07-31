from sqlalchemy import select

from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.gemini_service import GeminiService
from app.services.research_service import ResearchService


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Citation Guard Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def test_chat_refuses_ungrounded_question_without_ever_calling_the_answer_llm(db_session, monkeypatch):
    # Force Gemini "enabled" and make the answer-generation call blow up if hit,
    # to prove the anti-hallucination guard is structural -- it must short-circuit
    # before generate_answer ever reaches the LLM, not merely happen to be
    # skipped because no API key is configured in the test environment.
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: True)
    monkeypatch.setattr(GeminiService, "chat_json", lambda self, *a, **kw: None)

    def _fail_if_called(self, *a, **kw):
        raise AssertionError("chat_text (LLM answer generation) must not be called when ungrounded")

    monkeypatch.setattr(GeminiService, "chat_text", _fail_if_called)

    user = _get_or_create_test_user(db_session, "citation-guard@example.com")
    service = ResearchService()

    # This user follows nothing, so a question naming RELIANCE specifically
    # must refuse rather than substitute some other followed stock's data.
    response = service.chat(db_session, user, ChatRequest(message="What's the sentiment on RELIANCE this week?"))

    assert "I do not have that in the ingested data" in response.answer
    assert response.citations == []


def test_chat_greeting_never_calls_the_answer_llm_either(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: True)
    monkeypatch.setattr(GeminiService, "chat_json", lambda self, *a, **kw: None)

    def _fail_if_called(self, *a, **kw):
        raise AssertionError("chat_text must not be called for a plain greeting")

    monkeypatch.setattr(GeminiService, "chat_text", _fail_if_called)

    user = _get_or_create_test_user(db_session, "citation-guard-greeting@example.com")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="hello"))

    assert response.citations == []
    assert "recommend stocks" in response.answer.lower() or "ask me about" in response.answer.lower()
