"""Shared test fixtures."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.models.db_models  # noqa: F401 — registers ORM models with Base.metadata
import app.database as db_module
from app.database import Base, get_db
from app.main import app


@pytest.fixture(name="client")
def fixture_client() -> Generator[TestClient, None, None]:
    """FastAPI test client backed by a fresh in-memory SQLite database.

    Uses a single shared connection to ensure all sessions (including
    the one created by init_db) see the same in-memory tables.
    """
    # Single connection shared across the whole test — SQLite in-memory
    # creates a fresh database per connection, so we must reuse one.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Keep one connection open for the lifetime of the test so the
    # in-memory database is not destroyed between sessions.
    shared_connection = test_engine.connect()

    # Wrap every transaction in a savepoint so we can roll back after
    # each test without recreating tables.
    Base.metadata.create_all(bind=shared_connection)

    TestingSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=shared_connection,
    )

    # Swap out the global engine/session so init_db uses the same DB.
    original_engine = db_module.engine
    original_session_local = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = TestingSession

    def _override_get_db() -> Generator[Session, None, None]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Teardown
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=shared_connection)
    shared_connection.close()
    test_engine.dispose()
    db_module.engine = original_engine
    db_module.SessionLocal = original_session_local


@pytest.fixture(name="db_session")
def fixture_db_session(client: TestClient) -> Generator[Session, None, None]:
    """Expose a direct DB session for the same in-memory DB used by client."""
    session = db_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(name="mock_llm")
def fixture_mock_llm() -> Generator[MagicMock, None, None]:
    """Mock the LLM to avoid real API calls during tests."""
    mock_response = MagicMock()
    mock_response.content = "This is a test answer based on the provided context."

    mock = MagicMock(return_value=mock_response)

    with patch("app.services.rag_service._build_llm") as patched:
        patched.return_value.invoke = mock
        yield mock


@pytest.fixture(name="db_session")
def fixture_db_session(client: TestClient) -> Generator[Session, None, None]:
    """Expose a direct DB session for the same in-memory DB used by client."""
    session = db_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(name="mock_llm")
def fixture_mock_llm() -> Generator[MagicMock, None, None]:
    """Mock the LLM to avoid real API calls during tests."""
    mock_response = MagicMock()
    mock_response.content = "This is a test answer based on the provided context."

    mock = MagicMock(return_value=mock_response)

    with patch("app.services.rag_service._build_llm") as patched:
        patched.return_value.invoke = mock
        yield mock
