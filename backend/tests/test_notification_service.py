from app.core.config import settings
from app.services.notification_service import NotificationService


def test_is_enabled_false_when_sender_email_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "ses_sender_email", None)
    assert NotificationService().is_enabled() is False


def test_is_enabled_true_when_sender_email_configured(monkeypatch):
    monkeypatch.setattr(settings, "ses_sender_email", "agent@example.com")
    assert NotificationService().is_enabled() is True


def test_send_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ses_sender_email", None)
    assert NotificationService().send("subject", "body") is False


def test_send_swallows_boto3_errors_instead_of_raising(monkeypatch):
    monkeypatch.setattr(settings, "ses_sender_email", "agent@example.com")

    class _ExplodingClient:
        def send_email(self, **kwargs):
            raise RuntimeError("SES not verified")

    import app.services.notification_service as module

    monkeypatch.setattr(module.boto3, "client", lambda *a, **kw: _ExplodingClient())

    result = NotificationService().send("subject", "body")
    assert result is False
