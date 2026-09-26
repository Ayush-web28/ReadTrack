"""
schema.py: the GraphQL schema (types + resolvers) for ReadTrack.

Read it in this order:
  1. TYPES      what things exist and how they connect (the "graph")
  2. QUERY      entry points for reading
  3. MUTATION   entry points for writing

STRAWBERRY basics used here:
  * @strawberry.type    a Python class becomes a GraphQL object type
  * a plain attribute   a field whose value is already known (title: str)
  * @strawberry.field   a method = a RESOLVER: code that runs ONLY if the
                        client asked for that field, and fetches its value
  * snake_case names    are exposed to clients as camelCase (page_count -> pageCount)
  * strawberry.Private  data we keep on the object but do NOT expose (e.g. author_id)

Every resolver receives `info`; info.context.rest is the REST client (rest_client.py).

N+1 FIX (Phase 6): relationship resolvers (Book.author, Author.books,
ShelfEntry.book) do not call REST directly. They ask a DataLoader
(info.context.loaders, see loaders.py) which BATCHES all lookups made during
one query into a single REST request. Book.reviews is still one call per book,
because each book needs its own "last N reviews" (see NOTES.md).
"""

from enum import Enum

import strawberry
from strawberry.types import Info

from .extensions import RestCallCounter

# ---------------------------------------------------------------- enums


@strawberry.enum
class ShelfStatus(Enum):
    # GraphQL enum NAMES are SHOUTY_CASE; the VALUES are what the REST API uses.
    TO_READ = "to-read"
    READING = "reading"
    FINISHED = "finished"


def _norm(text: str) -> str:
    """Normalize for comparing titles/names: ignore case and extra spaces."""
    return " ".join(text.casefold().split())


# ---------------------------------------------------------------- types
# Each class has a from_rest() helper that converts a REST JSON dict into the
# GraphQL type. REST uses snake_case keys; we map them onto our fields.


@strawberry.type
class Review:
    id: strawberry.ID
    rating: int
    comment: str | None
    created_at: str
    user_name: str

    @classmethod
    def from_rest(cls, d: dict) -> "Review":
        return cls(
            id=strawberry.ID(str(d["id"])),
            rating=d["rating"],
            comment=d["comment"],
            created_at=d["created_at"],
            user_name=d["user_name"],
        )


@strawberry.type
class Book:
    id: strawberry.ID
    title: str
    genre: str | None
    page_count: int | None
    published_year: int | None
    description: str | None
    avg_rating: float | None
    review_count: int
    author_id: strawberry.Private[int]   # kept for the resolver below, hidden from clients

    @classmethod
    def from_rest(cls, d: dict) -> "Book":
        return cls(
            id=strawberry.ID(str(d["id"])),
            title=d["title"],
            genre=d["genre"],
            page_count=d["page_count"],
            published_year=d["published_year"],
            description=d["description"],
            avg_rating=d["avg_rating"],
            review_count=d["review_count"],
            author_id=d["author_id"],
        )

    # ---- relationships: these are what make it a GRAPH ----
    @strawberry.field
    async def author(self, info: Info) -> "Author":
        # Runs only if the query includes `author { ... }`.
        # .load() does NOT call REST immediately: it queues the id, and the
        # loader fetches all queued ids together (GET /authors?ids=1,2,3).
        data = await info.context.loaders.author.load(self.author_id)
        return Author.from_rest(data)

    @strawberry.field
    async def reviews(self, info: Info, last: int = 10) -> list[Review]:
        # `last` is a field ARGUMENT: reviews(last: 2). Newest first from REST.
        data = await info.context.rest.get(f"/books/{self.id}/reviews", params={"limit": last})
        return [Review.from_rest(r) for r in data]


@strawberry.type
class Author:
    id: strawberry.ID
    name: str
    bio: str | None

    @classmethod
    def from_rest(cls, d: dict) -> "Author":
        return cls(id=strawberry.ID(str(d["id"])), name=d["name"], bio=d["bio"])

    @strawberry.field
    async def books(self, info: Info) -> list[Book]:
        data = await info.context.loaders.books_by_author.load(int(self.id))
        return [Book.from_rest(b) for b in data]


