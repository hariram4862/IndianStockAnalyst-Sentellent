from fastapi import APIRouter

from app.api.routes import agent, alerts, auth, health, market, research, stocks, users

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(auth.router)
api_router.include_router(stocks.router)
api_router.include_router(research.router)
api_router.include_router(alerts.router)
api_router.include_router(agent.router)
api_router.include_router(market.router)
