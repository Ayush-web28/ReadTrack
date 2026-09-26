import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth'
import './styles.css'

// The entry point: mount <App> into <div id="root"> from index.html,
// wrapped in the router (page navigation) and the auth provider (who is logged in).
//
// NOTE: we deliberately do not wrap this in <StrictMode>. In development it runs every
// effect twice to help find bugs, which would make the Network panel show each API call
// twice and blur the REST-vs-GraphQL comparison this app is built to demonstrate.
createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <AuthProvider>
      <App />
    </AuthProvider>
  </BrowserRouter>,
)
