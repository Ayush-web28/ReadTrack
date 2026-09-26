"""
routers/books.py: all endpoints under /books.

Same CRUD pattern as authors.py, with one new idea: a book BELONGS TO an
author (foreign key), so we must check the author exists before saving.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/books", tags=["Books"])


def _require_author(db: Session, author_id: int) -> None:
    """Small helper: raise 404-style error if the given author does not exist."""
    if db.get(models.Author, author_id) is None:
        # 422 fits here: the request itself is well-formed, but the author_id
        # it points to is not valid. (Not 404, as the /books URL exists.)
        raise HTTPException(status_code=422, detail=f"Author {author_id} does not exist")


@router.get("", response_model=list[schemas.BookOut])
def list_books(db: Session = Depends(get_db)):
    """List all books. (Phase 2 adds filtering, sorting and pagination.)"""
    return db.execute(select(models.Book).order_by(models.Book.title)).scalars().all()


@router.get("/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("", response_model=schemas.BookOut, status_code=status.HTTP_201_CREATED)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)):
    _require_author(db, payload.author_id)   # validate the foreign key first
    book = models.Book(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


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
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
