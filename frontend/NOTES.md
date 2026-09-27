# Phase 8: React Frontend

React 19 + Vite + React Router, plain JavaScript, hand-written CSS (light and dark themes).

## Run it (all three servers must be running)
```
# terminal 1: REST API
cd D:\AYUSH\API\readtrack\rest-api
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# terminal 2: GraphQL gateway
cd D:\AYUSH\API\readtrack\graphql-api
.venv\Scripts\python -m uvicorn app.main:app --port 8001

# terminal 3: frontend
cd D:\AYUSH\API\readtrack\frontend
npm install
npm run dev
```
Open http://localhost:5173, create an account, and try Search -> "Reading" on a book.

## The dev proxy (why there is no CORS setup)
`vite.config.js` forwards `/api/*` to the REST API and `/graphql` to the gateway. The browser only
ever talks to `localhost:5173`, so the browser's cross-origin rules never apply.

## Which API each page uses
| Page | Reads | Writes |
|---|---|---|
| `/login` | | REST: register, login (`/auth/*`) |
| `/` My shelf | GraphQL: user + stats + shelf + books + authors in ONE query | REST: `PATCH /shelf/{id}/progress`, `DELETE /shelf/{id}` |
| `/search` | GraphQL: `searchBooks` (Open Library merged with our ratings) | GraphQL `importBook`, then REST `PUT /shelf/{id}` |
| `/catalog` | REST: `GET /books` with search, sort, pagination | |
| `/books/:id` | GraphQL: book + author + reviews; REST: my shelf entry | REST: `POST /books/{id}/reviews`, `PUT /shelf/{id}` |
| `/stats` | REST: `GET /users/me/stats` | |

The rule of thumb used: **GraphQL for reads that need nested data, REST for writes and flat lists.**

## The Network panel (bottom right)
Every API call is logged and labelled REST or GraphQL with status, time and size. GraphQL entries show
how many REST calls the gateway made behind them. The My shelf page is one `Dashboard` request that
costs the gateway 5 REST calls (user, stats, shelf, and one batched books call and one batched authors
call). Without DataLoader (Phase 6) it would be one call per shelved book and per author on top.

## Reading order
1. `src/api/rest.js` and `src/api/graphql.js`: how requests are made (auth header, errors, logging)
2. `src/api/token.js` and `src/auth.jsx`: login, session restore, logout on expiry
3. `src/useAsync.js`: the small data-loading hook every page uses
4. `src/pages/Dashboard.jsx`, `Search.jsx`, `BookDetail.jsx`: the GraphQL + REST mix
5. `src/components/NetworkPanel.jsx` and `src/netlog.js`: how the panel works

## Things to know
- **Token storage:** the JWT lives in `localStorage` so a refresh keeps you logged in. The trade-off
  (readable by any script on the page) is explained in `src/api/token.js`.
- **Open Library can be slow.** Searches sometimes take several seconds; the UI shows "Searching…".
- **No StrictMode:** deliberately removed so dev mode does not double every API call in the Network
  panel (see comment in `src/main.jsx`).
- **Not built yet:** editing or deleting your review from the UI (the REST endpoints exist), and
  frontend tests.

---

# Phase 10: Deploy to Render

Changed: `src/api/rest.js` and `src/api/graphql.js`.

## What changed and why
Locally (and in Docker), this app calls relative paths (`/api/...`, `/graphql`) and something else
in front of it (the Vite dev proxy, or nginx) forwards them to the real servers — the browser only
ever sees one origin, so CORS never comes up. On Render, the frontend is a static site with its own
`onrender.com` URL, separate from the REST API and GraphQL gateway, so it now calls them directly by
full URL:
```js
const BASE = import.meta.env.VITE_REST_URL || '/api'          // rest.js
const GRAPHQL_URL = import.meta.env.VITE_GRAPHQL_URL || '/graphql'   // graphql.js
```
`VITE_*` variables are read by Vite **at build time** and baked into the built JavaScript — there is no
runtime "settings" step. `render.yaml` sets both for the Render build; leaving them unset (as in local
dev) keeps the old relative-path behavior exactly as before.

## Verified
Built with `VITE_REST_URL`/`VITE_GRAPHQL_URL` pointing at two other `localhost` ports and served the
build with `vite preview` on a third port, so the browser treated all three as genuinely different
origins — the same situation as three separate Render services. Registering an account (REST, a
cross-origin `POST`) and loading the dashboard (GraphQL, a cross-origin `POST`) both worked with no
console/CORS errors. An actual Render deploy was not tested (no account was available while building
this); see the repo root `README.md` for the deploy steps and what to check afterward.
