from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    def get_by_id(self, db: Session, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def create(self, db: Session, user: UserCreate) -> User:
        db_user = User(
            email=user.email,
            full_name=user.full_name,
            google_id=user.google_id,
            profile_picture=user.profile_picture,
        )

        db.add(db_user)
        db.flush()
        db.refresh(db_user)

        return db_user

    def get_by_email(self, db: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_google_id(self, db: Session, google_id: str) -> User | None:
        stmt = select(User).where(User.google_id == google_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
