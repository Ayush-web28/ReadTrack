import { useState, useSyncExternalStore } from 'react'
import { clearLog, getEntries, subscribe } from '../netlog'

/*
  The Network panel: a live list of every API call this page makes, labelled
  REST or GraphQL, with status, time and size. Open it while clicking around to
  SEE the difference: a REST page often makes several calls, while the GraphQL
  dashboard gets everything in one (and reports how many REST calls it caused).
*/
export default function NetworkPanel() {
  const [open, setOpen] = useState(false)
  // Re-renders whenever netlog.js changes.
  const entries = useSyncExternalStore(subscribe, getEntries)

  const restCount = entries.filter((e) => e.kind === 'REST').length
  const gqlCount = entries.length - restCount

  return (
    <aside className={`netpanel ${open ? 'open' : ''}`} aria-label="Network requests">
      <button className="netpanel-toggle" onClick={() => setOpen(!open)}>
        Network · {restCount} REST · {gqlCount} GraphQL {open ? '▾' : '▴'}
      </button>
      {open && (
        <div className="netpanel-body">
          <div className="netpanel-actions">
            <span className="muted">Latest {entries.length} requests</span>
            <button className="link" onClick={clearLog}>Clear</button>
          </div>
          {entries.length === 0 && <p className="muted">Nothing yet. Navigate around.</p>}
          <ul>
            {entries.map((e) => (
              <li key={e.id}>
                <span className={`tag ${e.kind === 'REST' ? 'tag-rest' : 'tag-gql'}`}>{e.kind}</span>
                <span className="net-label">{e.label}</span>
                <span className={`net-status ${e.status >= 400 || e.status === 0 ? 'bad' : ''}`}>{e.status || 'ERR'}</span>
                <span className="muted">{e.ms} ms · {formatBytes(e.bytes)}</span>
                {e.restCalls !== undefined && (
                  <span className="net-note">→ {e.restCalls} REST call{e.restCalls === 1 ? '' : 's'} behind it</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  )
}

function formatBytes(n) {
  return n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KB`
}
