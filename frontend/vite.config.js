import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/*
  THE DEV PROXY
  The browser only ever talks to ONE origin (http://localhost:5173). Vite forwards:
      /api/...    ->  the REST API      (port 8000), with the "/api" prefix removed
      /graphql    ->  the GraphQL server (port 8001)
  Because the browser thinks everything is the same site, we never hit CORS errors.
  (In Docker, an nginx server does exactly the same job. See Phase 9.)
*/
const REST_URL = process.env.REST_URL || 'http://127.0.0.1:8000'
const GRAPHQL_URL = process.env.GRAPHQL_URL || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: REST_URL, rewrite: (path) => path.replace(/^\/api/, '') },
      '/graphql': { target: GRAPHQL_URL },
    },
  },
})
