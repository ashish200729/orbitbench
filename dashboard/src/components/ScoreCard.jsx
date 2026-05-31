// Big final-score display with a circular (radial) progress ring.
const color = (s) => (s >= 80 ? '#22c55e' : s >= 50 ? '#eab308' : '#ef4444')

export default function ScoreCard({ score, model }) {
  const pct = Math.max(0, Math.min(100, score ?? 0))
  const r = 70
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct / 100)
  return (
    <div className="card score-card">
      <h3>Final Score</h3>
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle cx="90" cy="90" r={r} stroke="#27272a" strokeWidth="14" fill="none" />
        <circle
          cx="90" cy="90" r={r} stroke={color(pct)} strokeWidth="14" fill="none"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
          transform="rotate(-90 90 90)"
        />
        <text x="90" y="86" textAnchor="middle" className="score-num">{pct.toFixed(1)}</text>
        <text x="90" y="110" textAnchor="middle" className="score-unit">/ 100</text>
      </svg>
      <div className="muted">{model || 'No run selected'}</div>
    </div>
  )
}
