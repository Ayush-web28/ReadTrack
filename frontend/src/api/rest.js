/*
  rest.js: the client for the REST API.

  Usage:
      rest('GET',  '/books', { params: { genre: 'scifi', page: 2 } })
      rest('POST', '/books/7/reviews', { json: { rating: 5 } })
      rest('POST', '/auth/login', { form: { username, password } })

  BASE URL: in development and in the Docker/nginx setup, requests go to the
  relative path "/api/..." and something else (the Vite dev proxy, or nginx)
  forwards them to the real REST server; that avoids CORS entirely, since the
  browser only ever sees one origin. On Render, the frontend and the REST API
  are two different origins, so we call the REST API directly instead, using
  its full URL from the VITE_REST_URL build-time environment variable (the
  REST API allows this origin via CORS; see rest-api/app/main.py).
*/

import { logRequest } from '../netlog'
import { getToken, notifyUnauthorized } from './token'

const BASE = import.meta.env.VITE_REST_URL || '/api'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

// FastAPI reports "detail" as a string (our own errors) or as a list (validation errors).
function readableError(body, fallback) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
  }
  return fallback
}

export async function rest(method, path, { json, form, params } = {}) {
  // Build the URL, skipping empty query parameters.
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  const qs = query.toString()
  const url = `${BASE}${path}${qs ? `?${qs}` : ''}`

  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`   // how the JWT travels

  let body
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    body = new URLSearchParams(form)   // browser sets the form Content-Type itself
  }

  const started = performance.now()
  let response
  try {
    response = await fetch(url, { method, headers, body })
  } catch {
    logRequest({ kind: 'REST', label: `${method} ${path}`, status: 0, ms: 0, bytes: 0 })
    throw new ApiError('Cannot reach the server. Is the REST API running?', 0)
  }
  const text = await response.text()
  logRequest({
    kind: 'REST',
    label: `${method} ${path}`,
    status: response.status,
    ms: Math.round(performance.now() - started),
    bytes: text.length,
  })

  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    // A 401 on a request that carried a token means the token expired: log out.
    if (response.status === 401 && token) notifyUnauthorized()
    throw new ApiError(readableError(data, `Request failed (${response.status})`), response.status)
  }
  return data
}
