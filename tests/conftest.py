"""Shared test fixtures — in-memory SQLite DB, test client, mock LLM."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def engine():
    """In-memory SQLite engine with WAL mode and foreign keys."""
    eng = create_engine("sqlite:///:memory:")

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    """Database session for a single test — rolls back after each test."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(engine):
    """FastAPI TestClient with overridden DB dependency."""
    from fastapi.testclient import TestClient

    session_factory = sessionmaker(bind=engine)

    def _override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_ollama_client():
    """Mock OpenAI-compatible client that returns predefined JSON."""
    with patch("app.ai.client.get_ollama_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture()
def now():
    """Standard reference time for deterministic tests."""
    return datetime(2025, 6, 9, 10, 0, 0, tzinfo=timezone.utc)  # Monday 10:00 UTC
