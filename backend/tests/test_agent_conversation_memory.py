import uuid

from sqlalchemy import select

from app.models.document import DocumentChunk, SourceDocument
from app.models.stock import FollowedStock, StockEntity
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.agent_graph import AgentGraph
from app.services.embedding_service import EmbeddingService
from app.services.gemini_service import GeminiService
from app.services.research_service import ResearchService


def _get_or_create_test_user(db_session, email: str) -> User:
    user = db_session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, full_name="Memory Test", google_id=f"{email}-sub")
        db_session.add(user)
        db_session.flush()
    return user


def _follow_stock(db_session, user: User, ticker: str) -> StockEntity:
    stock = db_session.execute(select(StockEntity).where(StockEntity.ticker == ticker)).scalar_one_or_none()
    if stock is None:
        stock = StockEntity(ticker=ticker, company_name=f"{ticker} Ltd", exchange="NSE")
        db_session.add(stock)
        db_session.flush()
    followed = db_session.execute(
        select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
    ).scalar_one_or_none()
    if followed is None:
        db_session.add(FollowedStock(user_id=user.id, stock_id=stock.id, is_active=True))
    db_session.flush()
    return stock


def test_second_turn_in_a_session_receives_prior_turns_as_history(db_session, monkeypatch):
    """This is the core "chat forgets everything after turn one" bug: the
    session's transcript must actually reach the agent on later turns, not
    just get persisted and never read back."""
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "memory-history@example.com")
    service = ResearchService()

    captured_histories = []
    original_run = AgentGraph.run

    def spy_run(self, message, history=None):
        captured_histories.append(history)
        return original_run(self, message, history=history)

    monkeypatch.setattr(AgentGraph, "run", spy_run)

    first = service.chat(db_session, user, ChatRequest(message="hello"))
    service.chat(db_session, user, ChatRequest(message="thanks!", session_id=first.session_id))

    assert captured_histories[0] == []
    assert captured_histories[1] == [("user", "hello"), ("assistant", first.answer)]


def test_a_new_session_does_not_inherit_another_sessions_history(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "memory-isolated@example.com")
    service = ResearchService()

    captured_histories = []
    original_run = AgentGraph.run

    def spy_run(self, message, history=None):
        captured_histories.append(history)
        return original_run(self, message, history=history)

    monkeypatch.setattr(AgentGraph, "run", spy_run)

    service.chat(db_session, user, ChatRequest(message="hello"))
    service.chat(db_session, user, ChatRequest(message="hi again"))  # no session_id -> brand new session

    assert captured_histories[0] == []
    assert captured_histories[1] == []


def _seed_news(db_session, stock: StockEntity, content: str) -> None:
    """A minimal grounded article + embedded chunk so retrieval has something
    real to find -- without this, "no ingested data" is the *correct* answer
    regardless of whether ticker carry-forward worked, making that assertion
    meaningless."""
    document = SourceDocument(
        stock_id=stock.id,
        source_type="news",
        external_id=f"test-{stock.ticker}-{uuid.uuid4().hex[:8]}",
        title=f"{stock.ticker}: test news",
        content=content,
        sentiment_label="neutral",
        mentioned_tickers=stock.ticker,
    )
    db_session.add(document)
    db_session.flush()
    embedding = EmbeddingService().embed_text(content)
    db_session.add(DocumentChunk(document_id=document.id, chunk_index=0, content=content, embedding=embedding))
    db_session.flush()


def test_followup_without_repeating_the_ticker_still_resolves_it(db_session, monkeypatch):
    """"What's the sentiment on TCS?" followed by "and its dividend yield?"
    should still resolve to TCS via the carried-forward ticker, not fall
    through to an unscoped answer."""
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "memory-followup@example.com")
    stock = _follow_stock(db_session, user, "FOLLOWUPCO")
    _seed_news(
        db_session, stock,
        "FOLLOWUPCO Ltd reported a stable quarter with a dividend yield of 2.1% and steady operating cash flow.",
    )
    service = ResearchService()

    first = service.chat(db_session, user, ChatRequest(message="What's the sentiment on FOLLOWUPCO this week?"))
    second = service.chat(
        db_session, user, ChatRequest(message="and its dividend yield?", session_id=first.session_id)
    )

    assert second.intent == "research"
    assert "I do not have that in the ingested data" not in second.answer


def test_chitchat_answer_is_personalised_not_a_fixed_string(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "memory-chitchat@example.com")
    _follow_stock(db_session, user, "CHATCO")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="hello"))

    assert "CHATCO" in response.answer


