from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.stock import (
    FollowedStockResponse,
    StockFollowRequest,
    StockIngestionResponse,
    StockRefreshResponse,
)
from app.services.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["Stocks"])
stock_service = StockService()


@router.get("/followed", response_model=list[FollowedStockResponse])
def list_followed_stocks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return stock_service.list_followed_stocks(db, current_user)


@router.post("/follow", response_model=StockIngestionResponse)
def follow_stock(
    payload: StockFollowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return stock_service.follow_stock(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{ticker}/refresh", response_model=StockRefreshResponse)
def refresh_stock(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return stock_service.refresh_stock(db, current_user, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
