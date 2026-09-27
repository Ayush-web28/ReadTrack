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

# Phase 10: Deploy to Render

Changed: `app/database.py` (works with Postgres, not only SQLite), `app/main.py` (CORS), `requirements.txt`
(added `psycopg[binary]`). New: `render.yaml` at the repo root.

## Why these changes
- **Postgres, not SQLite, in production.** A free Render web service's disk is wiped on every restart or
  redeploy, so a SQLite file there loses its data. `render.yaml` provisions a free Postgres database and
  points `DATABASE_URL` at it. `database.py` rewrites `postgres://` to `postgresql+psycopg://` (the driver
  name SQLAlchemy 2.x needs) and only passes SQLite's `check_same_thread` option when the URL is actually
  SQLite. Locally, nothing changes: no `DATABASE_URL` set → the same SQLite file as before.
- **CORS.** On Render, the frontend and this API are different origins (different `onrender.com`
  subdomains), so the browser blocks the frontend's JavaScript from reading our responses unless we say
  otherwise. `CORS_ORIGINS` (comma-separated) lists which origins may call this API.

## Verified without a live Render account
- `create_engine` on a fake `postgresql+psycopg://` URL resolves the psycopg driver with no error
  (engine creation does not connect; verified with `pytest` still green, 36 tests, 98% coverage).
- Full cross-origin test: this API on `:8000`, the gateway on `:8001`, and a built frontend on `:4173`
  (three different `localhost` ports, standing in for three Render origins), with `CORS_ORIGINS` set to
  the frontend's port. Register, login, and a GraphQL dashboard query all worked from the browser with no
  CORS errors — the same shape of request Render will make in production.
- Not verified: an actual deploy (no Render account available while building this). See the repo root
  `README.md`'s "Deploy to Render" section for the setup steps and what to check after a real deploy.
