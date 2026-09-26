"""Tests for reviews (incl. ownership), the personal shelf, and stats."""


# ---------------------------------------------------------------- reviews
def test_review_requires_login(client, book):
    assert client.post(f"/books/{book['id']}/reviews", json={"rating": 5}).status_code == 401


def test_create_and_list_review(client, auth, book):
    resp = client.post(f"/books/{book['id']}/reviews", json={"rating": 5, "comment": "Great"}, headers=auth)
    assert resp.status_code == 201
    assert resp.json()["user_name"] == "Ayush"
    listed = client.get(f"/books/{book['id']}/reviews").json()
    assert [r["comment"] for r in listed] == ["Great"]


def test_review_rating_range_and_missing_book(client, auth, book):
    for bad in (0, 6):
        resp = client.post(f"/books/{book['id']}/reviews", json={"rating": bad}, headers=auth)
        assert resp.status_code == 422
    assert client.post("/books/999/reviews", json={"rating": 3}, headers=auth).status_code == 404


def test_one_review_per_user_per_book(client, auth, book):
    url = f"/books/{book['id']}/reviews"
    assert client.post(url, json={"rating": 5}, headers=auth).status_code == 201
    assert client.post(url, json={"rating": 4}, headers=auth).status_code == 409


def test_only_owner_can_edit_or_delete_review(client, auth, other_auth, book):
    rid = client.post(f"/books/{book['id']}/reviews", json={"rating": 5}, headers=auth).json()["id"]
    assert client.patch(f"/reviews/{rid}", json={"rating": 1}, headers=other_auth).status_code == 403
    assert client.delete(f"/reviews/{rid}", headers=other_auth).status_code == 403
    assert client.patch(f"/reviews/{rid}", json={"rating": 4}, headers=auth).json()["rating"] == 4
    assert client.delete(f"/reviews/{rid}", headers=auth).status_code == 204
    assert client.delete(f"/reviews/{rid}", headers=auth).status_code == 404


def test_average_rating_appears_on_book_and_can_sort(client, auth, other_auth, book):
    url = f"/books/{book['id']}/reviews"
    client.post(url, json={"rating": 5}, headers=auth)
    client.post(url, json={"rating": 2}, headers=other_auth)
    detail = client.get(f"/books/{book['id']}").json()
    assert detail["avg_rating"] == 3.5 and detail["review_count"] == 2
    assert client.get("/books?sort=-avg_rating").json()["items"][0]["avg_rating"] == 3.5


def test_book_with_reviews_cannot_be_deleted(client, auth, book):
    client.post(f"/books/{book['id']}/reviews", json={"rating": 5}, headers=auth)
    assert client.delete(f"/books/{book['id']}", headers=auth).status_code == 409


# ------------------------------------------------------------------ shelf
def test_shelf_requires_login(client):
    assert client.get("/shelf").status_code == 401


def test_add_to_shelf_is_idempotent_upsert(client, auth, book):
    url = f"/shelf/{book['id']}"
    first = client.put(url, json={"status": "reading"}, headers=auth)
    second = client.put(url, json={"status": "reading"}, headers=auth)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]          # same row, not a duplicate
    assert len(client.get("/shelf", headers=auth).json()) == 1


def test_invalid_status_and_missing_book(client, auth, book):
    assert client.put(f"/shelf/{book['id']}", json={"status": "done"}, headers=auth).status_code == 422
    assert client.put("/shelf/999", json={"status": "reading"}, headers=auth).status_code == 404


def test_progress_updates_status_automatically(client, auth, book):
    url = f"/shelf/{book['id']}"
    client.put(url, json={"status": "to-read"}, headers=auth)
    mid = client.patch(f"{url}/progress", json={"current_page": 40}, headers=auth).json()
    assert mid["status"] == "reading"
    done = client.patch(f"{url}/progress", json={"current_page": 100}, headers=auth).json()
    assert done["status"] == "finished" and done["book"]["title"] == "Dune"


def test_progress_rules(client, auth, book):
    url = f"/shelf/{book['id']}/progress"
    assert client.patch(url, json={"current_page": 5}, headers=auth).status_code == 404   # not on shelf yet
    client.put(f"/shelf/{book['id']}", json={"status": "reading"}, headers=auth)
    assert client.patch(url, json={"current_page": 101}, headers=auth).status_code == 422  # past last page
    assert client.patch(url, json={"current_page": -1}, headers=auth).status_code == 422


def test_marking_finished_sets_page_to_end_and_to_read_resets(client, auth, book):
    url = f"/shelf/{book['id']}"
    assert client.put(url, json={"status": "finished"}, headers=auth).json()["current_page"] == 100
    assert client.put(url, json={"status": "to-read"}, headers=auth).json()["current_page"] == 0


def test_shelf_is_private_and_filterable(client, auth, other_auth, book):
    client.put(f"/shelf/{book['id']}", json={"status": "reading"}, headers=auth)
    assert client.get("/shelf", headers=other_auth).json() == []       # other user sees nothing
    assert len(client.get("/shelf?status=reading", headers=auth).json()) == 1
    assert client.get("/shelf?status=finished", headers=auth).json() == []
    assert client.delete(f"/shelf/{book['id']}", headers=auth).status_code == 204
    assert client.delete(f"/shelf/{book['id']}", headers=auth).status_code == 404


# ------------------------------------------------------------------ stats
def test_stats_empty_user(client, auth):
    assert client.get("/users/me/stats", headers=auth).json() == {
        "to_read": 0, "reading": 0, "finished": 0,
        "pages_read": 0, "reviews_written": 0, "average_rating_given": None,
    }


def test_stats_reflect_activity(client, auth, book):
    client.put(f"/shelf/{book['id']}", json={"status": "finished"}, headers=auth)
    client.post(f"/books/{book['id']}/reviews", json={"rating": 4}, headers=auth)
    stats = client.get("/users/me/stats", headers=auth).json()
    assert stats["finished"] == 1 and stats["pages_read"] == 100
    assert stats["reviews_written"] == 1 and stats["average_rating_given"] == 4.0
