"""Tests for the gateway's queries and mutations (against a fake REST API)."""

from .conftest import rest_author, rest_book


async def test_client_chooses_fields_and_relationships_are_resolved(run, fake):
    fake.add("GET", "/books/1", rest_book())
    fake.add("GET", "/authors/1", rest_author())
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
