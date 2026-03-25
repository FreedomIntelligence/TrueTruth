import { strengthClass } from './helpers'
import InfoTooltip from './InfoTooltip'

const CAVEATS_TIP = '使用本推荐意见时需注意的例外、限制或特殊情况'
const QUALITY_TIP = 'Assess agent 对整个 workflow 输出质量的自评分，独立于 Judge Score'

export default function RecommendationPanel({ rec, assess }) {
  if (!rec) return null
  const strCls = strengthClass(rec.strength)
  const score = assess?.quality_score
  const ringCls = score >= 0.8 ? 'qr-good' : score >= 0.6 ? 'qr-ok' : 'qr-bad'

  return (
    <div>
      <span className={`rec-strength ${strCls}`}>{rec.strength || 'Unknown'}</span>
      <div className="rec-text">{rec.text}</div>

      <div className="rec-section">
        <div className="rec-section-title">Evidence Quality</div>
        <div className="rec-section-body">{rec.evidence_quality}</div>
      </div>

      <div className="rec-section">
        <div className="rec-section-title">Rationale</div>
        <div className="rec-section-body">{rec.rationale}</div>
      </div>

      {rec.caveats?.length > 0 && (
        <div className="rec-section">
          <div className="rec-section-title" style={{display:'flex',alignItems:'center',gap:4}}>
            Caveats <InfoTooltip text={CAVEATS_TIP} />
          </div>
          <ul className="caveat-list">
            {rec.caveats.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {assess && (
        <div className="rec-section">
          <div className="rec-section-title">Quality Assessment</div>
          <div style={{display:'flex',alignItems:'center',gap:16,marginTop:8}}>
            <div style={{textAlign:'center'}}>
              <div className={`quality-ring ${ringCls}`} style={{width:54,height:54,fontSize:15}}>
                {Math.round(score * 100)}%
              </div>
              <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:2,fontSize:11,color:'var(--text3)',marginTop:4}}>
                Workflow Quality（自评）<InfoTooltip text={QUALITY_TIP} />
              </div>
            </div>
            {assess.gaps?.length > 0 && (
              <ul className="gap-list" style={{flex:1}}>
                {assess.gaps.slice(0,4).map((g,i) => <li key={i}>{g}</li>)}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
