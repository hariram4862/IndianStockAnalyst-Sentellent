from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.schemas.auth import LoginResponse
from app.services.google_auth_service import GoogleAuthService
from app.services.user_service import UserService


class AuthService:

    def __init__(self):
        self.google_auth_service = GoogleAuthService()
        self.user_service = UserService()

    def login_with_google(
        self,
        db: Session,
        google_token: str,
    ) -> LoginResponse:

        # Verify Google ID Token
        google_data = self.google_auth_service.verify_google_token(
            google_token
        )

        # Get existing user or create a new one
        user = self.user_service.get_or_create_google_user(
            db,
            google_data,
        )

        # Create our application's JWT
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
            }
        )

        return LoginResponse(
            access_token=access_token,
            user=user,
        )