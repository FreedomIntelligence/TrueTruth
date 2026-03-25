import InfoTooltip from './InfoTooltip'

const JUDGE_SCORE_TIP = '独立评估模块对当前阶段输出质量的打分，跨多个维度加权平均'

export default function JudgeScorePanel({ evaluation }) {
  if (!evaluation) return <p className="placeholder" style={{padding:'12px'}}>Awaiting judge…</p>

  const { overall_score, pass_threshold, dimension_scores, issues, summary } = evaluation
  const pct = Math.round(overall_score * 100)

  const severityOrder = { critical: 0, major: 1, minor: 2 }
  const sorted = [...(issues || [])].sort((a, b) =>
    (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9)
  )

  return (
    <div>
      <div className="judge-score">
        <div className={`judge-overall ${pass_threshold ? 'pass' : 'fail'}`}>
          {pct}%
        </div>
        <div className="dim-list">
          {Object.entries(dimension_scores || {}).map(([k, v]) => (
            <div className="dim-row" key={k}>
              <span className="dim-label">{k.replace(/_/g,' ')}</span>
              <div className="dim-bar">
                <div className="dim-fill" style={{width:`${Math.round(v*100)}%`, background: v>=0.7?'var(--green)':v>=0.5?'var(--orange)':'var(--red)'}} />
              </div>
              <span className="dim-val">{(v*100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{display:'flex',alignItems:'center',gap:4,marginBottom:4}}>
        <p style={{fontSize:'12px',color:'var(--text2)',margin:0}}>{summary}</p>
        <InfoTooltip text={JUDGE_SCORE_TIP} />
      </div>
      <p style={{fontSize:'11px',color:'var(--text3)',marginBottom:6}}>总分为各维度加权平均；Minor 问题不大幅影响分数，但仍列出供参考。</p>

      {sorted.length > 0 && (
        <div className="issue-list">
          <div style={{fontSize:'11px',color:'var(--text3)',marginBottom:4}}>
            {['critical','major','minor'].map(sev => {
              const cnt = sorted.filter(i => i.severity === sev).length
              return cnt > 0 ? `${cnt} ${sev.charAt(0).toUpperCase()+sev.slice(1)}` : null
            }).filter(Boolean).join(' · ')}
          </div>
          {sorted.map((issue, i) => (
            <div key={i} className={`issue-item issue-${issue.severity}`}>
              <span className="issue-label">{issue.severity}</span>
              <span style={{color:'var(--text3)',fontSize:'10px',marginRight:4}}>[{issue.dimension?.replace(/_/g,' ')}]</span>
              {issue.description}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