def test_memory_intent_with_no_persona_yet_explains_how_to_set_one(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "memory-empty@example.com")
    service = ResearchService()

    response = service.chat(db_session, user, ChatRequest(message="What do you know about me?"))

    assert response.intent == "memory"
    assert "don't have an investor profile" in response.answer.lower()


def test_memory_intent_reflects_persona_learned_from_chat(db_session, monkeypatch):
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "memory-learned@example.com")
    service = ResearchService()

    service.chat(
        db_session,
        user,
        ChatRequest(message="I'm a conservative, dividend-focused investor and I avoid high-debt companies."),
    )
    response = service.chat(db_session, user, ChatRequest(message="What's my investor profile?"))

    assert response.intent == "memory"
    assert "conservative" in response.answer.lower()
    assert "dividend-focused" in response.answer.lower()


def test_pure_persona_statement_is_acknowledged_not_misrouted_to_research(db_session, monkeypatch):
    """The doc's own canonical example -- "I'm a conservative, dividend-focused
    investor and I avoid high-debt companies" -- contains "dividend" and
    "debt", both research keywords. It must not get misclassified into a
    citation dump about some unrelated followed stock; it should be
    acknowledged as the persona update it actually is."""
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "persona-ack@example.com")
    _follow_stock(db_session, user, "UNRELATEDCO")
    service = ResearchService()

    response = service.chat(
        db_session,
        user,
        ChatRequest(message="I'm a conservative, dividend-focused investor and I avoid high-debt companies."),
    )

    assert response.intent == "persona_update"
    assert "I've noted" in response.answer
    assert "UNRELATEDCO" not in response.answer
    assert "I do not have that in the ingested data" not in response.answer


def test_persona_statement_after_an_earlier_ticker_discussion_is_still_acknowledged(db_session, monkeypatch):
    """Regression: a bare persona statement several turns after discussing a
    followed stock must not inherit that stock via the ticker carry-forward
    feature and get misrouted into a research answer about it -- the
    carry-forward is for follow-up *questions*, not for classifying whether
    this message named a stock at all."""
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "persona-after-ticker@example.com")
    _follow_stock(db_session, user, "EARLIERCO")
    service = ResearchService()

    first = service.chat(db_session, user, ChatRequest(message="What's the sentiment on EARLIERCO this week?"))
    response = service.chat(
        db_session,
        user,
        ChatRequest(
            message="I'm a conservative, dividend-focused investor and I avoid high-debt companies.",
            session_id=first.session_id,
        ),
    )

    assert "I've noted" in response.answer
    assert "EARLIERCO" not in response.answer


def test_persona_statement_naming_a_followed_ticker_still_gets_a_research_answer(db_session, monkeypatch):
    """If the message both states a preference *and* asks about a specific
    followed stock, the research answer still wins -- persona updates
    silently in the background either way."""
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "persona-with-ticker@example.com")
    _follow_stock(db_session, user, "TAGGEDCO")
    service = ResearchService()

    response = service.chat(
        db_session,
        user,
        ChatRequest(message="I'm conservative and avoid high debt -- what's the sentiment on TAGGEDCO?"),
    )

    assert response.intent == "research"


def test_recommend_when_persona_screens_out_every_followed_stock_gives_accurate_message(db_session, monkeypatch):
    """Previously this said "You are not following any stocks yet" even when
    the user does follow stocks and they were simply screened out by their
    own stated rules -- misleading rather than explaining what happened."""
    monkeypatch.setattr(GeminiService, "is_enabled", lambda self: False)
    user = _get_or_create_test_user(db_session, "screened-out@example.com")
    stock = db_session.execute(
        select(StockEntity).where(StockEntity.ticker == "HIGHDEBTCO")
    ).scalar_one_or_none()
    if stock is None:
        stock = StockEntity(
            ticker="HIGHDEBTCO", company_name="HIGHDEBTCO Ltd", exchange="NSE",
            pe_ratio=18.0, dividend_yield=2.0, debt_to_equity=5.0,
        )
        db_session.add(stock)
        db_session.flush()
    followed = db_session.execute(
        select(FollowedStock).where(FollowedStock.user_id == user.id, FollowedStock.stock_id == stock.id)
    ).scalar_one_or_none()
    if followed is None:
        db_session.add(FollowedStock(user_id=user.id, stock_id=stock.id, is_active=True))
        db_session.flush()
    service = ResearchService()

    service.chat(db_session, user, ChatRequest(message="I avoid high-debt companies."))
    response = service.chat(db_session, user, ChatRequest(message="recommend stocks for my profile"))

    assert "not following any stocks yet" not in response.answer
    assert "screen" in response.answer.lower()
