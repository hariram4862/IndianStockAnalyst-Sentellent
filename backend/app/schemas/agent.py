from datetime import datetime

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=15)
    rule_type: str
    threshold: float | None = None


class AlertRuleResponse(BaseModel):
    id: int
    ticker: str
    company_name: str
    rule_type: str
    threshold: float | None
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime


class TriggeredAlertResponse(BaseModel):
    id: int
    ticker: str
    message: str
    is_read: bool
    created_at: datetime


class AgentDecisionResponse(BaseModel):
    id: int
    ticker: str
    company_name: str
    action: str
    reasoning: str
    composite_score: float
    price_at_decision_inr: float | None
    current_price_inr: float | None
    created_at: datetime
