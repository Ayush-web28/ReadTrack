"""
dependencies.py: reusable pieces that routes can ask for with Depends(...).

get_current_user() is the "security guard" of the API. Any route that lists it
as a dependency is PROTECTED: a request without a valid token never reaches the
route's code, it gets a 401 first.

    @router.post("/books")
    def create_book(..., user: User = Depends(get_current_user)): ...

(In Phase 2 this function was a temporary stand-in. Because routes only depend
on the NAME get_current_user, swapping in real JWT checking needed no route changes.)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_access_token

# Tells FastAPI: "tokens arrive in the Authorization: Bearer <token> header, and
# clients obtain them from POST /auth/login". It also adds the green "Authorize"
# button to /docs, so you can log in once and try every protected endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),   # extracts the token from the header (401 if absent)
    db: Session = Depends(get_db),
) -> models.User:
    # One generic error for every failure: don't tell an attacker WHY it failed.
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},   # standard hint that Bearer auth is expected
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error

    user = db.get(models.User, user_id)
    if user is None:          # valid token, but the user was deleted since
        raise credentials_error
    return user
