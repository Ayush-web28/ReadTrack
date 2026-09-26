import { useState } from 'react'
import { Link } from 'react-router-dom'
import { gql } from '../api/graphql'
import { rest } from '../api/rest'
import { Cover, ErrorMessage, Loading, ProgressBar, Stars } from '../components/ui'
import { useAsync } from '../useAsync'

/*
  DASHBOARD: reads with GraphQL, writes with REST.

  This ONE query returns the user, their stats, their whole shelf, and for every
  book its author and average rating. With REST this screen would need a request
  for the user, one for stats, one for the shelf, and one per book for its author.
  Watch the Network panel: a single GraphQL entry, with the REST calls behind it.

  GraphQL enum values arrive in SHOUTY_CASE (READING); we lowercase them for display.
*/
const DASHBOARD = `
  query Dashboard {
    me {
      stats { toRead reading finished pagesRead reviewsWritten }
      shelf {
        id status currentPage
        book { id title pageCount avgRating reviewCount author { name } }
      }
    }
  }
`

const COLUMNS = [
  { status: 'READING', title: 'Currently reading' },
  { status: 'TO_READ', title: 'Want to read' },
  { status: 'FINISHED', title: 'Finished' },
]

export default function Dashboard() {
  const { data, error, loading, reload } = useAsync(() => gql(DASHBOARD), [])

  if (loading && !data) return <Loading text="Loading your shelf…" />
  if (error) return <ErrorMessage error={error} />
  const { stats, shelf } = data.me

  return (
    <>
      <h1>My shelf</h1>
      <div className="stat-row">
        <Stat label="Want to read" value={stats.toRead} />
        <Stat label="Reading" value={stats.reading} />
        <Stat label="Finished" value={stats.finished} />
        <Stat label="Pages read" value={stats.pagesRead} />
      </div>

      {shelf.length === 0 && (
        <p className="card center">
          Your shelf is empty. <Link to="/search">Search for a book</Link> or browse the{' '}
          <Link to="/catalog">catalog</Link>.
        </p>
      )}

      {COLUMNS.map(({ status, title }) => {
        const entries = shelf.filter((e) => e.status === status)
        if (entries.length === 0) return null
        return (
          <section key={status}>
            <h2>{title} <span className="muted">({entries.length})</span></h2>
            <div className="grid">
              {entries.map((entry) => (
                <ShelfCard key={entry.id} entry={entry} onChanged={reload} />
              ))}
            </div>
          </section>
        )
      })}
    </>
  )
}

function Stat({ label, value }) {
  return (
    <div className="card stat">
      <div className="stat-value">{value}</div>
      <div className="muted">{label}</div>
    </div>
  )
}

function ShelfCard({ entry, onChanged }) {
  const { book } = entry
  const [page, setPage] = useState(entry.currentPage)
  const [error, setError] = useState(null)

  // WRITES go through REST: PATCH /shelf/{bookId}/progress
  async function saveProgress(e) {
    e.preventDefault()
    setError(null)
    try {
      await rest('PATCH', `/shelf/${book.id}/progress`, { json: { current_page: Number(page) } })
      onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  async function remove() {
    try {
      await rest('DELETE', `/shelf/${book.id}`)
      onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <article className="card book-card">
      <Cover title={book.title} />
      <div className="book-card-body">
        <Link to={`/books/${book.id}`} className="book-title">{book.title}</Link>
        <div className="muted">{book.author.name}</div>
        <Stars value={book.avgRating} count={book.reviewCount} />
        <ProgressBar current={entry.currentPage} total={book.pageCount} />

        {entry.status !== 'FINISHED' && (
          <form className="inline-form" onSubmit={saveProgress}>
            <input
              type="number"
              min="0"
              max={book.pageCount || undefined}
              value={page}
              onChange={(e) => setPage(e.target.value)}
              aria-label="Current page"
            />
            <button className="btn small">Update page</button>
          </form>
        )}
        <button className="link danger" onClick={remove}>Remove</button>
        {error && <p className="error">{error}</p>}
      </div>
    </article>
  )
}
