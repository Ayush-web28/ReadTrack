import { useState } from 'react'
import { Link } from 'react-router-dom'
import { rest } from '../api/rest'
import { Cover, ErrorMessage, Loading, Stars } from '../components/ui'
import { useAsync } from '../useAsync'

/*
  CATALOG: plain REST. A flat list with filtering, sorting and pagination is
  exactly what REST does well. GET /books?search=&sort=&page=&limit= returns
  { items, total, page, pages }, and responses like this are easy for browsers
  and CDNs to cache.
*/
const SORTS = [
  { value: 'title', label: 'Title A-Z' },
  { value: '-avg_rating', label: 'Highest rated' },
  { value: '-review_count', label: 'Most reviewed' },
  { value: '-published_year', label: 'Newest' },
]

export default function Catalog() {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('title')
  const [page, setPage] = useState(1)

  // Re-fetches automatically whenever search, sort or page change.
  const { data, error, loading } = useAsync(
    () => rest('GET', '/books', { params: { search, sort, page, limit: 8 } }),
    [search, sort, page],
  )

  return (
    <>
      <h1>Catalog</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Filter by title…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}   // back to page 1 on a new filter
        />
        <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1) }} aria-label="Sort by">
          {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      <ErrorMessage error={error} />
      {loading && !data && <Loading />}
      {data && data.items.length === 0 && (
        <p className="card center">Nothing here yet. Use <Link to="/search">Search</Link> to add books.</p>
      )}

      <div className="grid">
        {data?.items.map((book) => (
          <article key={book.id} className="card book-card">
            <Cover title={book.title} />
            <div className="book-card-body">
              <Link to={`/books/${book.id}`} className="book-title">{book.title}</Link>
              <div className="muted">{[book.genre, book.published_year].filter(Boolean).join(' · ')}</div>
              <Stars value={book.avg_rating} count={book.review_count} />
            </div>
          </article>
        ))}
      </div>

      {data && data.pages > 1 && (
        <div className="pager">
          <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</button>
          <span className="muted">Page {data.page} of {data.pages} · {data.total} books</span>
          <button className="btn small" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next →</button>
        </div>
      )}
    </>
  )
}
