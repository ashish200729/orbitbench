import { useEffect, useState } from 'react'
import { fetchLeaderboard, fetchResults } from './api/results'
import ScoreCard from './components/ScoreCard'
import Leaderboard from './components/Leaderboard'
import TaskBreakdown from './components/TaskBreakdown'
import RunHistory from './components/RunHistory'

export default function App() {
  const [entries, setEntries] = useState([])
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    Promise.all([fetchLeaderboard(), fetchResults()])
      .then(([lb, res]) => {
        setEntries(lb.entries || [])
        setResults(res)
        setError(null)
        setSelected((cur) => cur || (res[0] && res[0].run_id) || null)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 5000) // live refresh
    return () => clearInterval(id)
  }, [])

  const run = results.find((r) => r.run_id === selected) || results[0] || null

  return (
    <div className="app">
      <header>
        <div>
          <h1>LLM-Bench</h1>
          <span className="muted">Multi-language code-generation benchmark · pass@1 · scored /100</span>
        </div>
        <button onClick={load}>Refresh</button>
      </header>

      {error && (
        <div className="card err">
          Cannot reach API ({error}). Start it with <code>python api_server.py</code>.
        </div>
      )}

      <div className="grid">
        <div className="col">
          <ScoreCard score={run?.final_score} model={run?.model_id} />
          <RunHistory results={results} model={run?.model_id} />
        </div>
        <div className="col wide">
          <Leaderboard entries={entries} selectedRun={run?.run_id} onSelect={setSelected} />
          <TaskBreakdown run={run} />
        </div>
      </div>
    </div>
  )
}
