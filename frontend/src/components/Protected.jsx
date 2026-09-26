import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Loading } from './ui'

// Wrap a page in <Protected> to require login; anonymous visitors are sent to /login.
export default function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading text="Checking your session…" />
  return user ? children : <Navigate to="/login" replace />
}
