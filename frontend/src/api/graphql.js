/*
  graphql.js: the client for the GraphQL server.

  GraphQL over HTTP is just a POST with JSON to ONE url:
      { "query": "...", "variables": { ... } }
  and the reply is { "data": ..., "errors": [...], "extensions": {...} }.

  Usage:
      const data = await gql(`query Book($id: ID!) { book(id: $id) { title } }`, { id: 7 })
*/

import { logRequest } from '../netlog'
import { ApiError } from './rest'
import { getToken, notifyUnauthorized } from './token'

// "query Dashboard {" -> "Dashboard";  otherwise the first field name.
function operationLabel(query) {
  const named = query.match(/(?:query|mutation)\s+(\w+)/)
  if (named) return named[1]
  const first = query.match(/{\s*(\w+)/)
  return first ? first[1] : 'query'
}

export async function gql(query, variables = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`   // the gateway forwards this to REST

  const label = operationLabel(query)
  const started = performance.now()
  let response
  try {
    response = await fetch('/graphql', {
      method: 'POST',
      headers,
      body: JSON.stringify({ query, variables }),
    })
  } catch {
    logRequest({ kind: 'GraphQL', label, status: 0, ms: 0, bytes: 0 })
    throw new ApiError('Cannot reach the GraphQL server. Is it running?', 0)
  }
  const text = await response.text()
  const result = text ? JSON.parse(text) : {}
  logRequest({
    kind: 'GraphQL',
    label,
    status: response.status,
    ms: Math.round(performance.now() - started),
    bytes: text.length,
    // Our server reports how many REST calls the query caused (Phase 6).
    restCalls: result.extensions?.restCalls,
  })

  // GraphQL answers HTTP 200 even when something failed; problems are in "errors".
  if (result.errors?.length) {
    const first = result.errors[0]
    if (first.extensions?.httpStatus === 401 && token) notifyUnauthorized()
    throw new ApiError(first.message, first.extensions?.httpStatus || 400)
  }
  if (!response.ok) throw new ApiError(`GraphQL request failed (${response.status})`, response.status)
  return result.data
}
