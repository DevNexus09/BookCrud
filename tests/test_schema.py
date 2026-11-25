"""Unit tests for the Pydantic schemas, without going through HTTP."""

import pytest
from pydantic import ValidationError

from models import Book
from schema import BookBase, BookOut


def test_bookbase_valid(book_data):
    assert BookBase(**book_data).model_dump() == book_data


def test_bookbase_coerces_numeric_string_year(book_data):
    assert BookBase(**{**book_data, "year": "2020"}).year == 2020


@pytest.mark.parametrize("bad", [{"title": ""}, {"year": -1}, {"isbn": "x" * 51}])
def test_bookbase_rejects_invalid(book_data, bad):
    with pytest.raises(ValidationError):
        BookBase(**{**book_data, **bad})


def test_bookout_reads_orm_object(book_data):
    out = BookOut.model_validate(Book(id=7, **book_data))
    assert out.model_dump() == {"id": 7, **book_data}
