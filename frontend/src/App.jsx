import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'
import NetworkPanel from './components/NetworkPanel'
import Protected from './components/Protected'
import BookDetail from './pages/BookDetail'
import Catalog from './pages/Catalog'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Search from './pages/Search'
import Stats from './pages/Stats'

/*
  App = the page frame (top navigation) + the routes.
  Each <Route> maps a URL to a page component.

  Which API each page uses (open the Network panel at the bottom to watch):
    /login          REST      register + login
    /               GraphQL   dashboard: your whole shelf in ONE query  (login required)
    /search         GraphQL   Open Library search merged with our ratings; REST to shelve
    /catalog        REST      filterable, sortable, paginated list
    /books/:id      GraphQL   nested read; REST for reviews and shelf changes
    /stats          REST      aggregate numbers                            (login required)
*/
export default function App() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <>
      <header className="topbar">
        <NavLink to="/" className="brand">📚 ReadTrack</NavLink>
        <nav>
          <NavLink to="/" end>My shelf</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/catalog">Catalog</NavLink>
          <NavLink to="/stats">Stats</NavLink>
        </nav>
        <div className="user">
          {user ? (
            <>
              <span className="muted">Hi, {user.name}</span>
              <button className="btn small" onClick={() => { logout(); navigate('/login') }}>Log out</button>
            </>
          ) : (
            <NavLink to="/login" className="btn small primary">Log in</NavLink>
          )}
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Protected><Dashboard /></Protected>} />
          <Route path="/stats" element={<Protected><Stats /></Protected>} />
          <Route path="/search" element={<Search />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/books/:id" element={<BookDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<p className="center">Page not found.</p>} />
        </Routes>
      </main>

      <NetworkPanel />
    </>
  )
}
