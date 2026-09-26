"""
main.py: the ENTRY POINT. This is the file uvicorn starts.

It creates the FastAPI application, makes sure the database tables exist,
and plugs in the routers.

Run the server (from the rest-api folder):
    .venv\\Scripts\\uvicorn app.main:app --reload
    (app.main = the file app/main.py, :app = the variable named `app` inside it,
     --reload = restart automatically when you edit code)

Then open  http://127.0.0.1:8000/docs  for interactive, auto-generated docs.
"""

from fastapi import FastAPI

from . import models  # noqa: F401  (importing registers the tables with SQLAlchemy)
from .database import Base, engine
from .routers import authors, books

# CREATE TABLE IF NOT EXISTS for every model in models.py.
# Fine for learning; real projects use migrations (Alembic) to evolve a schema.
Base.metadata.create_all(bind=engine)

# title/description/version show up at the top of the /docs page.
app = FastAPI(
    title="ReadTrack REST API",
    description="Track books, authors, reviews and reading progress.",
    version="0.1.0",
)

# Plug each router in. Their routes are now part of the app.
app.include_router(authors.router)
app.include_router(books.router)


@app.get("/", tags=["Health"])
def root():
    """A tiny 'is the server alive?' endpoint, handy for quick checks."""
    return {"status": "ok", "docs": "/docs"}
