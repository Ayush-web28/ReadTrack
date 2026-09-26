"""
models.py: the DATABASE TABLES, written as Python classes.

Each class = one table. Each attribute = one column.
SQLAlchemy turns these into real SQL tables for us.

Don't confuse these with schemas.py:
    models.py  -> what is STORED in the database
    schemas.py -> what goes IN and OUT of the API (JSON)
They are often similar, but keeping them separate is a core best practice
(e.g. a User model has a password_hash that must NEVER appear in a response).

Relationships in our data:

    Author 1 ----< Book 1 ----< Review >---- 1 User
                        \\                       /
                         `---< ShelfEntry >----'

    "1 ----<" means "one to many": one author has many books.
    ShelfEntry connects a User to a Book (their reading status/progress).
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Current time in UTC. Used as the default for 'created_at' columns."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"   # the real table name in the database

    # primary_key=True -> unique ID for each row, auto-incremented by the DB.
    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True -> the database itself rejects duplicate emails.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    # We NEVER store plain passwords, only a hash (used in Phase 3).
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    reviews: Mapped[list["Review"]] = relationship(back_populates="user")
    shelf: Mapped[list["ShelfEntry"]] = relationship(back_populates="user")


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    bio: Mapped[str | None] = mapped_column(Text, default=None)   # nullable = optional

    # relationship() is NOT a column. It is a Python-side shortcut:
    # author.books gives the list of that author's Book objects.
    # back_populates links it to Book.author so both sides stay in sync.
    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    genre: Mapped[str | None] = mapped_column(String(100), index=True, default=None)
    page_count: Mapped[int | None] = mapped_column(default=None)
    published_year: Mapped[int | None] = mapped_column(default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # FOREIGN KEY: this column stores an authors.id value. It is how the
    # database knows "this book belongs to that author".
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))

    author: Mapped[Author] = relationship(back_populates="books")
    reviews: Mapped[list["Review"]] = relationship(back_populates="book")
    shelf_entries: Mapped[list["ShelfEntry"]] = relationship(back_populates="book")


class Review(Base):
    __tablename__ = "reviews"
    # A table-level rule: rating must be between 1 and 5.
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rating: Mapped[int]
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    book: Mapped[Book] = relationship(back_populates="reviews")
    user: Mapped[User] = relationship(back_populates="reviews")

    @property
    def user_name(self) -> str:
        """Lets ReviewOut show the reviewer's name without exposing the User row."""
        return self.user.name


class ShelfEntry(Base):
    """A user's relationship with a book: want to read it? reading it? done?"""

    __tablename__ = "shelf_entries"
    # One user can have only ONE shelf entry per book.
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="one_entry_per_book"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="to-read")  # to-read/reading/finished
    current_page: Mapped[int] = mapped_column(default=0)

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    book: Mapped[Book] = relationship(back_populates="shelf_entries")
    user: Mapped[User] = relationship(back_populates="shelf")
