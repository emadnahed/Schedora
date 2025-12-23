"""API dependencies for FastAPI."""
from typing import Generator
from sqlalchemy.orm import Session
from schedora.core.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
