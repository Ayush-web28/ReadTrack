"""Tests for searchBooks (Open Library + our REST API) and importBook."""

from .conftest import rest_author, rest_book

DUNE = {"key": "/works/OL1W", "title": "Dune", "author_name": ["Frank Herbert"],
        "first_publish_year": 1965, "cover_i": 123, "number_of_pages_median": 608}
EMMA = {"key": "/works/OL2W", "title": "Emma", "author_name": ["Jane Austen"], "first_publish_year": 1815}

SEARCH = """{ searchBooks(text: "dune") { title authors coverUrl pageCount openLibraryKey
                                          inCatalog { id avgRating reviewCount } } }"""


def _page(*items):
    return {"items": list(items), "total": len(items), "page": 1, "limit": 100, "pages": 1 if items else 0}


async def test_search_merges_open_library_with_our_ratings(run, fake, fake_ol):
    fake_ol.add("GET", "/search.json", {"docs": [DUNE, EMMA]})
    fake.add("GET", "/books", _page(rest_book(id=7, author_id=1, title="Dune", avg=4.5, count=2)))
    fake.add("GET", "/authors", [rest_author(1, "Frank Herbert")])

    result = await run(SEARCH)

    assert result.errors is None
    dune, emma = result.data["searchBooks"]
    assert dune["title"] == "Dune" and dune["pageCount"] == 608
    assert dune["coverUrl"] == "https://covers.openlibrary.org/b/id/123-M.jpg"
    assert dune["inCatalog"] == {"id": "7", "avgRating": 4.5, "reviewCount": 2}   # OUR rating, merged in
    assert emma["inCatalog"] is None and emma["coverUrl"] is None                 # unknown to us


async def test_search_makes_one_call_per_service_batch(run, fake, fake_ol):
    fake_ol.add("GET", "/search.json", {"docs": [DUNE, EMMA]})
    fake.add("GET", "/books", _page(rest_book(id=7, author_id=1, title="Dune")))
    fake.add("GET", "/authors", [rest_author(1, "Frank Herbert")])
    await run(SEARCH)
    assert fake_ol.paths == ["/search.json"]
    assert fake.paths == ["/books", "/authors"]           # NOT one call per search result
    assert sorted(fake.requests[0].url.params.get_list("title")) == ["Dune", "Emma"]


async def test_same_title_by_a_different_author_is_not_a_match(run, fake, fake_ol):
    fake_ol.add("GET", "/search.json", {"docs": [DUNE]})
    fake.add("GET", "/books", _page(rest_book(id=9, author_id=2, title="Dune")))
    fake.add("GET", "/authors", [rest_author(2, "Somebody Else")])
    result = await run(SEARCH)
    assert result.data["searchBooks"][0]["inCatalog"] is None


async def test_no_results_skips_our_api_entirely(run, fake, fake_ol):
    fake_ol.add("GET", "/search.json", {"docs": []})
    result = await run(SEARCH)
    assert result.data == {"searchBooks": []} and fake.requests == []


async def test_open_library_outage_becomes_a_clean_error(run, fake, fake_ol):
    fake_ol.add("GET", "/search.json", {"error": "boom"}, status=503)
    result = await run(SEARCH)
    assert result.errors[0].message == "Open Library is unavailable, please try again later"
    assert fake.requests == []


async def test_search_limit_is_clamped_and_sent_with_field_list(run, fake, fake_ol):
    fake_ol.add("GET", "/search.json", {"docs": []})
    await run('{ searchBooks(text: "x", limit: 500) { title } }')
    params = dict(fake_ol.requests[0].url.params)
    assert params["limit"] == "20" and "cover_i" in params["fields"]


async def test_import_creates_author_and_book(run, fake):
    fake.add("GET", "/authors", [])                                              # author unknown
    fake.add("POST", "/authors", rest_author(5, "Frank Herbert"))
    fake.add("GET", "/books", _page())
    fake.add("POST", "/books", rest_book(id=11, author_id=5, title="Dune", avg=None, count=0))
    q = 'mutation { importBook(title: "Dune", authorName: "Frank Herbert", pageCount: 608) { id title } }'

    result = await run(q, token="t")
    assert result.data == {"importBook": {"id": "11", "title": "Dune"}}
    assert [r.method for r in fake.requests] == ["GET", "POST", "GET", "POST"]
    assert all(r.headers["authorization"] == "Bearer t" for r in fake.requests)   # auth forwarded


async def test_import_existing_book_returns_it_without_creating(run, fake):
    fake.add("GET", "/authors", [rest_author(5, "Frank Herbert")])
    fake.add("GET", "/books", _page(rest_book(id=3, author_id=5)))
    result = await run('mutation { importBook(title: "Dune", authorName: "frank herbert") { id } }', token="t")
    assert result.data == {"importBook": {"id": "3"}}
    assert "POST" not in [r.method for r in fake.requests]


async def test_import_without_login_is_rejected_by_rest(run, fake):
    fake.add("GET", "/authors", [])
    fake.add("POST", "/authors", {"detail": "Not authenticated"}, status=401)
    result = await run('mutation { importBook(title: "Dune", authorName: "X") { id } }')
    assert result.errors[0].extensions == {"httpStatus": 401}
