"""Tests for the gateway's queries and mutations (against a fake REST API)."""

from .conftest import rest_author, rest_book


async def test_client_chooses_fields_and_relationships_are_resolved(run, fake):
    fake.add("GET", "/books/1", rest_book())
    fake.add("GET", "/authors", [rest_author()])       # authors are fetched through the batch loader
    fake.add("GET", "/books/1/reviews", [
        {"id": 1, "rating": 5, "comment": "x", "created_at": "2026-01-01T00:00:00", "user_name": "Ayush"},
    ])
    result = await run("{ book(id: 1) { title avgRating author { name } reviews(last: 1) { rating userName } } }")
    assert result.errors is None
    assert result.data == {"book": {
        "title": "Dune", "avgRating": 4.5,
        "author": {"name": "Frank Herbert"},
        "reviews": [{"rating": 5, "userName": "Ayush"}],
    }}


async def test_resolvers_only_run_for_requested_fields(run, fake):
    fake.add("GET", "/books/1", rest_book())
    await run("{ book(id: 1) { title } }")
    assert fake.paths == ["/books/1"]     # no author or review calls were made


async def test_missing_book_is_null_not_an_error(run, fake):
    fake.add("GET", "/books/9", {"detail": "Book not found"}, status=404)
    result = await run("{ book(id: 9) { title } }")
    assert result.errors is None and result.data == {"book": None}


async def test_books_list_forwards_filters_and_maps_page(run, fake):
    fake.add("GET", "/books", {"items": [rest_book()], "total": 1, "page": 1, "limit": 5, "pages": 1})
    result = await run('{ books(genre: "scifi", sort: "-avg_rating", limit: 5) { total pages items { title } } }')
    assert result.data == {"books": {"total": 1, "pages": 1, "items": [{"title": "Dune"}]}}
    params = dict(fake.requests[0].url.params)
    assert params["genre"] == "scifi" and params["sort"] == "-avg_rating" and params["limit"] == "5"


async def test_authorization_header_is_forwarded_to_rest(run, fake):
    fake.add("GET", "/users/me", {"id": 1, "email": "a@x.com", "name": "Ayush", "created_at": "t"})
    result = await run("{ me { name } }", token="abc123")
    assert result.data == {"me": {"name": "Ayush"}}
    assert fake.requests[0].headers["authorization"] == "Bearer abc123"


async def test_rest_error_becomes_graphql_error(run, fake):
    fake.add("GET", "/users/me", {"detail": "Not authenticated"}, status=401)
    result = await run("{ me { name } }")
    assert result.errors[0].message == "Not authenticated"
    assert result.errors[0].extensions == {"httpStatus": 401}


async def test_login_mutation_sends_form_data(run, fake):
    fake.add("POST", "/auth/login", {"access_token": "tok", "token_type": "bearer"})
    result = await run('mutation { login(email: "a@x.com", password: "pw") { accessToken tokenType } }')
    assert result.data == {"login": {"accessToken": "tok", "tokenType": "bearer"}}
    assert b"username=a%40x.com" in fake.requests[0].content    # form-encoded, not JSON


async def test_shelf_mutation_uses_enum_value_expected_by_rest(run, fake):
    fake.add("PUT", "/shelf/1", {"id": 1, "status": "reading", "current_page": 0, "book_id": 1})
    result = await run("mutation { setShelfStatus(bookId: 1, status: READING) { status currentPage } }", token="t")
    assert result.data == {"setShelfStatus": {"status": "READING", "currentPage": 0}}
    assert b'"reading"' in fake.requests[0].content            # REST sees "reading", not READING


async def test_invalid_enum_is_rejected_by_graphql_before_any_rest_call(run, fake):
    result = await run("mutation { setShelfStatus(bookId: 1, status: DONE) { status } }", token="t")
    assert result.errors and fake.requests == []


# ---------------------------------------------------------------- Phase 6: N+1
async def test_n_plus_one_is_fixed_authors_are_batched_into_one_call(run, fake):
    # 10 books written by 4 different authors (ids 1..4, repeated).
    books = [rest_book(id=i, author_id=(i % 4) + 1, title=f"B{i}") for i in range(1, 11)]
    fake.add("GET", "/books", {"items": books, "total": 10, "page": 1, "limit": 10, "pages": 1})
    fake.add("GET", "/authors", lambda r: [rest_author(i, f"Author {i}") for i in (1, 2, 3, 4)])

    result = await run("{ books { items { title author { name } } } }")

    assert result.errors is None
    assert [b["author"]["name"] for b in result.data["books"]["items"]][:2] == ["Author 2", "Author 3"]
    # Naive resolvers would make 1 + 10 = 11 REST calls. Now: list + ONE batched authors call.
    assert fake.paths == ["/books", "/authors"]
    assert sorted(dict(fake.requests[1].url.params)["ids"].split(",")) == ["1", "2", "3", "4"]  # deduplicated
    assert result.extensions == {"restCalls": 2}


async def test_loader_cache_repeated_key_is_fetched_once(run, fake):
    books = [rest_book(id=i, author_id=7) for i in range(1, 6)]     # all five share author 7
    fake.add("GET", "/books", {"items": books, "total": 5, "page": 1, "limit": 10, "pages": 1})
    fake.add("GET", "/authors", [rest_author(7, "Only One")])
    await run("{ books { items { author { name } } } }")
    assert dict(fake.requests[1].url.params)["ids"] == "7"


async def test_author_books_are_batched_per_author(run, fake):
    fake.add("GET", "/authors", [rest_author(1, "A"), rest_author(2, "B")])
    fake.add("GET", "/books", {
        "items": [rest_book(1, author_id=1, title="a1"), rest_book(2, author_id=2, title="b1"),
                  rest_book(3, author_id=1, title="a2")],
        "total": 3, "page": 1, "limit": 100, "pages": 1,
    })
    result = await run("{ authors { name books { title } } }")
    assert result.data["authors"][0]["books"] == [{"title": "a1"}, {"title": "a2"}]
    assert result.data["authors"][1]["books"] == [{"title": "b1"}]
    assert fake.paths == ["/authors", "/books"]      # 2 calls, not 1 + one per author


async def test_shelf_books_are_batched(run, fake):
    fake.add("GET", "/users/me", {"id": 1, "email": "a@x.com", "name": "A", "created_at": "t"})
    fake.add("GET", "/shelf", [
        {"id": i, "status": "reading", "current_page": 1, "book_id": i} for i in (1, 2, 3)
    ])
    fake.add("GET", "/books", {
        "items": [rest_book(i, title=f"B{i}") for i in (1, 2, 3)],
        "total": 3, "page": 1, "limit": 100, "pages": 1,
    })
    result = await run("{ me { shelf { book { title } } } }", token="t")
    assert [e["book"]["title"] for e in result.data["me"]["shelf"]] == ["B1", "B2", "B3"]
    assert fake.paths == ["/users/me", "/shelf", "/books"]


async def test_missing_batched_item_is_reported_not_crashed(run, fake):
    fake.add("GET", "/books", {"items": [rest_book(1, author_id=99)], "total": 1, "page": 1, "limit": 10, "pages": 1})
    fake.add("GET", "/authors", [])                       # author 99 does not exist
    result = await run("{ books { items { title author { name } } } }")
    assert result.errors                                  # a clear error for that field
