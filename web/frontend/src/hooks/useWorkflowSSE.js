import { useRef } from 'react'
import { useWorkflowStore } from '../store/workflowStore'

const SSE_EVENTS = [
  'workflow_started', 'agent_started', 'agent_log',
  'agent_completed', 'judge_completed', 'scheduling_decided',
  'backtrack_occurred', 'fastpath_triggered',
  'workflow_completed', 'workflow_error', 'heartbeat',
  'rec_text_token', 'direct_answer_token',
]

export function useWorkflowSSE() {
  const esRef = useRef(null)
  const dispatch = useWorkflowStore(s => s.dispatch)
  const saveToHistory = useWorkflowStore(s => s.saveToHistory)

  async function startWorkflow(question) {
    // Close any existing stream
    if (esRef.current) { esRef.current.close(); esRef.current = null }

    dispatch('RESET')
    dispatch('SET_STATUS', 'running')

    // Track whether workflow completed normally (so onerror doesn't override it)
    let workflowFinished = false

    // Register session → get session_id
    let sessionId
    try {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      sessionId = json.session_id
    } catch (err) {
      dispatch('SET_STATUS', 'error')
      dispatch('WORKFLOW_ERROR', { error: `Failed to start session: ${err.message}` })
      return
    }

    // Open SSE stream
    const es = new EventSource(`/api/run?session_id=${sessionId}`)
    esRef.current = es

    SSE_EVENTS.forEach(type => {
      es.addEventListener(type, (e) => {
        try {
          const data = JSON.parse(e.data)
          dispatch(type.toUpperCase(), data)
          if (type === 'workflow_completed') {
            workflowFinished = true
            const finalRec = data.recommendation
            saveToHistory(finalRec ? 'completed' : 'terminated')
          } else if (type === 'workflow_error') {
            workflowFinished = true
            saveToHistory('error')
          }
        } catch {}
      })
    })

    es.onerror = () => {
      if (!workflowFinished) {
        dispatch('SET_STATUS', 'error')
      }
      es.close()
    }
  }

  function stopWorkflow() {
    esRef.current?.close()
    esRef.current = null
    dispatch('SET_STATUS', 'idle')
  }

  return { startWorkflow, stopWorkflow }
}
