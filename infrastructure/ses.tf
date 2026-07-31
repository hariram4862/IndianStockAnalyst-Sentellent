# Notification email identity for the scheduled agent job (alerts + daily
# briefing digests). Using the same address as both sender and recipient
# keeps this working entirely within SES sandbox mode -- no need to request
# production access, which can take AWS review time this project doesn't
# have before the deadline. AWS emails a verification link to this address
# right after `apply`; until it's clicked, notification_service.send() just
# no-ops (see backend/app/services/notification_service.py) rather than
# failing the scheduled job.
resource "aws_ses_email_identity" "notifications" {
  email = var.ses_notification_email
}
