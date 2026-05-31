import { useRef, useEffect, useState } from 'react'
import './index.css'
import { useWorkflowStore } from './store/workflowStore'
import { useWorkflowSSE } from './hooks/useWorkflowSSE'
import ThinkingBlock from './components/ThinkingBlock'
import StreamingAnswer from './components/StreamingAnswer'
import AnswerMeta from './components/AnswerMeta'
import ServiceStatus from './components/ServiceStatus'
import HistorySidebar from './components/HistorySidebar'
import BacktrackTimeline from './components/BacktrackTimeline'

const SAMPLES = [
  '子痫前期急性重度高血压发作时，口服降压药和静脉用药哪个更安全有效？',
  '妊娠期高血压需要做哪些实验室检查？',
  '34周早产风险孕妇是否应给予产前糖皮质激素促胎肺成熟？',
]

export default function App() {
  const [question, setQuestion] = useState('')
  const bottomRef = useRef(null)
  const { startWorkflow, stopWorkflow } = useWorkflowSSE()

  const {
    status, stages, backtracks,
    answerTokens, answerComplete,
    finalResult, error, historyView,
    question: currentQuestion,
  } = useWorkflowStore()

  const isRunning = status === 'running'
  const showContent = status !== 'idle' || historyView

  useEffect(() => {
    if (answerTokens) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [answerTokens])

  function handleSubmit(e) {
    e?.preventDefault()
    if (!question.trim() || isRunning) return
    startWorkflow(question.trim())
    setQuestion('')
  }

  const finalRec = finalResult?.recommendation
  const finalAssess = finalResult?.assessment
  const directAnswer = finalResult?.direct_answer
  const totalElapsed = finalResult?.stats?.total_elapsed_s

  return (
    <div className="chat-layout">
      <HistorySidebar />

      <div className="chat-main">
        {/* ── Header ── */}
        <header className="chat-header">
          <div className="chat-brand">
            <span className="brand-name">TrueTruth</span>
            <span className="brand-sub">AI 临床决策支持</span>
          </div>
          <div className="chat-header-right">
            <ServiceStatus />
            {status === 'completed' && (
              <span className="status-badge status-ok">✓ 完成</span>
            )}
            {status === 'error' && (
              <span className="status-badge status-err">✗ 错误</span>
            )}
          </div>
        </header>

        {/* ── History notice ── */}
        {historyView && (
          <div className="history-notice">
            📂 查看历史记录 — 只读模式。在左侧栏点击「← 新问题」开始新查询。
          </div>
        )}

        {/* ── Scroll area ── */}
        <div className="chat-scroll">
          <div className="chat-content">

            {showContent && currentQuestion && (
              <div className="q-bubble-wrap">
                <div className="q-bubble">{currentQuestion}</div>
              </div>
            )}

            {error && <div className="error-box">⚠ {error}</div>}

            {backtracks.length > 0 && (
              <BacktrackTimeline backtracks={backtracks} />
            )}

            {showContent && (
              <ThinkingBlock stages={stages} totalElapsed={totalElapsed} />
            )}

            {answerTokens && (
              <div className="answer-wrap">
                <StreamingAnswer tokens={answerTokens} complete={answerComplete} />
                {answerComplete && (finalRec || directAnswer) && (
                  <AnswerMeta
                    rec={finalRec}
                    assess={finalAssess}
                    directAnswer={directAnswer}
                  />
                )}
              </div>
            )}

            {status === 'completed' && !answerTokens && (
              <div className="no-answer-box">
                未找到足够的循证医学证据。建议重新定义问题、扩大检索范围或咨询专家。
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* ── Input ── */}
        {!historyView && (
          <div className="chat-input-bar">
            <form className="chat-form" onSubmit={handleSubmit}>
              <input
                className="chat-input"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                placeholder="输入临床问题，如：妊娠期高血压需要做哪些实验室检查？"
                disabled={isRunning}
                list="sample-questions"
              />
              <datalist id="sample-questions">
                {SAMPLES.map((q, i) => <option key={i} value={q} />)}
              </datalist>
              {isRunning
                ? <button type="button" className="btn btn-stop" onClick={stopWorkflow}>■ 停止</button>
                : <button type="submit" className="btn" disabled={!question.trim()}>▶ 提问</button>
              }
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
