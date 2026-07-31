from pydantic import BaseModel

from app.schemas.user import UserResponse


class GoogleLoginRequest(BaseModel):
    id_token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse