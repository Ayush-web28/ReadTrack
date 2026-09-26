"""
openlibrary.py: a client for the free Open Library search API (a THIRD-PARTY API).

Unlike our own REST API, we do not control this one: it can be slow, change,
or be down. So this file (a) sets a timeout, (b) asks only for the fields we
need, and (c) turns every failure into a clear GraphQL error instead of a crash.

Docs: https://openlibrary.org/dev/docs/api/search
"""

import os

import httpx
from graphql import GraphQLError

OPENLIBRARY_URL = os.getenv("OPENLIBRARY_URL", "https://openlibrary.org")

# Open Library asks API users to identify themselves with a User-Agent.
USER_AGENT = "ReadTrack/1.0 (learning project)"

# Only request the fields we use. Smaller response, faster call.
FIELDS = "key,title,author_name,first_publish_year,cover_i,number_of_pages_median"


def make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=OPENLIBRARY_URL, timeout=10, headers={"User-Agent": USER_AGENT}
    )


class OpenLibraryClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http
        self.call_count = 0

    async def search(self, text: str, limit: int) -> list[dict]:
        self.call_count += 1
        try:
            resp = await self.http.get(
                "/search.json", params={"q": text, "limit": limit, "fields": FIELDS}
            )
            resp.raise_for_status()
            return resp.json().get("docs", [])
        except (httpx.HTTPError, ValueError) as exc:
            # HTTPError covers timeouts, connection failures and 4xx/5xx replies;
            # ValueError covers a reply that is not valid JSON.
            raise GraphQLError("Open Library is unavailable, please try again later") from exc
