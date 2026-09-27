"""
database.py: the database connection.

This file answers one question: "How does our app talk to the database?"
Locally we use SQLite (a database stored in a single file, no server to
install). In production (Render) we use Postgres instead, because a free
Render web service's filesystem is wiped on every restart or redeploy, so
a SQLite file there would lose all its data. Only this ONE file changes to
support both: everywhere else (models.py, routers/...) just uses `db: Session`
and does not care which database is behind it.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# We read the connection string from the DATABASE_URL environment variable, so
# tests, Docker and Render can each point at a different database without
# editing code. Default: a local SQLite file, for running the server directly.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./readtrack.db")

# Render's Postgres gives a URL starting "postgres://" or "postgresql://".
# SQLAlchemy 2.x needs the DRIVER named in the scheme to know which library to
# use, so we rewrite it to "postgresql+psycopg://" (the psycopg driver, listed
# in requirements.txt). SQLite URLs are left untouched.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# check_same_thread=False is a SQLite-only setting: FastAPI may handle one
# request across different threads, and SQLite blocks that by default.
# Postgres has no such restriction, and its driver does not accept this
# argument, so we only pass it when we are actually using SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# The ENGINE is the actual connection to the database.
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# A SESSION is a "conversation" with the database: you add/query/delete
# objects, then commit to save. SessionLocal is a factory that makes
# a fresh session each time we call SessionLocal().
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Every database model (table) in models.py inherits from this class."""


def get_db():
    """
    A FastAPI *dependency*: gives each request its own database session
    and guarantees it is closed afterwards, even if an error occurs.

    Usage in a route:   def my_route(db: Session = Depends(get_db)): ...
    FastAPI calls get_db() for us and passes the result in as `db`.
    """
    db = SessionLocal()
    try:
        yield db          # <- the route runs here, using `db`
    finally:
        db.close()        # <- always runs afterwards (cleanup)
