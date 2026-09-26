"""
dependencies.py: reusable pieces that routes can ask for with Depends(...).

>>> TEMPORARY (Phase 2 only) <<<
Real login does not exist yet, so get_current_user() below pretends someone is
logged in. It reads an optional "X-User-Id" header (default 1) and auto-creates
a demo user. In Phase 3 this ONE function is replaced by real JWT checking,
and none of the routes that use it have to change. That is the benefit of
dependency injection.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import models
from .database import get_db


def get_current_user(
    x_user_id: int = Header(default=1),   # reads the "X-User-Id" request header
    db: Session = Depends(get_db),
) -> models.User:
    user = db.get(models.User, x_user_id)
    if user is None and x_user_id == 1:
        # First run: create the demo user so the endpoints are usable at once.
        user = models.User(email="demo@readtrack.dev", name="Demo User", password_hash="!")
        db.add(user)
        db.commit()
        db.refresh(user)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user
