/* ui.jsx: small reusable display pieces. */

// Shows a rating like ★★★★☆. Pass `value` (may be null when there are no reviews).
export function Stars({ value, count }) {
  if (value === null || value === undefined) return <span className="muted">No ratings yet</span>
  const filled = Math.round(value)
  return (
    <span className="stars" title={`${value} out of 5`}>
      {'★'.repeat(filled)}
      {'☆'.repeat(5 - filled)}
      <span className="muted"> {value.toFixed(1)}{count !== undefined ? ` (${count})` : ''}</span>
    </span>
  )
}

// A horizontal bar showing pages read out of the total.
export function ProgressBar({ current, total }) {
  const pct = total ? Math.min(100, Math.round((current / total) * 100)) : 0
  return (
    <div>
      <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="progress-text">{total ? `${current} / ${total} pages · ${pct}%` : `${current} pages`}</span>
    </div>
  )
}

export function Loading({ text = 'Loading…' }) {
  return <p className="muted center">{text}</p>
}

export function ErrorMessage({ error }) {
  if (!error) return null
  return <p className="error" role="alert">{error.message}</p>
}

// A placeholder "cover": a coloured tile with the title's first letter.
export function Cover({ title, url }) {
  if (url) return <img className="cover" src={url} alt={`Cover of ${title}`} loading="lazy" />
  const hue = [...title].reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % 360
  return (
    <div className="cover cover-fallback" style={{ background: `hsl(${hue} 45% 40%)` }} aria-hidden="true">
      {title.charAt(0).toUpperCase()}
    </div>
  )
}

export const STATUS_LABELS = { 'to-read': 'Want to read', reading: 'Reading', finished: 'Finished' }