@strawberry.type
class BookPage:
    """Mirror of the REST pagination envelope."""

    items: list[Book]
    total: int
    page: int
    pages: int


@strawberry.type
class BookSearchResult:
    """One hit from Open Library (an EXTERNAL API), merged with OUR data."""

    open_library_key: str
    title: str
    authors: list[str]
    first_publish_year: int | None
    page_count: int | None
    cover_url: str | None
    # If this book already exists in our catalog, it is embedded here, so the
    # client gets our community rating (avgRating, reviewCount) in the same response.
    in_catalog: Book | None


@strawberry.type
class ShelfEntry:
    id: strawberry.ID
    status: ShelfStatus
    current_page: int
    book_id: strawberry.Private[int]

    @classmethod
    def from_rest(cls, d: dict) -> "ShelfEntry":
        return cls(
            id=strawberry.ID(str(d["id"])),
            status=ShelfStatus(d["status"]),   # "reading" -> ShelfStatus.READING
            current_page=d["current_page"],
            book_id=d["book_id"],
        )

    @strawberry.field
    async def book(self, info: Info) -> Book:
        data = await info.context.loaders.book.load(self.book_id)
        return Book.from_rest(data)


@strawberry.type
class Stats:
    to_read: int
    reading: int
    finished: int
    pages_read: int
    reviews_written: int
    average_rating_given: float | None


@strawberry.type
class User:
    id: strawberry.ID
    email: str
    name: str

    @classmethod
    def from_rest(cls, d: dict) -> "User":
        return cls(id=strawberry.ID(str(d["id"])), email=d["email"], name=d["name"])

    @strawberry.field
    async def shelf(self, info: Info, status: ShelfStatus | None = None) -> list[ShelfEntry]:
        params = {"status": status.value} if status else {}
        data = await info.context.rest.get("/shelf", params=params)
        return [ShelfEntry.from_rest(e) for e in data]

    @strawberry.field
    async def stats(self, info: Info) -> Stats:
        return Stats(**await info.context.rest.get("/users/me/stats"))


@strawberry.type
class Token:
    access_token: str
    token_type: str


# ---------------------------------------------------------------- queries
@strawberry.type
class Query:
    @strawberry.field
    async def book(self, info: Info, id: strawberry.ID) -> Book | None:
        # optional=True: a missing book is answered with null, not an error.
        data = await info.context.rest.get(f"/books/{id}", optional=True)
        return Book.from_rest(data) if data else None

    @strawberry.field
    async def books(
        self,
        info: Info,
        genre: str | None = None,
        author_id: strawberry.ID | None = None,
        search: str | None = None,
        sort: str = "title",
        page: int = 1,
        limit: int = 10,
    ) -> BookPage:
        # Only send the filters the client actually used.
        params = {"sort": sort, "page": page, "limit": limit}
        if genre:
            params["genre"] = genre
        if author_id:
            params["author_id"] = author_id
        if search:
            params["search"] = search
        data = await info.context.rest.get("/books", params=params)
        return BookPage(
            items=[Book.from_rest(b) for b in data["items"]],
            total=data["total"],
            page=data["page"],
            pages=data["pages"],
        )

    @strawberry.field
    async def search_books(self, info: Info, text: str, limit: int = 10) -> list[BookSearchResult]:
        """
        API COMPOSITION: one GraphQL field combines two different APIs.
          1. Open Library (external): find books matching the text
          2. ReadTrack REST (ours):   which of those do we already have, and how are they rated?
        """
        docs = await info.context.openlibrary.search(text, max(1, min(limit, 20)))
        if not docs:
            return []

        # ONE REST call for every title Open Library returned (?title=A&title=B...).
        titles = list({d["title"] for d in docs if d.get("title")})
        ours = await info.context.rest.get("/books", params={"title": titles, "limit": 100})

        # Matching by title alone could confuse two different books with the same
        # name, so we also compare author names. The author loader batches these
        # lookups into ONE call (the same DataLoader that fixed N+1).
        candidates = ours["items"]
        authors = await info.context.loaders.author.load_many([b["author_id"] for b in candidates])
        catalog: dict[tuple[str, str], dict] = {}
        for book, author in zip(candidates, authors):
            if author:
                catalog[(_norm(book["title"]), _norm(author["name"]))] = book

        results = []
        for d in docs:
            names = d.get("author_name") or []
            match = next(
                (
                    catalog[(_norm(d["title"]), _norm(n))]
                    for n in names
                    if (_norm(d["title"]), _norm(n)) in catalog
                ),
                None,
            )
            cover_id = d.get("cover_i")
            results.append(
                BookSearchResult(
                    open_library_key=d["key"],
                    title=d["title"],
                    authors=names,
                    first_publish_year=d.get("first_publish_year"),
                    page_count=d.get("number_of_pages_median"),
                    cover_url=f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
                    in_catalog=Book.from_rest(match) if match else None,
                )
            )
        return results

    @strawberry.field
    async def author(self, info: Info, id: strawberry.ID) -> Author | None:
        data = await info.context.rest.get(f"/authors/{id}", optional=True)
        return Author.from_rest(data) if data else None

    @strawberry.field
    async def authors(self, info: Info) -> list[Author]:
        data = await info.context.rest.get("/authors")
        return [Author.from_rest(a) for a in data]

    @strawberry.field
    async def me(self, info: Info) -> User:
        # Needs an Authorization header. REST answers 401 otherwise, which
        # becomes a GraphQL error, so we do not re-implement any auth here.
        return User.from_rest(await info.context.rest.get("/users/me"))


