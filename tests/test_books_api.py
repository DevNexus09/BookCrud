"""End-to-end tests for the /books endpoints, through FastAPI's TestClient."""

import pytest

from models import Book


# ---------- list ----------

def test_list_books_empty(client):
    r = client.get("/books/")
    assert r.status_code == 200
    assert r.json() == []


def test_list_books_returns_created(client, book):
    assert client.get("/books/").json() == [book]


def test_list_books_ordered_by_id(client, book_data):
    ids = [client.post("/books/", json={**book_data, "title": f"B{i}"}).json()["id"] for i in range(3)]
    assert [b["id"] for b in client.get("/books/").json()] == ids


def test_pagination(client, book_data):
    for i in range(5):
        client.post("/books/", json={**book_data, "title": f"Book {i}"})
    titles = [b["title"] for b in client.get("/books/?skip=1&limit=2").json()]
    assert titles == ["Book 1", "Book 2"]


def test_pagination_skip_past_end(client, book):
    assert client.get("/books/?skip=10").json() == []


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=1001", "limit=abc"])
def test_pagination_invalid(client, query):
    assert client.get(f"/books/?{query}").status_code == 422


# ---------- create ----------

def test_create_book(client, book_data):
    r = client.post("/books/", json=book_data)
    assert r.status_code == 201
    body = r.json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], **book_data}


def test_create_book_saved_in_db(client, db_session, book_data):
    book_id = client.post("/books/", json=book_data).json()["id"]
    row = db_session.get(Book, book_id)
    assert (row.title, row.author, row.year, row.isbn) == tuple(book_data.values())


def test_create_assigns_unique_ids(client, book_data):
    a = client.post("/books/", json=book_data).json()["id"]
    b = client.post("/books/", json=book_data).json()["id"]
    assert a != b


def test_create_ignores_client_supplied_id(client, book_data):
    r = client.post("/books/", json={**book_data, "id": 999})
    assert r.status_code == 201
    assert r.json()["id"] != 999


@pytest.mark.parametrize("field", ["title", "author", "year", "isbn"])
def test_create_missing_field(client, book_data, field):
    del book_data[field]
    r = client.post("/books/", json=book_data)
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", field]


@pytest.mark.parametrize(
    "bad",
    [
        {"title": ""},
        {"author": ""},
        {"isbn": ""},
        {"title": "x" * 101},
        {"author": "x" * 101},
        {"isbn": "x" * 51},
        {"year": -1},
        {"year": 10000},
        {"year": "abc"},
        {"title": None},
    ],
)
def test_create_invalid_values(client, book_data, bad):
    assert client.post("/books/", json={**book_data, **bad}).status_code == 422


@pytest.mark.parametrize("good", [{"title": "x" * 100}, {"isbn": "x" * 50}, {"year": 0}, {"year": 9999}])
def test_create_boundary_values_accepted(client, book_data, good):
    assert client.post("/books/", json={**book_data, **good}).status_code == 201


def test_create_empty_body(client):
    assert client.post("/books/").status_code == 422


def test_create_invalid_json(client):
    r = client.post("/books/", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


# ---------- read one ----------

def test_get_book(client, book):
    r = client.get(f"/books/{book['id']}")
    assert r.status_code == 200
    assert r.json() == book


def test_get_book_not_found(client):
    r = client.get("/books/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "Book not found"}


def test_get_book_non_integer_id(client):
    assert client.get("/books/abc").status_code == 422


# ---------- update ----------

def test_update_book(client, book):
    update = {"title": "Updated", "author": "Someone", "year": 2023, "isbn": "0987654321"}
    r = client.put(f"/books/{book['id']}", json=update)
    assert r.status_code == 200
    assert r.json() == {"id": book["id"], **update}
    assert client.get(f"/books/{book['id']}").json() == {"id": book["id"], **update}


def test_update_only_changes_target_book(client, book, book_data):
    other = client.post("/books/", json={**book_data, "title": "Other"}).json()
    client.put(f"/books/{book['id']}", json={**book_data, "title": "Changed"})
    assert client.get(f"/books/{other['id']}").json() == other


def test_update_not_found(client, book_data):
    assert client.put("/books/999", json=book_data).status_code == 404


def test_update_requires_all_fields(client, book):
    # PUT replaces the whole book, so a partial body is rejected and nothing changes.
    r = client.put(f"/books/{book['id']}", json={"title": "Only title"})
    assert r.status_code == 422
    assert client.get(f"/books/{book['id']}").json() == book


def test_update_invalid_value(client, book, book_data):
    r = client.put(f"/books/{book['id']}", json={**book_data, "year": -5})
    assert r.status_code == 422
    assert client.get(f"/books/{book['id']}").json() == book


# ---------- delete ----------

def test_delete_book(client, book):
    r = client.delete(f"/books/{book['id']}")
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.get("/books/").json() == []


def test_delete_twice(client, book):
    assert client.delete(f"/books/{book['id']}").status_code == 204
    assert client.delete(f"/books/{book['id']}").status_code == 404


def test_delete_not_found(client):
    assert client.delete("/books/999").status_code == 404


def test_delete_only_removes_target(client, book, book_data):
    other = client.post("/books/", json={**book_data, "title": "Keep me"}).json()
    client.delete(f"/books/{book['id']}")
    assert client.get("/books/").json() == [other]


# ---------- full flow ----------

def test_full_crud_flow(client, book_data):
    book_id = client.post("/books/", json=book_data).json()["id"]
    assert client.get(f"/books/{book_id}").status_code == 200
    assert client.put(f"/books/{book_id}", json={**book_data, "year": 1999}).json()["year"] == 1999
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get("/books/").json() == []


def test_openapi_docs_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/books/{book_id}" in r.json()["paths"]
