"""
main.py: the entry point of the GraphQL gateway (runs on port 8001).

Start it (REST API must already be running on port 8000):
    python -m uvicorn app.main:app --port 8001 --reload
Then open http://127.0.0.1:8001/graphql : the built-in GraphiQL explorer with
autocomplete and docs generated from the schema.

To call protected fields (me, addReview...) add a header in GraphiQL's
"Headers" tab:   {"Authorization": "Bearer <token from the login mutation>"}
"""

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import BaseContext, GraphQLRouter

from .loaders import Loaders
from .openlibrary import OpenLibraryClient, make_http_client
from .rest_client import REST_API_URL, RestClient
from .schema import schema


class Context(BaseContext):
    """
    Per-request object available to every resolver as info.context.
    Strawberry requires custom contexts to inherit from BaseContext.
    """

    def __init__(self, rest: RestClient, openlibrary: OpenLibraryClient):
        super().__init__()
        self.rest = rest
        self.openlibrary = openlibrary
        self.loaders = Loaders(rest)   # fresh DataLoaders (and caches) for every request


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ONE shared HTTP client for the whole server (reuses connections = faster
    # than opening a new connection for every REST call).
    app.state.http = httpx.AsyncClient(base_url=REST_API_URL, timeout=10)
    app.state.ol_http = make_http_client()       # separate client for the external API
    yield
    await app.state.http.aclose()
    await app.state.ol_http.aclose()


async def get_context(request: Request) -> Context:
    # Called once per GraphQL request. We copy the caller's Authorization
    # header into the REST client so it is forwarded to the REST API.
    return Context(
        rest=RestClient(request.app.state.http, request.headers.get("authorization")),
        openlibrary=OpenLibraryClient(request.app.state.ol_http),
    )


# CORS: lets the frontend (a different origin in production) call this gateway
# directly from the browser. See the matching comment in rest-api/app/main.py.
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

app = FastAPI(title="ReadTrack GraphQL Gateway", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")
