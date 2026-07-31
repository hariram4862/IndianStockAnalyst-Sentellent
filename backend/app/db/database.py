from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create the SQLAlchemy Engine
engine = create_engine(
    settings.database_url,
    echo=settings.environment != "production",
)

# Factory for creating database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
