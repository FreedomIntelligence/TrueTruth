import { useEffect, useRef } from 'react'

const AGENT_COLORS = { Ask:'log-ask', Acquire:'log-acquire', Appraise:'log-appraise', Apply:'log-apply', Assess:'log-assess', system:'log-system' }

function classifyLine(line) {
  if (line.includes('[FAST-PATH') || line.includes('[FAST-PATH')) return 'log-fastpath'
  if (line.startsWith('[TIMING]')) return 'log-timing'
  if (line.startsWith('[WARN]') || line.includes('[WARN]')) return 'log-warn'
  if (line.startsWith('[DEBUG]')) return 'log-dim'
  return null
}

export default function LogConsole({ logs }) {
  const bodyRef = useRef(null)

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [logs.length])

  return (
    <div className="log-console">
      <div className="log-header">
        <span>Real-time Logs</span>
        <span className="log-count">{logs.length}</span>
      </div>
      <div className="log-body" ref={bodyRef}>
        {logs.length === 0 && <span className="log-system">Waiting for workflow to start…</span>}
        {logs.map((entry, i) => {
          const agentCls = AGENT_COLORS[entry.agent] || 'log-system'
          const lineCls = classifyLine(entry.line)
          return (
            <div key={i} className={`log-line ${lineCls || agentCls}`}>
              {entry.line}
            </div>
          )
        })}
      </div>
    </div>
  )
}
