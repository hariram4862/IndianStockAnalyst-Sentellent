from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent_activity import AgentDecision
from app.models.stock import StockEntity
from app.models.user import User
from app.schemas.agent import AgentDecisionResponse

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/decisions", response_model=list[AgentDecisionResponse])
def list_decisions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    rows = db.execute(
        select(AgentDecision, StockEntity)
        .join(StockEntity, StockEntity.id == AgentDecision.stock_id)
        .where(AgentDecision.user_id == current_user.id)
        .order_by(AgentDecision.created_at.desc())
        .limit(limit)
    ).all()

    return [
        AgentDecisionResponse(
            id=decision.id,
            ticker=stock.ticker,
            company_name=stock.company_name,
            action=decision.action,
            reasoning=decision.reasoning,
            composite_score=float(decision.composite_score),
            price_at_decision_inr=float(decision.price_at_decision_inr)
            if decision.price_at_decision_inr is not None
            else None,
            current_price_inr=float(stock.current_price_inr) if stock.current_price_inr is not None else None,
            created_at=decision.created_at,
        )
        for decision, stock in rows
    ]
