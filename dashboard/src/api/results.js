// Reads benchmark data from the local FastAPI server (api_server.py).
// Override the base URL with VITE_API_URL if needed.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const fetchLeaderboard = () => get('/api/leaderboard')
export const fetchResults = () => get('/api/results')
