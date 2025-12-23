"""Shared pytest fixtures for all tests."""
import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from schedora.core.database import Base
from schedora.config import get_settings

# Set test database URL before importing anything else
os.environ["DATABASE_URL"] = "postgresql://schedora_user:schedora_pass@localhost:5433/schedora_test"


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine for the session.

    Creates all tables at the start and drops them at the end.
    """
    settings = get_settings()
    engine = create_engine(
        settings.TEST_DATABASE_URL or settings.DATABASE_URL,
        echo=False,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Create a new database session for a test.

    Uses transaction rollback for test isolation - each test runs
    in a transaction that is rolled back after the test completes.
    This is fast and ensures tests don't interfere with each other.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Begin a nested transaction (using SAVEPOINT)
    nested = connection.begin_nested()

    # If the application code calls session.commit, it will only commit
    # the nested transaction (SAVEPOINT), not the outer one
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
