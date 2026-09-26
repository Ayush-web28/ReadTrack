import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { rest } from '../api/rest'
import { useAuth } from '../auth'
import { STATUS_LABELS } from './ui'

/*
  Three buttons to put a book on your shelf. This is a WRITE, so it uses REST:
      PUT /shelf/{bookId}   body: { status }
  `ensureBookId` lets a caller create the book first when needed (the Search page
  imports a book from Open Library before shelving it).
*/
export default function ShelfButtons({ bookId, ensureBookId, current, onChange }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function choose(status) {
    if (!user) return navigate('/login')   // shelving needs an account
    setBusy(true)
    setError(null)
    try {
      const id = bookId ?? (await ensureBookId())
      await rest('PUT', `/shelf/${id}`, { json: { status } })
      onChange?.(status, id)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="btn-row">
        {Object.entries(STATUS_LABELS).map(([status, label]) => (
          <button
            key={status}
            className={`btn small ${current === status ? 'primary' : ''}`}
            disabled={busy}
            onClick={() => choose(status)}
          >
            {label}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
