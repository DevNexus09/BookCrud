from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    """Validated input for creating or replacing a book."""

    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=0, le=9999)
    isbn: str = Field(min_length=1, max_length=50)


class BookOut(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
