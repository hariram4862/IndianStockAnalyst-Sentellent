from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_activity import AgentDecision
from app.models.chat import ChatMessage, ChatSession
from app.models.document import SourceDocument
from app.models.stock import FollowedStock, StockEntity, UserPersonaMemory
from app.models.user import User
from app.services.alert_service import AlertService
from app.services.citation_utils import build_citation
from app.services.ingestion_service import IngestionService
from app.services.research_service import encode_message_envelope, ranked_stock_response
from app.services.stock_scoring import from_stock_entity, rank_stocks

logger = logging.getLogger(__name__)

BRIEFING_TITLE_PREFIX = "Daily briefing"
BRIEFING_THROTTLE = timedelta(hours=20)
MAX_BRIEFING_PICKS = 5
BUY_THRESHOLD = 0.6
AVOID_THRESHOLD = 0.35


class AgentJobService:
    """Orchestrates the scheduled agent job's three steps. Each step is a
    separate, independently callable/testable method -- see
    app/jobs/scheduled_agent_job.py for the actual entrypoint that chains them.
    """

    def __init__(
        self,
        ingestion_service: IngestionService | None = None,
        alert_service: AlertService | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or IngestionService()
        self.alert_service = alert_service or AlertService()

    def refresh_followed_stocks(self, db: Session) -> list[StockEntity]:
        """Re-ingests every actively-followed stock once, deduplicated by
        ticker (not by follower count) -- ten users following RELIANCE means
        one refresh, not ten, matching the "efficient retrieval" requirement."""
        tickers = db.execute(
            select(StockEntity.ticker)
            .join(FollowedStock, FollowedStock.stock_id == StockEntity.id)
            .where(FollowedStock.is_active.is_(True))
            .distinct()
        ).scalars().all()

        refreshed: list[StockEntity] = []
        for ticker in tickers:
            try:
                stock, _docs, _chunks, _mode = self.ingestion_service.ingest_ticker(db, ticker)
                refreshed.append(stock)
            except Exception:
                # One ticker's provider hiccup (rate limit, bad data, network)
                # must not abort the refresh for every other followed stock.
                logger.exception("Scheduled refresh failed for ticker %s", ticker)
        return refreshed

    def evaluate_alerts(self, db: Session, stocks: list[StockEntity]) -> int:
        return sum(self.alert_service.evaluate_alerts_for_stock(db, stock) for stock in stocks)

    def generate_daily_briefings(self, db: Session) -> int:
        """One briefing chat session + one AgentDecision per followed stock,
        per user, throttled to roughly once a day. Returns how many
        briefings were actually generated (0 if everyone was already
        briefed today) -- used for the job's summary log."""
        user_ids = db.execute(
            select(FollowedStock.user_id).where(FollowedStock.is_active.is_(True)).distinct()
        ).scalars().all()

        generated = 0
        for user_id in user_ids:
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if user is None or self._already_briefed_today(db, user_id):
                continue
            if self._generate_briefing_for_user(db, user):
                generated += 1
        return generated

    def _already_briefed_today(self, db: Session, user_id: int) -> bool:
        cutoff = datetime.now(timezone.utc) - BRIEFING_THROTTLE
        existing = db.execute(
            select(ChatSession.id).where(
                ChatSession.user_id == user_id,
                ChatSession.title.like(f"{BRIEFING_TITLE_PREFIX}%"),
                ChatSession.created_at >= cutoff,
            )
        ).scalar_one_or_none()
        return existing is not None

    def _generate_briefing_for_user(self, db: Session, user: User) -> bool:
        followed = db.execute(
            select(StockEntity)
            .join(FollowedStock, FollowedStock.stock_id == StockEntity.id)
            .where(FollowedStock.user_id == user.id, FollowedStock.is_active.is_(True))
        ).scalars().all()
        if not followed:
            return False

        persona = db.execute(
            select(UserPersonaMemory).where(UserPersonaMemory.user_id == user.id)
        ).scalar_one_or_none()

        ranked = rank_stocks(
            [from_stock_entity(stock) for stock in followed],
            risk_profile=persona.risk_profile if persona else None,
            investment_style=persona.investment_style if persona else None,
            constraints_text=persona.constraints_text if persona else None,
        )
        by_ticker = {stock.ticker: stock for stock in followed}

        for pick in ranked[:MAX_BRIEFING_PICKS]:
            self._log_decision(db, user, by_ticker[pick.ticker], action=self._action_for_score(pick.composite_score), reasoning=pick.reason, composite_score=pick.composite_score)

        # Stocks the persona's own rules screened out entirely (e.g. a
        # conservative investor's high-debt exclusion) never appear in
        # `ranked`, but that exclusion is itself a decision worth logging --
        # it's the agent visibly applying "screen out the high-debt names".
        ranked_tickers = {pick.ticker for pick in ranked}
        for stock in followed:
            if stock.ticker in ranked_tickers:
                continue
            self._log_decision(
                db,
                user,
                stock,
                action="avoid",
                reasoning=f"Screened out by your investor profile (e.g. debt-to-equity {stock.debt_to_equity}).",
                composite_score=0.0,
            )

        citations = [self._latest_citation(db, by_ticker[pick.ticker]) for pick in ranked[:MAX_BRIEFING_PICKS]]
        citations = [c for c in citations if c is not None]
        ranked_responses = [ranked_stock_response(pick) for pick in ranked[:MAX_BRIEFING_PICKS]]

        answer = self._build_briefing_text(ranked[:MAX_BRIEFING_PICKS], persona)

        session = ChatSession(user_id=user.id, title=f"{BRIEFING_TITLE_PREFIX} — {date.today().isoformat()}")
        db.add(session)
        db.flush()
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=answer,
                citations_json=json.dumps(encode_message_envelope(citations, "briefing", ranked_responses)),
            )
        )
        db.commit()
        return True

    def _action_for_score(self, composite_score: float) -> str:
        if composite_score >= BUY_THRESHOLD:
            return "buy"
        if composite_score <= AVOID_THRESHOLD:
            return "avoid"
        return "hold"

    def _log_decision(self, db: Session, user: User, stock: StockEntity, action: str, reasoning: str, composite_score: float) -> None:
        db.add(
            AgentDecision(
                user_id=user.id,
                stock_id=stock.id,
                action=action,
                reasoning=reasoning,
                composite_score=composite_score,
                price_at_decision_inr=stock.current_price_inr,
            )
        )

    def _latest_citation(self, db: Session, stock: StockEntity):
        document = db.execute(
            select(SourceDocument)
            .where(SourceDocument.stock_id == stock.id)
            .order_by(SourceDocument.published_at.desc().nullslast(), SourceDocument.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if document is None:
            return None
        return build_citation(stock, document, document.content, None)

    def _build_briefing_text(self, ranked, persona: UserPersonaMemory | None) -> str:
        if not ranked:
            return "No followed stocks cleared your investor profile's screening today."

        lines = ["Your autonomous daily briefing, ranked against your investor profile:"]
        for pick in ranked:
            lines.append(f"- {pick.ticker} ({pick.company_name}): score {pick.composite_score:.2f}. {pick.reason}")
        if persona and persona.summary:
            lines.append(f"Investor memory applied: {persona.summary}")
        lines.append("Generated automatically -- ask about any of these in chat for the full cited detail.")
        return "\n".join(lines)
