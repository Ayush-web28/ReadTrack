"""
routers/reviews.py: reviews of books.

NESTED RESOURCES: a review only exists in the context of a book, so listing
and creating use a nested URL:
    GET  /books/{book_id}/reviews      list a book's reviews
    POST /books/{book_id}/reviews      write a review
But once a review exists it has its own identity, so editing/deleting it uses:
    PATCH  /reviews/{review_id}
    DELETE /reviews/{review_id}

These routes show AUTHORIZATION: anyone can read reviews, but only the
author of a review may change or delete it (403 Forbidden otherwise).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(tags=["Reviews"])   # no prefix: the two URL families differ


@router.get("/books/{book_id}/reviews", response_model=list[schemas.ReviewOut])
def list_reviews(
    book_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Newest reviews first."""
    if db.get(models.Book, book_id) is None:
        raise HTTPException(status_code=404, detail="Book not found")
    stmt = (
        select(models.Review)
        .where(models.Review.book_id == book_id)
        .order_by(models.Review.created_at.desc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


@router.post(
    "/books/{book_id}/reviews",
    response_model=schemas.ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    book_id: int,
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),   # WHO is writing the review
):
    if db.get(models.Book, book_id) is None:
        raise HTTPException(status_code=404, detail="Book not found")

    # Business rule: one review per user per book.
    already = db.execute(
        select(models.Review).where(
            models.Review.book_id == book_id, models.Review.user_id == user.id
        )
    ).scalar_one_or_none()
    if already:
        raise HTTPException(status_code=409, detail="You already reviewed this book")

    review = models.Review(book_id=book_id, user_id=user.id, **payload.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def _get_own_review(db: Session, review_id: int, user: models.User) -> models.Review:
    """404 if it does not exist, 403 if it belongs to someone else."""
    review = db.get(models.Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    # 401 = "who are you?"   403 = "I know who you are, but you may not do this."
    if review.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only change your own reviews")
    return review


@router.patch("/reviews/{review_id}", response_model=schemas.ReviewOut)
def update_review(
    review_id: int,
    payload: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    review = _get_own_review(db, review_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    review = _get_own_review(db, review_id, user)
    db.delete(review)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
