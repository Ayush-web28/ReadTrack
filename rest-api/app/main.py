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

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (importing registers the tables with SQLAlchemy)
from .database import Base, engine
from .routers import auth, authors, books, reviews, shelf, users

# CREATE TABLE IF NOT EXISTS for every model in models.py.
# Fine for learning; real projects use migrations (Alembic) to evolve a schema.
Base.metadata.create_all(bind=engine)

# title/description/version show up at the top of the /docs page.
app = FastAPI(
    title="ReadTrack REST API",
    description="Track books, authors, reviews and reading progress.",
    version="0.3.0",
)

# CORS (Cross-Origin Resource Sharing): by default a browser blocks JavaScript
# on one origin (e.g. https://readtrack-frontend.onrender.com) from reading
# responses from another origin (this API's own onrender.com URL). This
# middleware tells the browser which origins are allowed to call us.
# CORS_ORIGINS is a comma-separated list, e.g. "https://readtrack-frontend.onrender.com,http://localhost:5173".
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],   # includes "Authorization", for the JWT
)

# Plug each router in. Their routes are now part of the app.
app.include_router(auth.router)
app.include_router(authors.router)
app.include_router(books.router)
app.include_router(reviews.router)
app.include_router(shelf.router)
app.include_router(users.router)


@app.get("/", tags=["Health"])
def root():
    """A tiny 'is the server alive?' endpoint, handy for quick checks."""
    return {"status": "ok", "docs": "/docs"}
