import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { gql } from '../api/graphql'
import ShelfButtons from '../components/ShelfButtons'
import { Cover, ErrorMessage, Loading, Stars } from '../components/ui'

/*
  SEARCH: one GraphQL field, two APIs.
  `searchBooks` asks Open Library (an external API) for matches and merges in OUR
  data: if we already have the book, `inCatalog` carries our average rating.

  Shelving a book that is not in our catalog yet is a two-step flow:
     1. importBook  (GraphQL mutation)  -> creates it and returns its id
     2. PUT /shelf/{id} (REST)          -> puts it on your shelf
  (ShelfButtons handles step 2; `ensureBookId` below is step 1.)
*/
const SEARCH = `
  query Search($text: String!) {
    searchBooks(text: $text, limit: 12) {
      openLibraryKey title authors firstPublishYear pageCount coverUrl
      inCatalog { id avgRating reviewCount }
    }
  }
`

const IMPORT = `
  mutation Import($title: String!, $author: String!, $pages: Int, $year: Int) {
    importBook(title: $title, authorName: $author, pageCount: $pages, publishedYear: $year) { id }
  }
`

export default function Search() {
  const [text, setText] = useState('')
  const [results, setResults] = useState(null)   // null = nothing searched yet
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // DEBOUNCE: wait until the user stops typing for 500 ms before calling the API,
  // otherwise every keystroke would fire a request.
  useEffect(() => {
    const query = text.trim()
    if (query.length < 2) {
      setResults(null)
      return
    }
    let cancelled = false
    const timer = setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await gql(SEARCH, { text: query })
        if (!cancelled) setResults(data.searchBooks)
      } catch (e) {
        if (!cancelled) setError(e)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 500)
    return () => {
      cancelled = true       // a newer search started; ignore this one's answer
      clearTimeout(timer)
    }
  }, [text])

  return (
    <>
      <h1>Search books</h1>
      <input
        className="search-input"
        type="search"
        placeholder="Try “dune”, “pride and prejudice”, “tolkien”…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        autoFocus
      />

      {loading && <Loading text="Searching Open Library…" />}
      <ErrorMessage error={error} />
      {results && results.length === 0 && !loading && <p className="muted center">No results.</p>}

      <div className="grid">
        {(results || []).map((r) => (
          <ResultCard key={r.openLibraryKey} result={r} />
        ))}
      </div>
    </>
  )
}

function ResultCard({ result }) {
  const [catalogId, setCatalogId] = useState(result.inCatalog?.id ?? null)
  const [shelf, setShelf] = useState(null)

  // Step 1 of the flow above: make sure the book exists in OUR catalog.
  async function ensureBookId() {
    const data = await gql(IMPORT, {
      title: result.title,
      author: result.authors[0] || 'Unknown',
      pages: result.pageCount,
      year: result.firstPublishYear,
    })
    setCatalogId(data.importBook.id)
    return data.importBook.id
  }

  return (
    <article className="card book-card">
      <Cover title={result.title} url={result.coverUrl} />
      <div className="book-card-body">
        {catalogId ? (
          <Link to={`/books/${catalogId}`} className="book-title">{result.title}</Link>
        ) : (
          <span className="book-title">{result.title}</span>
        )}
        <div className="muted">{result.authors.join(', ') || 'Unknown author'}</div>
        <div className="muted">
          {[result.firstPublishYear, result.pageCount && `${result.pageCount} pages`].filter(Boolean).join(' · ')}
        </div>
        {result.inCatalog ? (
          <Stars value={result.inCatalog.avgRating} count={result.inCatalog.reviewCount} />
        ) : (
          // catalogId is set after a successful import, even though the search result is unchanged.
          <span className="muted">{catalogId ? 'Added to ReadTrack' : 'Not in ReadTrack yet'}</span>
        )}
        <ShelfButtons
          bookId={catalogId}
          ensureBookId={ensureBookId}
          current={shelf}
          onChange={setShelf}
        />
      </div>
    </article>
  )
}
