"""
routers/auth.py: register and log in.

    POST /auth/register   create an account          -> 201 + the new user
    POST /auth/login      exchange credentials       -> 200 + a JWT access token
    GET  /users/me        who am I? (needs a token)  -> lives in users.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()   # emails are case-insensitive in practice

    if db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        email=email,
        name=payload.name,
        password_hash=hash_password(payload.password),   # store the HASH, never the password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user   # UserOut has no password field, so the hash can never leak


@router.post("/login", response_model=schemas.Token)
def login(
    # OAuth2PasswordRequestForm reads a standard FORM (not JSON) with fields
    # "username" and "password". We treat username as the email. Using the
    # standard form is what makes the Authorize button in /docs work.
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.execute(
        select(models.User).where(models.User.email == form.username.lower())
    ).scalar_one_or_none()

    # Same message whether the email is unknown or the password is wrong, so an
    # attacker cannot use this endpoint to discover which emails have accounts.
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return schemas.Token(access_token=create_access_token(user.id))
