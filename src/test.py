import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from database import Base, get_db

BOOK = {"title": "Test Book", "author": "Test Author", "year": 2022, "isbn": "1234567890"}


@pytest.fixture
def client():
    # Fresh in-memory DB per test so tests never touch database.db or depend on each other.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_books_empty(client):
    r = client.get("/books/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_fetch_book(client):
    r = client.post("/books/", json=BOOK)
    assert r.status_code == 201
    created = r.json()
    assert created == {"id": created["id"], **BOOK}

    r = client.get(f"/books/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created
    assert client.get("/books/").json() == [created]


def test_update_book(client):
    book_id = client.post("/books/", json=BOOK).json()["id"]
    update = {"title": "Updated", "author": "Someone", "year": 2023, "isbn": "0987654321"}
    r = client.put(f"/books/{book_id}", json=update)
    assert r.status_code == 200
    assert r.json() == {"id": book_id, **update}
    assert client.get(f"/books/{book_id}").json()["title"] == "Updated"


def test_delete_book(client):
    book_id = client.post("/books/", json=BOOK).json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_book_404(client, method):
    kwargs = {"json": BOOK} if method == "put" else {}
    assert getattr(client, method)("/books/999", **kwargs).status_code == 404


@pytest.mark.parametrize("bad", [{"title": ""}, {"year": "abc"}, {"year": -1}, {"isbn": "x" * 51}])
def test_create_invalid(client, bad):
    assert client.post("/books/", json={**BOOK, **bad}).status_code == 422


def test_pagination(client):
    for i in range(3):
        client.post("/books/", json={**BOOK, "title": f"Book {i}"})
    titles = [b["title"] for b in client.get("/books/?skip=1&limit=1").json()]
    assert titles == ["Book 1"]
