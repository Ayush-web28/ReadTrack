/*
  token.js: where the JWT is kept in the browser.

  We use localStorage so you stay logged in after a page refresh. TRADE-OFF: any
  JavaScript running on the page can read localStorage, so a cross-site-scripting
  (XSS) bug could steal the token. The more secure production pattern is an
  HttpOnly cookie set by the server (JavaScript cannot read those). For a learning
  project localStorage keeps the flow easy to follow.

  Every access is wrapped in try/catch because browsers can block storage
  (private windows, strict settings).
*/

const KEY = 'readtrack_token'

export function getToken() {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(KEY, token)
    else localStorage.removeItem(KEY)
  } catch {
    /* storage unavailable: the user will simply have to log in again */
  }
}

// api/rest.js calls this when the server answers 401 (token missing/expired).
// AuthProvider registers what should happen (log the user out).
let onUnauthorized = () => {}
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}
export function notifyUnauthorized() {
  onUnauthorized()
}
