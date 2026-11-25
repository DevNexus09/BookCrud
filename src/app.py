from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Book
from schema import BookBase, BookOut

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book CRUD API")

DB = Annotated[Session, Depends(get_db)]


def get_book_or_404(book_id: int, db: DB) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


BookOr404 = Annotated[Book, Depends(get_book_or_404)]


# Handlers are plain `def`: SQLAlchemy sessions are blocking, so FastAPI runs them in a threadpool.
@app.get("/books/", response_model=list[BookOut])
def list_books(db: DB, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    return db.query(Book).order_by(Book.id).offset(skip).limit(limit).all()


@app.post("/books/", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(book: BookBase, db: DB):
    new_book = Book(**book.model_dump())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book: BookOr404):
    return book


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(data: BookBase, book: BookOr404, db: DB):
    for key, value in data.model_dump().items():
        setattr(book, key, value)
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book: BookOr404, db: DB):
    db.delete(book)
    db.commit()
