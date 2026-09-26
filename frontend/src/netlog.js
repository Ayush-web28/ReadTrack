/*
  netlog.js: a tiny "store" that remembers the latest network requests, so the
  Network panel (components/NetworkPanel.jsx) can show them.

  Both API clients (api/rest.js and api/graphql.js) call logRequest() after every
  request. React components subscribe to changes through useSyncExternalStore.
*/

let entries = []           // newest first
let counter = 0
const listeners = new Set()

export function logRequest(entry) {
  counter += 1
  // Always create a NEW array: React detects changes by comparing references.
  entries = [{ id: counter, ...entry }, ...entries].slice(0, 30)
  listeners.forEach((notify) => notify())
}

export function clearLog() {
  entries = []
  listeners.forEach((notify) => notify())
}

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)   // unsubscribe function
}

export function getEntries() {
  return entries
}
