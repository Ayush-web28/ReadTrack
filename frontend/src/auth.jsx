/*
  auth.jsx: who is logged in, available to every component.

  React CONTEXT = a way to share a value with the whole component tree without
  passing it down through every level. Any component can call useAuth() to get
  { user, login, register, logout, loading }.

  Flow:
    login()  -> REST POST /auth/login (form) -> JWT -> saved in localStorage
             -> REST GET /users/me           -> the user object
    On page load, if a token is already saved, we call /users/me to restore the session.
    If the server ever answers 401, api/rest.js tells us and we log out.
*/

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { rest } from './api/rest'
import { getToken, setToken, setUnauthorizedHandler } from './api/token'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))   // only "loading" if a token exists

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  // Restore the session on first load.
  useEffect(() => {
    setUnauthorizedHandler(logout)
    if (!getToken()) return
    rest('GET', '/users/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [logout])

  const login = useCallback(async (email, password) => {
    // The REST login expects FORM fields named "username" and "password".
    const { access_token } = await rest('POST', '/auth/login', {
      form: { username: email, password },
    })
    setToken(access_token)
    setUser(await rest('GET', '/users/me'))
  }, [])

  const register = useCallback(
    async (email, name, password) => {
      await rest('POST', '/auth/register', { json: { email, name, password } })
      await login(email, password)   // sign in straight away
    },
    [login],
  )

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
