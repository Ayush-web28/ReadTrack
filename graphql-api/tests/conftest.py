"""
conftest.py: test helpers for the GraphQL gateway.

The gateway has no database, only calls to the REST API. To test it without a
running REST server we plug in a FAKE REST API: httpx.MockTransport lets us
answer every outgoing request with canned JSON, and records each request so
tests can assert HOW MANY REST calls a GraphQL query caused.
"""

import httpx
import pytest

from app.main import Context
from app.openlibrary import OpenLibraryClient
from app.rest_client import RestClient
from app.schema import schema


class FakeRest:
    def __init__(self):
        self.routes: dict[tuple[str, str], object] = {}   # (METHOD, path) -> json or callable
        self.requests: list[httpx.Request] = []           # every call the gateway made

    def add(self, method: str, path: str, body, status: int = 200):
        self.routes[(method, path)] = (status, body)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = (request.method, request.url.path)
        if key not in self.routes:
            return httpx.Response(404, json={"detail": f"no fake route for {key}"})
        status, body = self.routes[key]
        if callable(body):
            body = body(request)
        return httpx.Response(status, json=body)

    @property
    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]


@pytest.fixture()
def fake():
    return FakeRest()


@pytest.fixture()
def fake_ol():
    """A second fake, standing in for the external Open Library API."""
    return FakeRest()


@pytest.fixture()
def run(fake, fake_ol):
    """run(query, variables=None, token=None) -> the GraphQL result, using fake REST + fake Open Library."""

    async def _run(query: str, variables: dict | None = None, token: str | None = None):
        http = httpx.AsyncClient(base_url="http://rest", transport=httpx.MockTransport(fake.handler))
        ol_http = httpx.AsyncClient(base_url="http://ol", transport=httpx.MockTransport(fake_ol.handler))
        context = Context(
            rest=RestClient(http, f"Bearer {token}" if token else None),
            openlibrary=OpenLibraryClient(ol_http),
        )
        result = await schema.execute(query, variable_values=variables, context_value=context)
        await http.aclose()
        await ol_http.aclose()
        return result

    return _run


# ---- reusable fake data (shapes match the REST API's responses) ----
def rest_book(id=1, author_id=1, title="Dune", avg=4.5, count=2):
    return {
        "id": id, "title": title, "author_id": author_id, "genre": "scifi",
        "page_count": 100, "published_year": 1965, "description": None,
        "avg_rating": avg, "review_count": count,
    }


def rest_author(id=1, name="Frank Herbert"):
    return {"id": id, "name": name, "bio": None}
