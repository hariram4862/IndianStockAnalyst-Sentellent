from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import GoogleLoginRequest, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

auth_service = AuthService()


@router.post(
    "/google/login",
    response_model=LoginResponse,
)
def google_login(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    return auth_service.login_with_google(
        db,
        request.id_token,
    )