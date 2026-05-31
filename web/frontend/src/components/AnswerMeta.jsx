import { strengthClass, cleanRationale, buildEvidenceMap } from './helpers'
import { useWorkflowStore } from '../store/workflowStore'

export default function AnswerMeta({ rec, assess, directAnswer }) {
  const evidenceList = useWorkflowStore(
    s => s.stages.Acquire?.calls.at(-1)?.output?.evidence_list ?? []
  )
  const evMap = buildEvidenceMap(evidenceList)
  if (directAnswer) {
    const { answer_basis, guideline_source, caveats } = directAnswer
    return (
      <div className="answer-meta">
        {answer_basis && (
          <div className="meta-row">
            <span className="meta-key">依据</span>
            <span className="meta-val">{answer_basis}</span>
          </div>
        )}
        {guideline_source && (
          <div className="meta-row">
            <span className="meta-key">指南来源</span>
            <span className="meta-val">{guideline_source}</span>
          </div>
        )}
        {caveats?.length > 0 && (
          <ul className="caveat-list">
            {caveats.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        )}
      </div>
    )
  }

  if (!rec) return null
  const score = assess?.quality_score

  return (
    <div className="answer-meta">
      <div className="meta-badges">
        <span className={`rec-strength ${strengthClass(rec.strength)}`}>
          {rec.strength}
        </span>
        {rec.evidence_quality && (
          <span className="meta-badge">{rec.evidence_quality}</span>
        )}
        {score != null && (
          <span className="meta-badge" style={{
            color: score >= 0.8 ? 'var(--green)' : 'var(--orange)'
          }}>
            质量分 {Math.round(score * 100)}%
          </span>
        )}
      </div>

      {rec.rationale && (
        <div className="meta-section">
          <div className="meta-label">理由</div>
          <div className="meta-body">{cleanRationale(rec.rationale, evMap)}</div>
        </div>
      )}

      {rec.caveats?.length > 0 && (
        <div className="meta-section">
          <div className="meta-label">注意事项</div>
          <ul className="caveat-list">
            {rec.caveats.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {assess?.gaps?.length > 0 && (
        <div className="meta-section">
          <div className="meta-label">证据缺口</div>
          <ul className="gap-list">
            {assess.gaps.slice(0, 4).map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
