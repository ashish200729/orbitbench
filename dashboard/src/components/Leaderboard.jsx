// All model runs sorted by score (the API already returns them sorted).
const color = (s) => (s >= 80 ? '#22c55e' : s >= 50 ? '#eab308' : '#ef4444')

export default function Leaderboard({ entries, selectedRun, onSelect }) {
  return (
    <div className="card">
      <h3>Leaderboard</h3>
      {!entries || entries.length === 0 ? (
        <p className="muted">No runs yet. Run one with <code>python -m cli.main run --model ...</code></p>
      ) : (
        <table>
          <thead>
            <tr><th>#</th><th>Model</th><th>Score</th><th>Run ID</th><th>When</th></tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr
                key={e.run_id + i}
                className={e.run_id === selectedRun ? 'sel' : ''}
                onClick={() => onSelect && onSelect(e.run_id)}
              >
                <td>{i + 1}</td>
                <td>{e.model_id}</td>
                <td>
                  <div className="bar">
                    <div className="bar-fill" style={{ width: `${e.score}%`, background: color(e.score) }} />
                  </div>
                  <span className="bar-val">{e.score}</span>
                </td>
                <td className="mono">{e.run_id}</td>
                <td className="muted">{new Date(e.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
