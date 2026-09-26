"""
routers/shelf.py: the current user's personal bookshelf.

Each shelf entry says "this user is to-read / reading / finished this book"
and how far through it they are. Every route here is PRIVATE: it only ever
touches the logged-in user's own entries (see get_current_user).

    GET    /shelf?status=reading     my books (optionally filtered by status)
    PUT    /shelf/{book_id}          put a book on my shelf / change its status
    PATCH  /shelf/{book_id}/progress update the page I am on
    DELETE /shelf/{book_id}          remove it from my shelf
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(prefix="/shelf", tags=["Shelf"])


def _find_entry(db: Session, user: models.User, book_id: int) -> models.ShelfEntry | None:
    return db.execute(
        select(models.ShelfEntry).where(
            models.ShelfEntry.user_id == user.id, models.ShelfEntry.book_id == book_id
        )
    ).scalar_one_or_none()


@router.get("", response_model=list[schemas.ShelfEntryOut])
def my_shelf(
    status: schemas.ShelfStatus | None = None,   # optional ?status= filter
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    stmt = select(models.ShelfEntry).where(models.ShelfEntry.user_id == user.id)
    if status:
        stmt = stmt.where(models.ShelfEntry.status == status)
    return db.execute(stmt.order_by(models.ShelfEntry.id)).scalars().all()


@router.put("/{book_id}", response_model=schemas.ShelfEntryOut)
def set_status(
    book_id: int,
    payload: schemas.ShelfStatusIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    PUT is IDEMPOTENT: sending the same request twice leaves the same result.
    That fits "set this book's status to X", which creates the entry the first
    time and simply overwrites it afterwards (an "upsert").
    """
    book = db.get(models.Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    entry = _find_entry(db, user, book_id)
    if entry is None:
        entry = models.ShelfEntry(user_id=user.id, book_id=book_id)
        db.add(entry)

    entry.status = payload.status
    # Keep progress consistent with the status.
    if payload.status == "to-read":
        entry.current_page = 0
    elif payload.status == "finished" and book.page_count:
        entry.current_page = book.page_count

    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{book_id}/progress", response_model=schemas.ShelfEntryOut)
def update_progress(
    book_id: int,
    payload: schemas.ProgressIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _find_entry(db, user, book_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Book is not on your shelf")

    pages = entry.book.page_count
    if pages and payload.current_page > pages:
        raise HTTPException(status_code=422, detail=f"This book only has {pages} pages")

    entry.current_page = payload.current_page
    # The status follows the progress automatically.
    if pages and payload.current_page == pages:
        entry.status = "finished"
    elif payload.current_page > 0:
        entry.status = "reading"

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_shelf(
    book_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    entry = _find_entry(db, user, book_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Book is not on your shelf")
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
