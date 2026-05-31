import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

export default function RunHistory({ results, model }) {
  const data = results
    .filter((r) => !model || r.model_id === model)
    .slice()
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    .map((r, i) => ({ idx: i + 1, score: r.final_score, when: new Date(r.timestamp).toLocaleString() }))

  return (
    <div className="card">
      <h3>Run History{model ? ` — ${model}` : ''}</h3>
      {data.length === 0 ? (
        <p className="muted">No history yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ left: -10, right: 10 }}>
            <CartesianGrid stroke="#27272a" />
            <XAxis dataKey="idx" stroke="#a1a1aa" />
            <YAxis domain={[0, 100]} stroke="#a1a1aa" />
            <Tooltip
              contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }}
              labelFormatter={(i) => data[i - 1]?.when}
            />
            <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
