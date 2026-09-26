# Phase 1: REST Foundation

## Run it
```
cd D:\AYUSH\API\readtrack\rest-api
.venv\Scripts\uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs and try the endpoints ("Try it out").
(If the venv is missing: `python -m venv .venv` then `.venv\Scripts\pip install -r requirements.txt`.)

## Reading order
1. `app/database.py`  : connection + session
2. `app/models.py`    : tables
3. `app/schemas.py`   : JSON in/out shapes
4. `app/routers/authors.py` : the full CRUD pattern, heavily commented
5. `app/routers/books.py`   : same pattern + foreign key check
6. `app/main.py`      : wires everything together

## Endpoints
| Method | URL | Success | Errors |
|---|---|---|---|
| GET | /authors | 200 | |
| GET | /authors/{id} | 200 | 404 |
| POST | /authors | 201 | 422 |
| PATCH | /authors/{id} | 200 | 404, 422 |
| DELETE | /authors/{id} | 204 | 404, 409 (has books) |
| GET/POST/PATCH/DELETE | /books ... | same | 422 if author_id is invalid |

## Experiments to try
- Send `{"title": ""}` to POST /books and read the 422 error.
- Create an author, a book, then DELETE the author (409), delete the book, then the author (204).
- PATCH with one field and confirm the others are untouched.
- Delete `readtrack.db` to reset all data (tables are recreated on startup).

---

# Phase 2: REST Features

New files: `app/dependencies.py`, `routers/reviews.py`, `routers/shelf.py`, `routers/users.py`.
Changed: `routers/books.py` (filter/sort/paginate/ratings), `routers/authors.py` (nested books), `schemas.py`.

**Breaking change:** `GET /books` now returns a page object
`{items, total, page, limit, pages}` instead of a bare list.

| Method | URL | Notes |
|---|---|---|
| GET | /books?genre=&author_id=&search=&sort=&page=&limit= | filter, sort (`-avg_rating`), paginate |
| GET | /authors/{id}/books | nested resource |
| GET/POST | /books/{id}/reviews | 409 if you already reviewed it |
| PATCH/DELETE | /reviews/{id} | 403 unless it is your review |
| GET | /shelf?status= | my shelf |
| PUT | /shelf/{book_id} | upsert status |
| PATCH | /shelf/{book_id}/progress | auto-updates status |
| DELETE | /shelf/{book_id} | |
| GET | /users/me/stats | aggregates |

Temporary identity: send header `X-User-Id: 1` (default). Replaced by JWT in Phase 3.

---

# Phase 3: Authentication (JWT)

New: `app/security.py` (bcrypt + JWT), `app/routers/auth.py`. Rewritten: `app/dependencies.py`
(`get_current_user` now verifies a real token; the `X-User-Id` stand-in is gone).

| Method | URL | Notes |
|---|---|---|
| POST | /auth/register | JSON `{email, name, password}` -> 201; 409 if email taken |
| POST | /auth/login | **form data** `username` (email) + `password` -> `{access_token}` |
| GET | /users/me | needs token |

Protected: POST/PATCH/DELETE on authors and books, all reviews writes, all of /shelf, /users/me*.
Public: every GET on authors, books and a book's reviews.

Try it in /docs: register, click **Authorize**, log in with your email as the username, then call any protected endpoint.
From code: send `Authorization: Bearer <token>`.

Configuration (environment variables): `SECRET_KEY` (set your own outside development), `ACCESS_TOKEN_MINUTES` (default 60).

---

# Phase 4: Tests and Docs

New: `tests/` (conftest + 3 test files, 34 tests, ~98% coverage), `pytest.ini`, `requirements-dev.txt`.

Run:
```
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
```
Every test gets a fresh in-memory database via a dependency override (see `tests/conftest.py`).
The suite takes ~45 s mostly because bcrypt is deliberately slow on every registration.

Read the tests as documentation of the API's rules: each test name describes one behavior.

---

# Phase 6: DataLoader (fixing N+1)

New: `app/loaders.py`, `app/extensions.py`. Changed: `schema.py` (relationship resolvers use loaders),
`main.py` (each request gets its own `Loaders`). REST gained `GET /books?ids=&author_ids=` and
`GET /authors?ids=` so the loaders have something to batch against.

## Measured result
Query `{ books(limit: 10) { items { title author { name } } } }` against a real REST API
(10 books, 5 authors):

| Version | REST calls |
|---|---|
| Phase 5 (naive resolvers) | **11** (1 list + 10 author lookups) |
| Phase 6 (DataLoader) | **2** (1 list + 1 batched `GET /authors?ids=...`) |

That is an 82% reduction, and the gap grows with page size (N=100: 101 calls vs 2).

Every response now includes the count: `"extensions": {"restCalls": 2}`. Try it in GraphiQL
(open the response's extensions) or with curl and compare a query with and without `author`.

## How it works
1. `Book.author` calls `loaders.author.load(3)`. It does not hit REST yet; the key is queued.
2. When the current batch of resolvers has all asked, the loader calls `_load_authors([3, 5, ...])` once.
3. Results are matched back to each caller by key. Repeated keys are deduplicated and cached for the request.

## Still not batched (on purpose)
`Book.reviews(last: N)` makes one REST call per book. Batching it needs a REST endpoint that returns
"last N reviews for each of these books", which is a bigger API change than this phase warrants.
Knowing exactly where N+1 remains is part of the exercise.
