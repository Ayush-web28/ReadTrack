# GraphQL Gateway

## Run it (needs the REST API running on port 8000)
```
cd D:\AYUSH\API\readtrack\graphql-api
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app.main:app --port 8001 --reload
```
Open http://127.0.0.1:8001/graphql (GraphiQL: autocomplete + docs from the schema).
For protected fields, open the **Headers** tab and add `{"Authorization": "Bearer <token>"}`,
where the token comes from the `login` mutation.

## Reading order
1. `app/rest_client.py`: how we call REST, forward the auth header, and convert errors
2. `app/schema.py`: types, resolvers, queries, mutations
3. `app/main.py`: wiring (context per request, shared HTTP client)
4. `tests/`: uses a fake REST API to check behavior and count REST calls

---

# Phase 5: GraphQL layer

The gateway has **no database**. Every resolver calls the REST API, so business rules and
auth stay in one place.

## Try these in GraphiQL
```graphql
# One query, nested data, only the fields you name
{
  book(id: 1) {
    title
    avgRating
    author { name }
    reviews(last: 2) { rating userName }
  }
}
```
```graphql
mutation { login(email: "you@example.com", password: "secret123") { accessToken } }
```
```graphql
# needs the Authorization header
{
  me {
    name
    stats { finished pagesRead }
    shelf(status: READING) { currentPage book { title author { name } } }
  }
}
```
```graphql
mutation { addReview(bookId: 1, rating: 5, comment: "Great") { rating userName } }
mutation { setShelfStatus(bookId: 1, status: READING) { status } }
mutation { updateProgress(bookId: 1, page: 50) { status currentPage } }
```

## Concepts to notice in the code
- **Resolvers only run for requested fields.** Ask for just `title` and no other REST call happens
  (see `test_resolvers_only_run_for_requested_fields`).
- **HTTP 200 even for errors.** REST failures come back in the `errors` array.
- **Missing thing = null**, not an error (`book(id: 999)`).
- **Enums:** GraphQL says `READING`, REST expects `"reading"`; the mapping lives in `ShelfStatus`.
- **The naive part:** `Book.author` makes one REST call per book. Listing 10 books with authors
  costs 1 + 10 calls. That is the N+1 problem, fixed in Phase 6.

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

---

# Phase 7: External API (Open Library) and composition

New: `app/openlibrary.py`. Changed: `schema.py` (`searchBooks`, `importBook`), `main.py` (second HTTP client,
`Context` now carries `openlibrary`). REST gained `GET /books?title=A&title=B` (exact, repeatable) and
`GET /authors?name=` (exact) so matching and find-or-create stay cheap.

## searchBooks: one query, two APIs
```graphql
{
  searchBooks(text: "dune frank herbert", limit: 5) {
    title
    authors
    pageCount
    coverUrl
    inCatalog { id avgRating reviewCount }   # our data, merged in when we have the book
  }
}
```
What happens: 1 call to Open Library, then 1 REST call covering all the returned titles at once, then
1 batched authors call to confirm the author matches (a title alone can collide). Total: 3 calls however
many results.

## importBook: search result -> our catalog (needs Authorization header)
```graphql
mutation { importBook(title: "Dune", authorName: "Frank Herbert", pageCount: 608, genre: "scifi") { id title } }
```
Finds or creates the author, then the book. Calling it twice returns the same book.
After importing, `searchBooks` shows `inCatalog` filled in, and reviews change `avgRating`.

## Concepts to notice
- **Third-party APIs fail.** `openlibrary.py` sets a timeout and converts every failure into a clean
  GraphQL error rather than a crash. Tests cover an outage (`503`).
- **Ask only for what you need:** the `fields=` parameter keeps Open Library's response small.
- **Testing without the network:** both APIs are faked with `httpx.MockTransport`, so the whole suite
  runs offline in under a second.
- **Reused machinery:** the author DataLoader from Phase 6 also batches the matching step here.
