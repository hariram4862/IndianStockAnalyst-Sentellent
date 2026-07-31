import pytest

from app.db.database import SessionLocal


@pytest.fixture()
def db_session():
    """A real DB session (Postgres/pgvector, migrated) rolled back after each
    test so integration tests never leave rows behind. Tests using this
    fixture require DATABASE_URL to point at a migrated database — see
    .github/workflows/deploy.yml's `test` job or docker-compose.yml locally.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
