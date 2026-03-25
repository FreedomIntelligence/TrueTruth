import { useState } from 'react'
import './index.css'
import { useWorkflowStore } from './store/workflowStore'
import { useWorkflowSSE } from './hooks/useWorkflowSSE'
import WorkflowPipeline from './components/WorkflowPipeline'
import StageCard from './components/StageCard'
import LogConsole from './components/LogConsole'
import BacktrackTimeline from './components/BacktrackTimeline'
import RecommendationPanel from './components/RecommendationPanel'
import HistorySidebar from './components/HistorySidebar'
import { strengthClass } from './components/helpers'

const SAMPLE_QUESTIONS = [
  '子痫前期急性重度高血压发作时，口服降压药和静脉用药相比哪个更安全有效？',
  '妊娠期糖尿病血糖控制不达标时，二甲双胍和胰岛素如何选择？',
  '34周早产风险孕妇是否应该给予产前糖皮质激素促胎肺成熟？',
  '妊娠期高血压需要做哪些实验室检查？',
]

export default function App() {
  const [question, setQuestion] = useState('')
  const [selectedStage, setSelectedStage] = useState('Ask')
  const { startWorkflow, stopWorkflow } = useWorkflowSSE()

  const { status, stages, logs, backtracks, finalResult, error, historyView } = useWorkflowStore()

  const isRunning = status === 'running'

  function handleSubmit(e) {
    e?.preventDefault()
    if (!question.trim() || isRunning) return
    setSelectedStage('Ask')
    startWorkflow(question.trim())
  }

  function handleStop() {
    stopWorkflow()
  }

  const finalRec = finalResult?.recommendation
  const finalAssess = finalResult?.assessment
  const stats = finalResult?.stats

  return (
    <div className="app-layout">
      <HistorySidebar />
      <div className="app">
        {/* Header */}
        <div className="header">
          <div className="header-brand">
            <h1>TrueTruth</h1>
            <span className="header-subtitle">AI-Powered Clinical Evidence Synthesis</span>
          </div>
          <div className="header-badges">
            <span className="header-badge">Clinical Decision Support</span>
            {status === 'completed' && <span className="header-badge" style={{background:'var(--green-dim)',color:'#86efac'}}>✓ Complete</span>}
            {status === 'error' && <span className="header-badge" style={{background:'#7f1d1d',color:'#fca5a5'}}>✗ Error</span>}
          </div>
        </div>

        {historyView && (
          <div style={{background:'#1a1d27',border:'1px solid var(--border)',borderRadius:'var(--radius)',padding:'8px 14px',fontSize:12,color:'var(--text3)'}}>
            📂 Viewing history — read-only mode. Click "← New Question" in the sidebar to start a new run.
          </div>
        )}

        {/* Question input */}
        {!historyView && (
          <form className="question-form" onSubmit={handleSubmit}>
            <input
              className="question-input"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="输入临床问题，如：妊娠期高血压需要做哪些实验室检查？"
              disabled={isRunning}
              list="sample-questions"
            />
            <datalist id="sample-questions">
              {SAMPLE_QUESTIONS.map((q, i) => <option key={i} value={q} />)}
            </datalist>
            {isRunning
              ? <button type="button" className="btn btn-stop" onClick={handleStop}>■ Stop</button>
              : <button type="submit" className="btn" disabled={!question.trim()}>▶ Run</button>}
          </form>
        )}

        {/* Error */}
        {status === 'error' && error && (
          <div className="error-box">⚠ {error}</div>
        )}

        {/* Pipeline */}
        <WorkflowPipeline
          stages={stages}
          currentAgent={useWorkflowStore.getState().currentAgent}
          selectedStage={selectedStage}
          onSelectStage={setSelectedStage}
        />

        {/* Backtrack alerts */}
        {backtracks.length > 0 && <BacktrackTimeline backtracks={backtracks} />}

        {/* Main body: stage detail + log console */}
        <div className="main-body">
          <StageCard stageName={selectedStage} stage={stages[selectedStage]} />
          <LogConsole logs={logs} />
        </div>

        {/* Final recommendation */}
        {status === 'completed' && !finalRec && (
          <div className="final-banner" style={{borderColor:'var(--orange)'}}>
            <div className="final-banner-header" style={{color:'var(--orange)'}}>
              ⚠ Workflow Terminated
            </div>
            <div className="final-body" style={{padding:'10px 16px',fontSize:13,color:'var(--text2)'}}>
              未找到足够的循证医学证据。建议重新定义问题、扩大检索范围或咨询专家意见。
              {stats && (
                <div className="final-stats" style={{marginTop:10}}>
                  <div className="stat"><div className="stat-val">{stats.iteration_count}</div><div className="stat-label">Iterations</div></div>
                  <div className="stat"><div className="stat-val">{Math.round(stats.total_elapsed_s)}s</div><div className="stat-label">Total Time</div></div>
                </div>
              )}
            </div>
          </div>
        )}
        {finalRec && (
          <div className="final-banner">
            <div className="final-banner-header">
              🎯 Final Clinical Recommendation
              <span className={`rec-strength ${strengthClass(finalRec.strength)}`} style={{marginLeft:'auto',fontSize:11}}>
                {finalRec.strength}
              </span>
            </div>
            <div className="final-body">
              <RecommendationPanel rec={finalRec} assess={finalAssess} />
              {stats && (
                <div className="final-stats">
                  <div className="stat"><div className="stat-val">{stats.iteration_count}</div><div className="stat-label">Iterations</div></div>
                  <div className="stat"><div className="stat-val">{stats.backtrack_count}</div><div className="stat-label">Backtracks</div></div>
                  <div className="stat"><div className="stat-val">{Math.round(stats.total_elapsed_s)}s</div><div className="stat-label">Total Time</div></div>
                  {finalAssess && (
                    <div className="stat">
                      <div className="stat-val" style={{color: finalAssess.quality_score >= 0.8 ? 'var(--green)' : 'var(--orange)'}}>
                        {Math.round(finalAssess.quality_score * 100)}%
                      </div>
                      <div className="stat-label">Quality Score</div>
                    </div>
                  )}
                  {Object.entries(stats.agent_call_counts || {}).map(([agent, count]) => (
                    <div className="stat" key={agent}>
                      <div className="stat-val" style={{fontSize:16}}>{count}</div>
                      <div className="stat-label">{agent} calls</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
