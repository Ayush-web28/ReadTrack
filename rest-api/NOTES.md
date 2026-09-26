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
