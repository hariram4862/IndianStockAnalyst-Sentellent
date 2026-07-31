"""Entrypoint for the scheduled agentic-actions job.

Run as `python -m app.jobs.scheduled_agent_job`. Invoked in production by an
EventBridge Scheduler rule that runs this exact command as a container
override on the same ECS backend task definition/image the API uses -- no
new service, no new image, no HTTP exposure (mirrors how the CI/CD pipeline
already runs `alembic upgrade head` as a one-off ECS task; see
.github/workflows/deploy.yml and infrastructure/scheduler.tf).
"""

from __future__ import annotations

import logging

from app.db.database import SessionLocal
from app.services.agent_job_service import AgentJobService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    service = AgentJobService()
    try:
        refreshed = service.refresh_followed_stocks(db)
        logger.info("Refreshed %d followed stock(s).", len(refreshed))

        fired = service.evaluate_alerts(db, refreshed)
        logger.info("Fired %d alert(s).", fired)

        briefings = service.generate_daily_briefings(db)
        logger.info("Generated %d daily briefing(s).", briefings)
    finally:
        db.close()


if __name__ == "__main__":
    main()
