"""
routers/books.py: all endpoints under /books.

Phase 2 adds to the basic CRUD from Phase 1:
  * FILTERING   GET /books?genre=scifi&author_id=3&search=dune
  * SORTING     GET /books?sort=-avg_rating        ("-" = descending)
  * PAGINATION  GET /books?page=2&limit=10
  * RATINGS     every book now reports avg_rating and review_count
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/books", tags=["Books"])


def _require_author(db: Session, author_id: int) -> None:
    """Small helper: raise an error if the given author does not exist."""
    if db.get(models.Author, author_id) is None:
        # 422 fits here: the request itself is well-formed, but the author_id
        # it points to is not valid. (Not 404, as the /books URL exists.)
        raise HTTPException(status_code=422, detail=f"Author {author_id} does not exist")


# ---- rating statistics ------------------------------------------------------
# A SUBQUERY: "for each book, its average rating and number of reviews".
# In SQL:  SELECT book_id, AVG(rating), COUNT(id) FROM reviews GROUP BY book_id
# We LEFT JOIN it onto books, so books with no reviews still appear (as NULL).
_rating_stats = (
    select(
        models.Review.book_id.label("book_id"),
        func.avg(models.Review.rating).label("avg_rating"),
        func.count(models.Review.id).label("review_count"),
    )
    .group_by(models.Review.book_id)
    .subquery()
)


def _books_with_ratings():
    """Base query returning (Book, avg_rating, review_count) rows."""
    return select(
        models.Book, _rating_stats.c.avg_rating, _rating_stats.c.review_count
    ).outerjoin(_rating_stats, _rating_stats.c.book_id == models.Book.id)


def _to_out(book: models.Book, avg_rating, review_count) -> schemas.BookOut:
    """Combine a Book row and its rating numbers into one response object."""
    out = schemas.BookOut.model_validate(book)
    out.avg_rating = round(float(avg_rating), 2) if avg_rating is not None else None
    out.review_count = review_count or 0
    return out


# Which values are allowed for ?sort=. A whitelist means a client can never
# make us sort by (or leak) an arbitrary column.
_SORT_COLUMNS = {
    "title": models.Book.title,
    "published_year": models.Book.published_year,
    "page_count": models.Book.page_count,
    "avg_rating": _rating_stats.c.avg_rating,
    "review_count": _rating_stats.c.review_count,
}


@router.get("", response_model=schemas.Page[schemas.BookOut])
def list_books(
    db: Session = Depends(get_db),
    # Query(...) declares a QUERY PARAMETER (the ?key=value part of the URL)
    # and lets us add validation and documentation.
    genre: str | None = Query(default=None, description="Exact genre, e.g. scifi"),
    author_id: int | None = Query(default=None),
    search: str | None = Query(default=None, description="Text contained in the title"),
    sort: str = Query(default="title", description="title, published_year, page_count, avg_rating, review_count. Prefix with - for descending"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),   # cap page size to protect the server
):
    stmt = _books_with_ratings()

    # --- FILTERING: add a WHERE clause only for the filters the client sent.
    if genre:
        stmt = stmt.where(models.Book.genre == genre)
    if author_id:
        stmt = stmt.where(models.Book.author_id == author_id)
    if search:
        stmt = stmt.where(models.Book.title.ilike(f"%{search}%"))   # case-insensitive LIKE

    # --- TOTAL: count matching rows BEFORE slicing them into pages.
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    # --- SORTING: "-price" -> descending on "price".
    descending = sort.startswith("-")
    sort_key = sort.lstrip("-")
    column = _SORT_COLUMNS.get(sort_key)
    if column is None:
        raise HTTPException(status_code=422, detail=f"Cannot sort by '{sort_key}'")
    ordering = column.desc().nulls_last() if descending else column.asc().nulls_last()
    # Book.id as a tie-breaker keeps the order stable, so a book never
    # appears on two different pages.
    stmt = stmt.order_by(ordering, models.Book.id)

    # --- PAGINATION: skip the previous pages, take `limit` rows.
    stmt = stmt.offset((page - 1) * limit).limit(limit)
    rows = db.execute(stmt).all()

    return schemas.Page[schemas.BookOut](
        items=[_to_out(book, avg, count) for book, avg, count in rows],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit),
    )


@router.get("/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    row = db.execute(_books_with_ratings().where(models.Book.id == book_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return _to_out(*row)


@router.post("", response_model=schemas.BookOut, status_code=status.HTTP_201_CREATED)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)):
    _require_author(db, payload.author_id)   # validate the foreign key first
    book = models.Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return _to_out(book, None, 0)   # a brand-new book has no reviews


@router.patch("/{book_id}", response_model=schemas.BookOut)
def update_book(book_id: int, payload: schemas.BookUpdate, db: Session = Depends(get_db)):
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    changes = payload.model_dump(exclude_unset=True)   # only what the client sent
    if "author_id" in changes:
        # If they are moving the book to another author, make sure that author exists.
        _require_author(db, changes["author_id"])

    for field, value in changes.items():
        setattr(book, field, value)

    db.commit()
    return get_book(book_id, db)   # reuse get_book to include fresh rating info


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    # A book with reviews/shelf entries would leave orphaned rows behind.
    if book.reviews or book.shelf_entries:
        raise HTTPException(status_code=409, detail="Book has reviews or shelf entries")
    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
