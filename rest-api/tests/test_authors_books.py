"""Tests for authors and books: CRUD, protection, filtering, sorting, pagination."""


def test_reads_are_public_but_writes_need_a_token(client):
    assert client.get("/authors").status_code == 200
    assert client.get("/books").status_code == 200
    assert client.post("/authors", json={"name": "X"}).status_code == 401


def test_author_crud_cycle(client, auth):
    created = client.post("/authors", json={"name": "Ursula", "bio": "SF"}, headers=auth)
    assert created.status_code == 201
    aid = created.json()["id"]

    assert client.get(f"/authors/{aid}").json()["name"] == "Ursula"
    patched = client.patch(f"/authors/{aid}", json={"bio": "New"}, headers=auth).json()
    assert patched["bio"] == "New" and patched["name"] == "Ursula"   # PATCH keeps other fields

    assert client.delete(f"/authors/{aid}", headers=auth).status_code == 204
    assert client.get(f"/authors/{aid}").status_code == 404


def test_author_validation_and_missing(client, auth):
    assert client.post("/authors", json={"name": ""}, headers=auth).status_code == 422
    assert client.get("/authors/999").status_code == 404
    assert client.patch("/authors/999", json={"bio": "x"}, headers=auth).status_code == 404


def test_cannot_delete_author_with_books(client, auth, book):
    assert client.delete(f"/authors/{book['author_id']}", headers=auth).status_code == 409


def test_nested_author_books(client, auth, book):
    resp = client.get(f"/authors/{book['author_id']}/books")
    assert [b["title"] for b in resp.json()] == ["Dune"]
    assert client.get("/authors/999/books").status_code == 404


def test_book_requires_existing_author_and_valid_fields(client, auth):
    assert client.post("/books", json={"title": "X", "author_id": 999}, headers=auth).status_code == 422
    assert client.post("/books", json={"title": "", "author_id": 1}, headers=auth).status_code == 422
    assert client.post("/books", json={"title": "X", "author_id": 1, "page_count": 0}, headers=auth).status_code == 422


def test_book_patch_and_delete(client, auth, book):
    resp = client.patch(f"/books/{book['id']}", json={"page_count": 250}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["page_count"] == 250 and resp.json()["title"] == "Dune"
    assert client.patch(f"/books/{book['id']}", json={"author_id": 999}, headers=auth).status_code == 422
    assert client.delete(f"/books/{book['id']}", headers=auth).status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404


def _seed_books(client, auth):
    aid = client.post("/authors", json={"name": "A"}, headers=auth).json()["id"]
    for title, genre, year in [("Alpha", "scifi", 2001), ("Beta", "scifi", 1999), ("Gamma", "classic", 1850)]:
        client.post(
            "/books",
            json={"title": title, "author_id": aid, "genre": genre, "published_year": year},
            headers=auth,
        )
    return aid


def _titles(client, url):
    return [b["title"] for b in client.get(url).json()["items"]]


def test_list_filter_by_genre_author_and_search(client, auth):
    aid = _seed_books(client, auth)
    assert _titles(client, "/books?genre=scifi") == ["Alpha", "Beta"]
    assert _titles(client, f"/books?author_id={aid}") == ["Alpha", "Beta", "Gamma"]
    assert _titles(client, "/books?search=amm") == ["Gamma"]          # case-insensitive substring
    assert _titles(client, "/books?genre=nothing") == []


def test_list_sorting(client, auth):
    _seed_books(client, auth)
    assert _titles(client, "/books?sort=published_year") == ["Gamma", "Beta", "Alpha"]
    assert _titles(client, "/books?sort=-published_year") == ["Alpha", "Beta", "Gamma"]
    assert client.get("/books?sort=password").status_code == 422   # not whitelisted


def test_list_pagination(client, auth):
    _seed_books(client, auth)
    page1 = client.get("/books?limit=2&page=1").json()
    page2 = client.get("/books?limit=2&page=2").json()
    assert (page1["total"], page1["pages"]) == (3, 2)
    assert [b["title"] for b in page1["items"]] == ["Alpha", "Beta"]
    assert [b["title"] for b in page2["items"]] == ["Gamma"]
    assert client.get("/books?page=0").status_code == 422
    assert client.get("/books?limit=1000").status_code == 422   # page size is capped
