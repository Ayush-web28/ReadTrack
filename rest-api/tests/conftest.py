"""
conftest.py: shared test setup. pytest loads this file automatically.

FIXTURES are reusable setup functions. A test asks for one by naming it as a
parameter, e.g. `def test_x(client, auth):`, and pytest builds it first.

Key idea: every test gets its OWN brand-new empty in-memory database, so tests
never depend on each other or on leftover data.
"""

import os

# Must happen BEFORE importing the app: point it at a throwaway in-memory DB so
# importing app.main never creates a real readtrack.db file during tests.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    # StaticPool = every connection shares ONE in-memory database
    # (otherwise each connection would see its own empty one).
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    # DEPENDENCY OVERRIDE: whenever a route asks for get_db, hand it the test
    # database instead. This is why dependency injection makes testing easy.
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def make_user(client, email="ayush@example.com", name="Ayush", password="secret123"):
    """Register + log in, and return headers carrying a valid token."""
    client.post("/auth/register", json={"email": email, "name": name, "password": password})
    resp = client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    """Headers for a logged-in user (the default test user)."""
    return make_user(client)


@pytest.fixture()
def other_auth(client):
    """Headers for a SECOND user, for testing that you cannot touch someone else's data."""
    return make_user(client, email="bee@example.com", name="Bee")


@pytest.fixture()
def book(client, auth):
    """A ready-made author + book (100 pages). Returns the book JSON."""
    author = client.post("/authors", json={"name": "Frank Herbert"}, headers=auth).json()
    return client.post(
        "/books",
        json={"title": "Dune", "author_id": author["id"], "genre": "scifi", "page_count": 100},
        headers=auth,
    ).json()
