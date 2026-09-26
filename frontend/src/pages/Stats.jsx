import { rest } from '../api/rest'
import { ErrorMessage, Loading } from '../components/ui'
import { useAsync } from '../useAsync'

/*
  STATS: plain REST. GET /users/me/stats returns a small fixed set of numbers
  computed by the database (counts, sums, an average). Note the snake_case keys:
  REST answers with the names the server uses (GraphQL would give camelCase).
*/
export default function Stats() {
  const { data, error, loading } = useAsync(() => rest('GET', '/users/me/stats'), [])

  if (loading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  const items = [
    ['Want to read', data.to_read],
    ['Currently reading', data.reading],
    ['Finished', data.finished],
    ['Pages read', data.pages_read],
    ['Reviews written', data.reviews_written],
    ['Average rating you give', data.average_rating_given ?? '–'],
  ]

  return (
    <>
      <h1>My stats</h1>
      <div className="stat-row">
        {items.map(([label, value]) => (
          <div key={label} className="card stat">
            <div className="stat-value">{value}</div>
            <div className="muted">{label}</div>
          </div>
        ))}
      </div>
    </>
  )
}
