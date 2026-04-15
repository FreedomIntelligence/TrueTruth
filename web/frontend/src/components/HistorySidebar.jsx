import { useState, useEffect } from 'react'
import { useWorkflowStore } from '../store/workflowStore'
import { loadHistory } from '../store/workflowStore'

const SIDEBAR_KEY = 'truetruth_sidebar_open'

function relativeTime(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function StatusIcon({ status }) {
  if (status === 'completed') return <span style={{color:'var(--green)'}}>✓</span>
  if (status === 'terminated') return <span style={{color:'var(--orange)'}}>⚠</span>
  return <span style={{color:'var(--red)'}}>✗</span>
}

export default function HistorySidebar() {
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(SIDEBAR_KEY) !== 'false' } catch { return true }
  })
  const [history, setHistory] = useState([])
  const loadFromHistory = useWorkflowStore(s => s.loadFromHistory)
  const exitHistoryView = useWorkflowStore(s => s.exitHistoryView)
  const historyView = useWorkflowStore(s => s.historyView)

  useEffect(() => {
    setHistory(loadHistory())
  }, [])

  // Refresh history list when a new run finishes
  const status = useWorkflowStore(s => s.status)
  useEffect(() => {
    if (status === 'completed' || status === 'error') {
      setHistory(loadHistory())
    }
  }, [status])

  function toggle() {
    const next = !open
    setOpen(next)
    try { localStorage.setItem(SIDEBAR_KEY, String(next)) } catch {}
  }

  return (
    <div className={`history-sidebar ${open ? 'open' : 'closed'}`}>
      <button className="sidebar-toggle" onClick={toggle} title={open ? 'Collapse sidebar' : 'Expand sidebar'}>
        ☰
      </button>

      {open && (
        <div className="sidebar-content">
          <div className="sidebar-header">History</div>
          {historyView && (
            <button className="sidebar-new-btn" onClick={exitHistoryView}>← New Question</button>
          )}
          {history.length === 0 && (
            <p style={{fontSize:11,color:'var(--text3)',padding:'8px 10px'}}>No history yet.</p>
          )}
          {history.map(entry => (
            <div
              key={entry.id}
              className={`sidebar-entry ${historyView ? 'readonly' : ''}`}
              onClick={() => loadFromHistory(entry)}
            >
              <div className="sidebar-entry-q">{entry.question.slice(0, 60)}{entry.question.length > 60 ? '…' : ''}</div>
              <div className="sidebar-entry-meta">
                <StatusIcon status={entry.status} />
                <span style={{fontSize:10,color:'var(--text3)'}}>{relativeTime(entry.timestamp)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
