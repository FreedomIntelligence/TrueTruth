import { useState, useRef, useEffect, useMemo } from 'react'
import { cleanRationale, buildEvidenceMap } from './helpers'
import { useWorkflowStore } from '../store/workflowStore'

const STAGE_NAMES = ['Ask', 'Acquire', 'Appraise', 'Apply', 'Assess']

// ── summary line (collapsed header) ─────────────────────────────────────────

function stageSummary(name, stage) {
  const call = stage.calls.at(-1)
  if (!call) return null
  const { output, elapsed_s } = call
  const t = elapsed_s ? ` · ${elapsed_s}s` : ''

  if (name === 'Ask' && output?.pico_query) {
    const patient = (output.pico_query.patient || '').slice(0, 28)
    const ellipsis = (output.pico_query.patient || '').length > 28 ? '…' : ''
    return `${output.question_type || 'PICO'} · ${patient}${ellipsis}${t}`
  }
  if (name === 'Acquire' && output) {
    const dist = output.study_type_distribution || {}
    const parts = Object.entries(dist).map(([k, v]) => `${k}×${v}`).join(' ')
    return `${output.selected_count ?? '?'} 篇${parts ? ' · ' + parts : ''}${t}`
  }
  if (name === 'Appraise' && output?.evidence_grades) {
    const grades = {}
    for (const e of output.evidence_grades)
      if (e.grade_level) grades[e.grade_level] = (grades[e.grade_level] || 0) + 1
    const gs = Object.entries(grades).map(([g, n]) => `${g}×${n}`).join(' ')
    return `${gs}${output.has_conflict ? ' · ⚠ 冲突' : ''}${t}`
  }
  if (name === 'Apply') {
    if (stage.status === 'running') return '推荐生成中...'
    const str = output?.recommendation?.strength
    return str ? `${str}${t}` : `已完成${t}`
  }
  if (name === 'Assess' && output?.assessment)
    return `质量分 ${Math.round(output.assessment.quality_score * 100)}%${t}`
  if (stage.status === 'running') return '处理中...'
  return elapsed_s ? `${elapsed_s}s` : null
}

// ── badge helpers ────────────────────────────────────────────────────────────

function studyBadge(type) {
  if (!type) return 'badge-other'
  const t = type.toLowerCase()
  if (t.includes('rct') || t.includes('randomized') || t.includes('trial')) return 'badge-rct'
  if (t.includes('meta') || t.includes('systematic')) return 'badge-sr'
  if (t.includes('cohort') || t.includes('observ')) return 'badge-cohort'
  if (t.includes('guideline')) return 'badge-guideline'
  return 'badge-other'
}

function gradeBadge(grade) {
  if (!grade) return 'badge-other'
  const g = grade.toLowerCase()
  if (g === 'high') return 'badge-high'
  if (g === 'moderate') return 'badge-moderate'
  if (g === 'low') return 'badge-low'
  if (g.includes('very')) return 'badge-vlow'
  return 'badge-other'
}

// ── live log (running) ───────────────────────────────────────────────────────

