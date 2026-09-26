"""
routers/users.py: endpoints about the current user.

/users/me/stats shows AGGREGATION: instead of returning stored rows, we
compute summary numbers (counts, sums, averages) inside the database.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/stats", response_model=schemas.StatsOut)
def my_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # GROUP BY status -> how many books in each status, e.g. {"reading": 2, ...}
    counts = dict(
        db.execute(
            select(models.ShelfEntry.status, func.count())
            .where(models.ShelfEntry.user_id == user.id)
            .group_by(models.ShelfEntry.status)
        ).all()
    )

    # SUM of pages across everything on the shelf. coalesce(x, 0): if there
    # are no rows SUM gives NULL, so we turn that into 0.
    pages_read = db.execute(
        select(func.coalesce(func.sum(models.ShelfEntry.current_page), 0)).where(
            models.ShelfEntry.user_id == user.id
        )
    ).scalar_one()

    # COUNT and AVG of the ratings this user has given.
    reviews_written, avg_rating = db.execute(
        select(func.count(models.Review.id), func.avg(models.Review.rating)).where(
            models.Review.user_id == user.id
        )
    ).one()

    return schemas.StatsOut(
        to_read=counts.get("to-read", 0),
        reading=counts.get("reading", 0),
        finished=counts.get("finished", 0),
        pages_read=pages_read,
        reviews_written=reviews_written,
        average_rating_given=round(float(avg_rating), 2) if avg_rating is not None else None,
    )
