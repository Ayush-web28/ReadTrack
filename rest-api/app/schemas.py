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

from pydantic import BaseModel, ConfigDict, Field


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
