from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.agent import AlertRuleCreate, AlertRuleResponse, TriggeredAlertResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])
alert_service = AlertService()


def _to_rule_response(rule) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=rule.id,
        ticker=rule.stock.ticker,
        company_name=rule.stock.company_name,
        rule_type=rule.rule_type,
        threshold=float(rule.threshold) if rule.threshold is not None else None,
        is_active=rule.is_active,
        last_triggered_at=rule.last_triggered_at,
        created_at=rule.created_at,
    )


def _to_notification_response(notification) -> TriggeredAlertResponse:
    return TriggeredAlertResponse(
        id=notification.id,
        ticker=notification.stock.ticker,
        message=notification.message,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.post("", response_model=AlertRuleResponse)
def create_alert_rule(
    payload: AlertRuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rule = alert_service.create_rule(db, current_user, payload.ticker, payload.rule_type, payload.threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_rule_response(rule)


@router.get("", response_model=list[AlertRuleResponse])
def list_alert_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [_to_rule_response(rule) for rule in alert_service.list_rules(db, current_user)]


@router.delete("/{rule_id}")
def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        alert_service.delete_rule(db, current_user, rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": "Alert rule deleted."}


@router.get("/notifications", response_model=list[TriggeredAlertResponse])
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [_to_notification_response(n) for n in alert_service.list_notifications(db, current_user)]


@router.post("/notifications/read")
def mark_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert_service.mark_notifications_read(db, current_user)
    return {"message": "Notifications marked as read."}
