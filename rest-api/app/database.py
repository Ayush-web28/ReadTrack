"""
database.py: the database connection.

This file answers one question: "How does our app talk to the database?"
We use SQLite (a database stored in a single file, no server to install)
through SQLAlchemy (a library that lets us use Python classes instead of
writing raw SQL).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Where the database lives. "sqlite:///./readtrack.db" = a file called
# readtrack.db in the folder you start the server from.
# (Later, swapping to PostgreSQL only means changing this one line.)
DATABASE_URL = "sqlite:///./readtrack.db"

# The ENGINE is the actual connection to the database.
# check_same_thread=False is a SQLite-only setting: FastAPI may handle one
# request across different threads, and SQLite blocks that by default.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

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
