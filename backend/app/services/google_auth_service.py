from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings


class GoogleAuthService:

    @staticmethod
    def verify_google_token(token: str) -> dict:
        """
        Verify Google ID token and return user information.
        """

        return id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id,
        )