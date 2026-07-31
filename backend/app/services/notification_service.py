from __future__ import annotations

import logging

from app.core.config import settings

try:
    import boto3
except Exception:  # pragma: no cover - handled by runtime fallback
    boto3 = None

logger = logging.getLogger(__name__)


class NotificationService:
    """Thin SES wrapper. Optional and fails soft, same pattern as
    GeminiService.is_enabled(): with no SES_SENDER_EMAIL configured (or SES
    misconfigured/unverified), every call is a silent no-op rather than an
    exception -- the scheduled agent job's alerts/briefings must never fail
    just because email delivery isn't set up yet. The in-app notification
    bell (TriggeredAlert rows) is the guaranteed-to-work channel; this is a
    bonus on top of it.
    """

    def is_enabled(self) -> bool:
        return boto3 is not None and bool(settings.ses_sender_email)

    def send(self, subject: str, body: str) -> bool:
        if not self.is_enabled():
            return False

        try:
            client = boto3.client("ses", region_name=settings.aws_region)
            client.send_email(
                Source=settings.ses_sender_email,
                Destination={"ToAddresses": [settings.ses_sender_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                },
            )
            return True
        except Exception:
            logger.exception("Failed to send SES notification email (subject=%r)", subject)
            return False
