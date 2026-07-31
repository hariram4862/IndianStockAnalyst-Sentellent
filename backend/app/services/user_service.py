from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class UserService:

    def __init__(self):
        self.repository = UserRepository()

    def create_user(self, db: Session, user: UserCreate):
        existing = self.repository.get_by_email(db, user.email)

        if existing:
            raise ValueError("User already exists.")

        db_user = self.repository.create(db, user)

        db.commit()

        return db_user

    def get_or_create_google_user(
        self,
        db: Session,
        google_data: dict,
    ):
        existing = self.repository.get_by_google_id(
            db,
            google_data["sub"],
        )

        if existing:
            return existing

        user = UserCreate(
            email=google_data["email"],
            full_name=google_data["name"],
            google_id=google_data["sub"],
            profile_picture=google_data.get("picture"),
        )

        db_user = self.repository.create(db, user)

        db.commit()

        return db_user