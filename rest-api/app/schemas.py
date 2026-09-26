"""
schemas.py: the SHAPE OF JSON going in and out of the API.

These are Pydantic models. Pydantic does two jobs for us automatically:
  1. VALIDATION: if a client sends {"title": 123} or forgets a required
     field, FastAPI replies 422 with a clear error, and our code never runs.
  2. SERIALIZATION: turns database objects into JSON for responses, and
     includes ONLY the fields declared here.

Naming pattern used for each resource (e.g. Author):
    AuthorCreate -> what a client sends to CREATE one   (POST)
    AuthorUpdate -> what a client sends to CHANGE one   (PATCH, all optional)
    AuthorOut    -> what the API sends BACK             (responses)
"""

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# The three allowed reading statuses. Literal[...] makes Pydantic reject
# anything else (e.g. "done") with a 422 automatically.
ShelfStatus = Literal["to-read", "reading", "finished"]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """
    A generic PAGINATED response. Page[BookOut] means "a page of books".
    Instead of returning a bare list (which could be thousands of rows),
    list endpoints return one slice plus the info a client needs to ask
    for the next slice.
    """

    items: list[T]
    total: int    # how many rows match in ALL pages
    page: int     # current page number (starts at 1)
    limit: int    # page size
    pages: int    # total number of pages


# ------------------------------------------------------------------ Users
class UserCreate(BaseModel):
    email: EmailStr                                   # validated email format
    name: str = Field(min_length=1, max_length=100)
    # bcrypt only uses the first 72 bytes, so we cap the length instead of
    # silently ignoring the rest.
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    """Deliberately has NO password / password_hash field."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------- Authors
class AuthorCreate(BaseModel):
    # Field(...) adds validation rules: here, a name of 1 to 200 characters.
    name: str = Field(min_length=1, max_length=200)
    bio: str | None = None


class AuthorUpdate(BaseModel):
    # Everything is optional so a client can send just the fields to change.
    name: str | None = Field(default=None, min_length=1, max_length=200)
    bio: str | None = None


class AuthorOut(BaseModel):
    # from_attributes=True lets Pydantic read data from a database object
    # (author.name) and not only from a dict (author["name"]).
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bio: str | None


# ------------------------------------------------------------------ Books
class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    author_id: int
    genre: str | None = Field(default=None, max_length=100)
    # gt = "greater than", ge = "greater than or equal", le = "less than or equal"
    page_count: int | None = Field(default=None, gt=0)
    published_year: int | None = Field(default=None, ge=1000, le=2100)
    description: str | None = None


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    author_id: int | None = None
    genre: str | None = Field(default=None, max_length=100)
    page_count: int | None = Field(default=None, gt=0)
    published_year: int | None = Field(default=None, ge=1000, le=2100)
    description: str | None = None


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author_id: int
    genre: str | None
    page_count: int | None
    published_year: int | None
    description: str | None
    # Computed from the reviews table (not stored on the book itself).
    # Defaults let this schema also be used where no rating info is loaded.
    avg_rating: float | None = None
    review_count: int = 0


# ---------------------------------------------------------------- Reviews
class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: int
    comment: str | None
    created_at: datetime
    book_id: int
    user_id: int
    user_name: str    # comes from the Review.user_name property in models.py


# ------------------------------------------------------------------ Shelf
class ShelfStatusIn(BaseModel):
    status: ShelfStatus


class ProgressIn(BaseModel):
    current_page: int = Field(ge=0)


class ShelfEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ShelfStatus
    current_page: int
    book_id: int
    book: BookOut     # nested object: the shelf entry embeds its book


# ------------------------------------------------------------------ Stats
class StatsOut(BaseModel):
    to_read: int
    reading: int
    finished: int
    pages_read: int
    reviews_written: int
    average_rating_given: float | None
