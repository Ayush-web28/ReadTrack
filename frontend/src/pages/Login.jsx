import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { ErrorMessage } from '../components/ui'

/* Login / register page. Uses REST (see auth.jsx). */
export default function Login() {
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')            // 'login' or 'register'
  const [form, setForm] = useState({ email: '', name: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />         // already logged in

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  async function submit(e) {
    e.preventDefault()                                  // stop the browser's own form reload
    setBusy(true)
    setError(null)
    try {
      if (mode === 'login') await login(form.email, form.password)
      else await register(form.email, form.name, form.password)
      navigate('/')
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card auth-card" onSubmit={submit}>
      <h1>{mode === 'login' ? 'Log in' : 'Create your account'}</h1>

      <label>
        Email
        <input type="email" required value={form.email} onChange={update('email')} autoComplete="email" />
      </label>
      {mode === 'register' && (
        <label>
          Name
          <input required maxLength={100} value={form.name} onChange={update('name')} autoComplete="name" />
        </label>
      )}
      <label>
        Password
        <input
          type="password"
          required
          minLength={mode === 'register' ? 8 : undefined}
          maxLength={72}
          value={form.password}
          onChange={update('password')}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
        />
        {mode === 'register' && <small className="muted">At least 8 characters.</small>}
      </label>

      <ErrorMessage error={error} />
      <button className="btn primary" disabled={busy}>
        {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Sign up'}
      </button>

      <p className="muted center">
        {mode === 'login' ? 'New here?' : 'Already have an account?'}{' '}
        <button type="button" className="link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}>
          {mode === 'login' ? 'Create an account' : 'Log in'}
        </button>
      </p>
    </form>
  )
}
