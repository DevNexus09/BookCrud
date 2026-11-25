import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from database import Base, get_db

BOOK = {"title": "Test Book", "author": "Test Author", "year": 2022, "isbn": "1234567890"}


@pytest.fixture
def db_session():
    # Fresh in-memory DB per test: tests never touch database.db or depend on each other.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def book_data():
    """Valid request body for a book (a fresh copy per test)."""
    return dict(BOOK)


@pytest.fixture
def book(client, book_data):
    """A book already saved through the API."""
    return client.post("/books/", json=book_data).json()
