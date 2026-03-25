export default function BacktrackTimeline({ backtracks }) {
  if (!backtracks?.length) return null
  return (
    <div>
      <p className="section-title">Backtrack Events ({backtracks.length})</p>
      <div className="backtrack-list">
        {backtracks.map((bt, i) => (
          <div key={i} className="backtrack-item">
            <div className="backtrack-header">
              ↩ {bt.from_stage} → {bt.to_stage}
            </div>
            <div className="backtrack-reason">{bt.reason?.slice(0, 200)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
