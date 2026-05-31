import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from 'recharts'

const color = (s) => (s >= 80 ? '#22c55e' : s >= 50 ? '#eab308' : '#ef4444')

export default function TaskBreakdown({ run }) {
  if (!run) return null
  const data = run.task_results.map((t) => ({
    name: `${t.task_id.replace('task_', '#')} ${t.language}`,
    score: t.task_score.score,
    pass: t.task_score.pass_rate,
    title: t.task_title,
  }))
  return (
    <div className="card">
      <h3>Per-Task Breakdown</h3>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={data} layout="vertical" margin={{ left: 30, right: 20 }}>
          <XAxis type="number" domain={[0, 100]} stroke="#a1a1aa" />
          <YAxis type="category" dataKey="name" width={120} stroke="#a1a1aa" />
          <Tooltip
            contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }}
            formatter={(v, _n, p) => [`${v}/100 (${p.payload.pass})`, p.payload.title]}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => <Cell key={i} fill={color(d.score)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
