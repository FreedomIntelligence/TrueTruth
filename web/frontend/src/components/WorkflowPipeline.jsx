export default function WorkflowPipeline({ stages, currentAgent, onSelectStage, selectedStage }) {
  const STAGES = ['Ask', 'Acquire', 'Appraise', 'Apply', 'Assess']
  const ICONS = { Ask: '🎯', Acquire: '🔍', Appraise: '⚖️', Apply: '💊', Assess: '✅' }

  return (
    <div className="pipeline">
      {STAGES.map(name => {
        const stage = stages[name]
        const lastCall = stage.calls.at(-1)
        const eval_ = lastCall?.evaluation
        const score = eval_ ? eval_.overall_score : null
        const pass = eval_ ? eval_.pass_threshold : null
        const callCount = stage.calls.length
        const isActive = selectedStage === name

        return (
          <div
            key={name}
            className={`pipeline-stage st-${stage.status}${isActive ? ' active' : ''}`}
            onClick={() => onSelectStage(name)}
          >
            <div className="stage-arrow" />
            <div className="stage-name">
              <span>{ICONS[name]}</span>
              <span>{name}</span>
              {callCount > 1 && <span className="call-badge">×{callCount}</span>}
              {stage.status === 'running' && <span className="call-badge" style={{background:'#1d4ed8',color:'#93c5fd'}}>⏳</span>}
            </div>
            <div className="stage-sub">
              {lastCall?.elapsed_s != null
                ? `${lastCall.elapsed_s}s`
                : stage.status === 'pending' ? 'waiting' : stage.status}
            </div>
            {score !== null && (
              <div className="score-bar-wrap">
                <div
                  className={`score-bar-fill ${pass ? 'score-pass' : 'score-fail'}`}
                  style={{ width: `${Math.round(score * 100)}%` }}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