# ---------------------------------------------------------------- mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def register(self, info: Info, email: str, name: str, password: str) -> User:
        data = await info.context.rest.post(
            "/auth/register", json={"email": email, "name": name, "password": password}
        )
        return User.from_rest(data)

    @strawberry.mutation
    async def login(self, info: Info, email: str, password: str) -> Token:
        # The REST login expects FORM data (username/password), hence data=, not json=.
        data = await info.context.rest.post(
            "/auth/login", data={"username": email, "password": password}
        )
        return Token(access_token=data["access_token"], token_type=data["token_type"])

    @strawberry.mutation
    async def import_book(
        self,
        info: Info,
        title: str,
        author_name: str,
        page_count: int | None = None,
        published_year: int | None = None,
        genre: str | None = None,
    ) -> Book:
        """
        Add a book found through searchBooks to OUR catalog. Needs a login.
        Idempotent: importing something that already exists returns the existing book.
        """
        rest = info.context.rest
        # Find the author, or create them.
        found = await rest.get("/authors", params={"name": author_name})
        author = found[0] if found else await rest.post("/authors", json={"name": author_name})

        existing = await rest.get("/books", params={"title": [title], "author_id": author["id"]})
        if existing["items"]:
            return Book.from_rest(existing["items"][0])

        created = await rest.post(
            "/books",
            json={
                "title": title,
                "author_id": author["id"],
                "page_count": page_count,
                "published_year": published_year,
                "genre": genre,
            },
        )
        return Book.from_rest(created)

    @strawberry.mutation
    async def add_review(
        self, info: Info, book_id: strawberry.ID, rating: int, comment: str | None = None
    ) -> Review:
        data = await info.context.rest.post(
            f"/books/{book_id}/reviews", json={"rating": rating, "comment": comment}
        )
        return Review.from_rest(data)

    @strawberry.mutation
    async def set_shelf_status(
        self, info: Info, book_id: strawberry.ID, status: ShelfStatus
    ) -> ShelfEntry:
        data = await info.context.rest.put(f"/shelf/{book_id}", json={"status": status.value})
        return ShelfEntry.from_rest(data)

    @strawberry.mutation
    async def update_progress(self, info: Info, book_id: strawberry.ID, page: int) -> ShelfEntry:
        data = await info.context.rest.patch(
            f"/shelf/{book_id}/progress", json={"current_page": page}
        )
        return ShelfEntry.from_rest(data)

    @strawberry.mutation
    async def remove_from_shelf(self, info: Info, book_id: strawberry.ID) -> bool:
        await info.context.rest.delete(f"/shelf/{book_id}")
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation, extensions=[RestCallCounter])
