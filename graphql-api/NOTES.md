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
