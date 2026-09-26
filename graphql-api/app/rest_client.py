"""
rest_client.py: how the GraphQL server talks to the REST API.

THE GATEWAY PATTERN: this GraphQL server has NO database. Every resolver gets
its data by calling the REST API over HTTP. So business rules (validation,
ownership checks, password hashing...) live in exactly ONE place: the REST API.
GraphQL is just a flexible "front desk" on top of it.

AUTH PROPAGATION: the browser sends its JWT to us in the Authorization header.
We forward that same header on every REST call, so REST decides who the user is.
We never inspect or store tokens here.
"""

import os

import httpx
from graphql import GraphQLError

REST_API_URL = os.getenv("REST_API_URL", "http://127.0.0.1:8000")


class RestClient:
    """A small wrapper bound to ONE incoming GraphQL request."""

    def __init__(self, http: httpx.AsyncClient, authorization: str | None):
        self.http = http                      # shared connection pool (created once at startup)
        self.authorization = authorization    # the caller's "Bearer <token>" header, if any
        self.call_count = 0                   # how many REST calls this one query caused

    async def request(self, method: str, path: str, *, optional: bool = False, **kwargs):
        headers = {"Authorization": self.authorization} if self.authorization else {}
        self.call_count += 1
        try:
            resp = await self.http.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise GraphQLError("REST API is unreachable") from exc

        if optional and resp.status_code == 404:
            return None                        # "not found" is a valid answer: GraphQL returns null
        if resp.status_code >= 400:
            # Turn the REST error into a GraphQL error. It appears in the
            # response's "errors" array (GraphQL itself still replies HTTP 200).
            detail = resp.json().get("detail", "Request failed") if resp.content else "Request failed"
            if isinstance(detail, list):       # FastAPI validation errors are a list
                detail = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in detail)
            raise GraphQLError(str(detail), extensions={"httpStatus": resp.status_code})
        if resp.status_code == 204:
            return None
        return resp.json()

    # Thin shortcuts so resolvers read like:  await rest.get("/books/7")
    async def get(self, path: str, **kwargs):
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs):
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs):
        return await self.request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs):
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs):
        return await self.request("DELETE", path, **kwargs)