const NOISE = /^\[TIMING\]|^\[FAST-PATH|^\[PARALLEL-|^\[SERVICE-CHECK\]/

function StageLogArea({ logs }) {
  const areaRef = useRef(null)
  const lines = logs
    .filter(l => !NOISE.test(l))
    .map(l => l.replace(/\*\*/g, '').replace(/`/g, ''))

  useEffect(() => {
    if (areaRef.current) areaRef.current.scrollTop = areaRef.current.scrollHeight
  }, [lines.length])

  return (
    <div ref={areaRef} className="ts-log-area">
      {lines.map((line, i) => <div key={i} className="ts-log-line">{line}</div>)}
    </div>
  )
}

// ── structured result cards (completed) ─────────────────────────────────────

function AskCard({ output }) {
  const pico = output.pico_query
  if (!pico) return null
  const rows = [
    ['患者 (P)', pico.patient],
    ['干预 (I)', pico.intervention],
    ['对照 (C)', pico.comparison],
    ['结局 (O)', pico.outcome],
  ].filter(([, v]) => v)
  return (
    <div className="ts-detail">
      <div className="ts-detail-row">
        <span className="ts-detail-key">问题类型</span>
        <span className="ts-detail-val">{output.question_type}</span>
      </div>
      {rows.map(([k, v]) => (
        <div key={k} className="ts-detail-row">
          <span className="ts-detail-key">{k}</span>
          <span className="ts-detail-val">{v}</span>
        </div>
      ))}
    </div>
  )
}

function AcquireCard({ output }) {
  const papers = output.evidence_list || []
  return (
    <div className="ts-detail">
      <div className="ts-detail-subtitle">检索到 {output.selected_count} 篇文献</div>
      {papers.map((p, i) => (
        <div key={i} className="ts-paper-row">
          <span className={`badge ${studyBadge(p.study_type)}`}>{p.study_type || '?'}</span>
          {p.grade_level && <span className={`badge ${gradeBadge(p.grade_level)}`}>{p.grade_level}</span>}
          <span className="ts-paper-title">{p.title}</span>
        </div>
      ))}
    </div>
  )
}

function AppraiseCard({ output }) {
  const grades = output.evidence_grades || []
  const dist = {}
  for (const e of grades) {
    const g = e.grade_level || '未分级'
    dist[g] = (dist[g] || 0) + 1
  }
  return (
    <div className="ts-detail">
      <div className="ts-detail-row">
        <span className="ts-detail-key">GRADE 分布</span>
        <span className="ts-detail-val">
          {Object.entries(dist).map(([g, n]) => `${g} ×${n}`).join('　') || '未分级'}
        </span>
      </div>
      {output.has_conflict && (
        <div className="ts-detail-row ts-conflict-row">
          <span className="ts-detail-key">⚠ 冲突</span>
          <span className="ts-detail-val">{output.conflict_description || '存在证据冲突'}</span>
        </div>
      )}
      {output.summary && <div className="ts-detail-full">{output.summary}</div>}
    </div>
  )
}

function ApplyCard({ output }) {
  const rec = output.recommendation
  const evidenceList = useWorkflowStore(
    s => s.stages.Acquire?.calls.at(-1)?.output?.evidence_list ?? []
  )
  const evMap = useMemo(() => buildEvidenceMap(evidenceList), [evidenceList])

  if (!rec) return null
  return (
    <div className="ts-detail">
      <div className="ts-detail-row">
        <span className="ts-detail-key">推荐强度</span>
        <span className="ts-detail-val">{rec.strength}</span>
      </div>
      {rec.evidence_quality && (
        <div className="ts-detail-row">
          <span className="ts-detail-key">证据质量</span>
          <span className="ts-detail-val">{rec.evidence_quality}</span>
        </div>
      )}
      {rec.rationale && (
        <div className="ts-detail-full">{cleanRationale(rec.rationale, evMap)}</div>
      )}
    </div>
  )
}

function AssessCard({ output }) {
  const assess = output.assessment
  if (!assess) return null
  const score = Math.round(assess.quality_score * 100)
  return (
    <div className="ts-detail">
      <div className="ts-detail-row">
        <span className="ts-detail-key">质量评分</span>
        <span className="ts-detail-val">{score}%</span>
      </div>
      {assess.gaps?.length > 0 && (
        <ul className="ts-gap-list">
          {assess.gaps.map((g, i) => <li key={i}>{g}</li>)}
        </ul>
      )}
    </div>
  )
}

function StageContent({ name, stage }) {
  const st = stage.status
  const call = stage.calls.at(-1)
  const output = call?.output
  const logs = call?.logs ?? []

  if ((st === 'running' || st === 'retrying') && logs.length > 0)
    return <StageLogArea logs={logs} />

  if (st !== 'completed' || !output) return null

  if (name === 'Ask') return <AskCard output={output} />
  if (name === 'Acquire') return <AcquireCard output={output} />
  if (name === 'Appraise') return <AppraiseCard output={output} />
  if (name === 'Apply') return <ApplyCard output={output} />
  if (name === 'Assess') return <AssessCard output={output} />
  return null
}

// ── main ─────────────────────────────────────────────────────────────────────

export default function ThinkingBlock({ stages, totalElapsed }) {
  const [open, setOpen] = useState(true)
  const [expanded, setExpanded] = useState({})

  return (
    <div className="thinking-block">
      <button className="thinking-toggle" onClick={() => setOpen(o => !o)}>
        <span className="thinking-arrow">{open ? '▼' : '▶'}</span>
        <span className="thinking-label">思考过程</span>
        {totalElapsed != null && (
          <span className="thinking-time">{Math.round(totalElapsed)}s</span>
        )}
      </button>

      {open && (
        <div className="thinking-stages">
          {STAGE_NAMES.map(name => {
            const stage = stages[name]
            const st = stage.status
            const call = stage.calls.at(-1)
            const logs = call?.logs ?? []
            const output = call?.output
            const hasContent =
              ((st === 'running' || st === 'retrying') && logs.length > 0) ||
              (st === 'completed' && !!output)

            // Running stages auto-expand when logs arrive; completed start collapsed
            const isExpanded = expanded[name] !== undefined
              ? expanded[name]
              : (st === 'running' || st === 'retrying') && logs.length > 0

            const icon = st === 'completed' ? '✓'
              : st === 'running' || st === 'retrying' ? '⏳'
              : st === 'error' ? '✗' : '·'
            const colorClass = st === 'completed' ? 'ts-done'
              : st === 'running' || st === 'retrying' ? 'ts-run'
              : st === 'error' ? 'ts-err' : 'ts-wait'
            const summary = stageSummary(name, stage)

            return (
              <div key={name} className={`thinking-stage ${colorClass}`}>
                <div
                  className={`ts-header${hasContent ? ' ts-clickable' : ''}`}
                  onClick={() => {
                    if (!hasContent) return
                    setExpanded(prev => ({ ...prev, [name]: !isExpanded }))
                  }}
                >
                  <span className="ts-name">{icon} {name}</span>
                  {summary && <span className="ts-summary">{summary}</span>}
                  {hasContent && (
                    <span className="ts-expand-btn">{isExpanded ? '▴' : '▾'}</span>
                  )}
                </div>
                {isExpanded && <StageContent name={name} stage={stage} />}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
