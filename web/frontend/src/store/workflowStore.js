import { create } from 'zustand'

const STAGE_NAMES = ['Ask', 'Acquire', 'Appraise', 'Apply', 'Assess']
const HISTORY_KEY = 'truetruth_history'
const MAX_HISTORY = 20
const MAX_ENTRY_BYTES = 200 * 1024

const makeStage = () => ({
  status: 'pending',   // pending | running | completed | retrying | error
  calls: [],           // [{call_count, status, output, evaluation, decision, logs, elapsed_s}]
})

const INITIAL = {
  status: 'idle',      // idle | running | completed | error
  question: '',
  stages: Object.fromEntries(STAGE_NAMES.map(n => [n, makeStage()])),
  currentAgent: null,
  backtracks: [],
  logs: [],
  finalResult: null,
  error: null,
  historyView: false,
}

function updateLastCall(calls, patch) {
  if (!calls.length) return calls
  return calls.map((c, i) => i === calls.length - 1 ? { ...c, ...patch } : c)
}

function stripStagesForStorage(stages) {
  const result = {}
  for (const [name, stage] of Object.entries(stages)) {
    result[name] = {
      ...stage,
      calls: stage.calls.map(c => {
        const { logs, ...rest } = c
        return rest
      })
    }
  }
  return result
}

function saveEntryToLocalStorage(entry) {
  let stored
  try { stored = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { stored = [] }

  const serialized = JSON.stringify(entry)
  let finalEntry = entry
  if (serialized.length > MAX_ENTRY_BYTES) {
    const { stages, ...rest } = entry
    finalEntry = rest
  }

  const updated = [finalEntry, ...stored].slice(0, MAX_HISTORY)
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(updated)) } catch (e) {
    console.warn('Failed to save history to localStorage', e)
  }
}

export function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
}

export const useWorkflowStore = create((set, get) => ({
  ...INITIAL,

  saveToHistory(status) {
    const state = get()
    const entry = {
      id: crypto.randomUUID(),
      question: state.question,
      timestamp: new Date().toISOString(),
      status,
      stages: stripStagesForStorage(state.stages),
      backtracks: state.backtracks,
      finalResult: state.finalResult,
    }
    saveEntryToLocalStorage(entry)
  },

  loadFromHistory(entry) {
    set({
      historyView: true,
      status: entry.status,
      question: entry.question,
      stages: entry.stages || Object.fromEntries(STAGE_NAMES.map(n => [n, makeStage()])),
      backtracks: entry.backtracks || [],
      logs: [],
      finalResult: entry.finalResult || null,
      error: null,
      currentAgent: null,
    })
  },

  exitHistoryView() {
    set({ historyView: false, ...INITIAL, stages: Object.fromEntries(STAGE_NAMES.map(n => [n, makeStage()])) })
  },

  dispatch(type, payload) {
    set(state => {
      switch (type) {

        case 'RESET':
          return { ...INITIAL, stages: Object.fromEntries(STAGE_NAMES.map(n => [n, makeStage()])) }

        case 'SET_STATUS':
          return { status: payload }

        case 'WORKFLOW_STARTED':
          return { question: payload.question, status: 'running' }

        case 'AGENT_STARTED': {
          const { agent, call_count } = payload
          const newCall = { call_count, status: 'running', output: null, evaluation: null, decision: null, logs: [], elapsed_s: null }
          return {
            currentAgent: agent,
            stages: {
              ...state.stages,
              [agent]: {
                status: 'running',
                calls: [...state.stages[agent].calls, newCall],
              }
            }
          }
        }

        case 'AGENT_LOG': {
          const { agent, line } = payload
          const newLog = payload
          const stageAgent = state.stages[agent]
          if (!stageAgent) return { logs: [...state.logs, newLog] }
          return {
            logs: [...state.logs, newLog],
            stages: {
              ...state.stages,
              [agent]: {
                ...stageAgent,
                calls: updateLastCall(stageAgent.calls, {
                  logs: [...(stageAgent.calls.at(-1)?.logs ?? []), line]
                })
              }
            }
          }
        }

        case 'AGENT_COMPLETED': {
          const { agent, output, elapsed_s } = payload
          return {
            stages: {
              ...state.stages,
              [agent]: {
                ...state.stages[agent],
                status: 'completed',
                calls: updateLastCall(state.stages[agent].calls, { status: 'completed', output, elapsed_s })
              }
            }
          }
        }

        case 'JUDGE_COMPLETED': {
          const { agent, evaluation } = payload
          return {
            stages: {
              ...state.stages,
              [agent]: {
                ...state.stages[agent],
                calls: updateLastCall(state.stages[agent].calls, { evaluation })
              }
            }
          }
        }

        case 'SCHEDULING_DECIDED':
        case 'FASTPATH_TRIGGERED': {
          const { agent, action, reasoning, is_fastpath } = payload
          const decision = { action, reasoning, is_fastpath }
          return {
            stages: {
              ...state.stages,
              [agent]: {
                ...state.stages[agent],
                calls: updateLastCall(state.stages[agent].calls, { decision })
              }
            }
          }
        }

        case 'BACKTRACK_OCCURRED': {
          const { to_stage } = payload
          return {
            backtracks: [...state.backtracks, payload],
            stages: {
              ...state.stages,
              [to_stage]: { ...state.stages[to_stage], status: 'retrying' }
            }
          }
        }

        case 'WORKFLOW_COMPLETED':
          return { status: 'completed', finalResult: payload, currentAgent: null }

        case 'WORKFLOW_ERROR':
          return { status: 'error', error: payload.error, currentAgent: null }

        default:
          return state
      }
    })
  }
}))
