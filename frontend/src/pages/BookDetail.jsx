import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { gql } from '../api/graphql'
import { rest } from '../api/rest'
import { useAuth } from '../auth'
import ShelfButtons from '../components/ShelfButtons'
import { Cover, ErrorMessage, Loading, Stars } from '../components/ui'
import { useAsync } from '../useAsync'

/*
  BOOK DETAIL: the mixed-API page.
    READ  (GraphQL): the book, its author and its latest reviews in ONE request.
    WRITE (REST):    POST /books/{id}/reviews and PUT /shelf/{id}.
  After a write we call reload() to fetch fresh data.
*/
const BOOK = `
  query Book($id: ID!) {
    book(id: $id) {
      id title genre pageCount publishedYear description avgRating reviewCount
      author { name }
      reviews(last: 20) { id rating comment userName createdAt }
    }
  }
`

export default function BookDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const { data, error, loading, reload } = useAsync(() => gql(BOOK, { id }), [id])

  // Which shelf status does the current user have for this book? (REST read)
  const shelf = useAsync(
    () => (user ? rest('GET', '/shelf') : Promise.resolve([])),
    [user, id],
  )
  const myEntry = shelf.data?.find((e) => String(e.book_id) === id)

  if (loading && !data) return <Loading />
  if (error) return <ErrorMessage error={error} />
  const book = data.book
  if (!book) return <p className="card center">Book not found. <Link to="/catalog">Back to catalog</Link></p>

  return (
    <>
      <div className="detail-head card">
        <Cover title={book.title} />
        <div>
          <h1>{book.title}</h1>
          <p className="muted">
            by {book.author.name}
            {[book.genre, book.publishedYear, book.pageCount && `${book.pageCount} pages`].filter(Boolean).map((t) => ` · ${t}`).join('')}
          </p>
          <Stars value={book.avgRating} count={book.reviewCount} />
          {book.description && <p>{book.description}</p>}
          <ShelfButtons bookId={book.id} current={myEntry?.status} onChange={() => shelf.reload()} />
        </div>
      </div>

      <h2>Reviews</h2>
      <ReviewForm bookId={book.id} onSaved={reload} />
      {book.reviews.length === 0 && <p className="muted">No reviews yet. Be the first.</p>}
      {book.reviews.map((r) => (
        <article key={r.id} className="card review">
          <div><strong>{r.userName}</strong> <Stars value={r.rating} /></div>
          {r.comment && <p>{r.comment}</p>}
          <small className="muted">{new Date(r.createdAt).toLocaleDateString()}</small>
        </article>
      ))}
    </>
  )
}

function ReviewForm({ bookId, onSaved }) {
  const { user } = useAuth()
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (!user) return <p className="muted"><Link to="/login">Log in</Link> to write a review.</p>

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      // REST write. A second review of the same book gets 409 "already reviewed".
      await rest('POST', `/books/${bookId}/reviews`, { json: { rating: Number(rating), comment: comment || null } })
      setComment('')
      onSaved()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card review-form" onSubmit={submit}>
      <label>
        Your rating
        <select value={rating} onChange={(e) => setRating(e.target.value)}>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{'★'.repeat(n)} ({n})</option>)}
        </select>
      </label>
      <label>
        Comment (optional)
        <textarea rows="3" maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </label>
      <ErrorMessage error={error} />
      <button className="btn primary" disabled={busy}>Post review</button>
    </form>
  )
}
