"""
loaders.py: DataLoaders, the fix for the N+1 problem.

THE PROBLEM
  Query:  { books { items { title author { name } } } }
  Naive resolvers: 1 call for the books list, then Book.author runs ONCE PER
  BOOK  ->  1 + N REST calls (11 calls for 10 books).

THE FIX
  A DataLoader collects every .load(key) made during the same moment, then
  calls our batch function ONCE with all the keys together.
      author_loader.load(3)  ┐
      author_loader.load(5)  ├─>  batch function receives [3, 5, 3->deduped]  ->  ONE call:
      author_loader.load(3)  ┘                                                    GET /authors?ids=3,5
  It also CACHES within the request: asking for author 3 twice costs nothing extra.

RULES for a batch function
  * receives a list of keys, must return a list of results IN THE SAME ORDER
  * return None for a key that was not found

Loaders are created per request (see Context in main.py) so one user's cached
data can never leak into another user's request.
"""

from collections import defaultdict

from strawberry.dataloader import DataLoader

from .rest_client import RestClient

PAGE_SIZE = 100   # the REST API caps page size at 100


async def _fetch_all_books(rest: RestClient, **filters) -> list[dict]:
    """Read every page of GET /books for the given filters."""
    items: list[dict] = []
    page = 1
    while True:
        data = await rest.get("/books", params={**filters, "page": page, "limit": PAGE_SIZE})
        items += data["items"]
        if page >= data["pages"]:
            return items
        page += 1


def _csv(keys) -> str:
    return ",".join(str(k) for k in keys)


class Loaders:
    def __init__(self, rest: RestClient):
        self._rest = rest
        self.author = DataLoader(load_fn=self._load_authors)
        self.book = DataLoader(load_fn=self._load_books)
        self.books_by_author = DataLoader(load_fn=self._load_books_by_author)

    async def _load_authors(self, ids: list[int]) -> list[dict | None]:
        rows = await self._rest.get("/authors", params={"ids": _csv(ids)})
        by_id = {a["id"]: a for a in rows}
        return [by_id.get(i) for i in ids]        # same order as the keys

    async def _load_books(self, ids: list[int]) -> list[dict | None]:
        rows = await _fetch_all_books(self._rest, ids=_csv(ids))
        by_id = {b["id"]: b for b in rows}
        return [by_id.get(i) for i in ids]

    async def _load_books_by_author(self, author_ids: list[int]) -> list[list[dict]]:
        rows = await _fetch_all_books(self._rest, author_ids=_csv(author_ids))
        grouped: dict[int, list[dict]] = defaultdict(list)
        for b in rows:
            grouped[b["author_id"]].append(b)
        return [grouped[i] for i in author_ids]   # an author with no books gets []
