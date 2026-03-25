import { useState } from 'react'
import JudgeScorePanel from './JudgeScorePanel'
import DecisionBadge from './DecisionBadge'
import EvidenceTable from './EvidenceTable'
import RecommendationPanel from './RecommendationPanel'
import InfoTooltip from './InfoTooltip'
import { studyTypeBadge, gradeBadge } from './helpers'

const STAGE_SUBTITLES = {
  Ask: '将临床问题结构化为 PICO 格式，提取检索关键词',
  Acquire: '从证据库中检索相关文献段落，筛选最相关条目',
  Appraise: '评估证据质量和等级（GRADE），识别研究间冲突',
  Apply: '基于证据生成临床推荐意见及推荐强度',
  Assess: '自评推荐质量，识别证据缺口，决定是否需要回溯',
}

const TOOLTIPS = {
  PICO: '临床问题四要素：P=患者/病症, I=干预措施, C=对照, O=结局指标',
  GRADE: '证据质量分级体系：High→Moderate→Low→Very Low',
}

// ── Ask output ──
function AskOutput({ output }) {
  const pico = output?.pico_query
  if (!pico) return <p className="placeholder">Processing…</p>
  return (
    <div>
      <div style={{display:'flex',alignItems:'center',gap:4,marginBottom:6}}>
        <span style={{fontSize:12,fontWeight:700,color:'var(--text2)'}}>PICO</span>
        <InfoTooltip text={TOOLTIPS.PICO} />
      </div>
      <table className="pico-table">
        <tbody>
          {[['P', pico.patient], ['I', pico.intervention], ['C', pico.comparison], ['O', pico.outcome]].map(([k,v]) => (
            <tr key={k}><td>{k}</td><td>{v}</td></tr>
          ))}
        </tbody>
      </table>
      {pico.keywords?.length > 0 && (
        <div style={{marginTop:8,display:'flex',gap:4,flexWrap:'wrap'}}>
          {pico.keywords.map((kw,i) => <span key={i} style={{background:'var(--bg3)',color:'var(--text2)',padding:'1px 6px',borderRadius:4,fontSize:11}}>{kw}</span>)}
        </div>
      )}
      {output.question_type && <div className="pico-type-badge">{output.question_type}</div>}
    </div>
  )
}

// ── Acquire output ──
function AcquireOutput({ output }) {
  if (!output) return <p className="placeholder">Processing…</p>
  return (
    <div>
      <div style={{display:'flex',gap:16,marginBottom:10,fontSize:12,color:'var(--text2)'}}>
        <span>Candidates: <strong style={{color:'var(--text)'}}>{output.total_results}</strong></span>
        <span>Selected: <strong style={{color:'var(--text)'}}>{output.selected_count}</strong></span>
        {output.study_type_distribution && Object.entries(output.study_type_distribution).map(([k,v]) => (
          <span key={k}>{studyTypeBadge(k)} <strong style={{color:'var(--text)'}}>{v}</strong></span>
        ))}
      </div>
      <EvidenceTable evidenceList={output.evidence_list} />
    </div>
  )
}

// ── Appraise output ──
function AppraiseOutput({ output }) {
  if (!output?.evidence_grades) return <p className="placeholder">Processing…</p>
  return (
    <div>
      {output.has_conflict && (
        <div style={{background:'#2a1515',border:'1px solid var(--orange)',borderRadius:5,padding:'6px 10px',fontSize:12,marginBottom:10,color:'#fdba74'}}>
          ⚠ Conflict detected: {output.conflict_description}
        </div>
      )}
      {output.summary && <p style={{fontSize:13,color:'var(--text2)',marginBottom:10,lineHeight:1.4}}>{output.summary}</p>}
      <div style={{display:'flex',flexDirection:'column',gap:5}}>
        {output.evidence_grades.map((e, i) => (
          <div key={i} style={{display:'flex',alignItems:'flex-start',gap:8,fontSize:12,padding:'4px 0',borderBottom:'1px solid var(--border)'}}>
            <span style={{color:'var(--text3)',width:18,flexShrink:0}}>{i+1}</span>
            <span style={{flex:1,color:'var(--text)',lineHeight:1.4}}>{e.title}</span>
            <div style={{display:'flex',gap:4,alignItems:'center',flexShrink:0}}>
              {studyTypeBadge(e.study_type)}
              {gradeBadge(e.grade_level)}
              <InfoTooltip text={TOOLTIPS.GRADE} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Apply output ──
function ApplyOutput({ output }) {
  if (!output?.recommendation) return <p className="placeholder">Processing…</p>
  return <RecommendationPanel rec={output.recommendation} />
}

// ── Assess output ──
function AssessOutput({ output }) {
  const assess = output?.assessment
  if (!assess) return <p className="placeholder">Processing…</p>
  const score = assess.quality_score
  const ringCls = score >= 0.8 ? 'qr-good' : score >= 0.6 ? 'qr-ok' : 'qr-bad'
  return (
    <div style={{textAlign:'center'}}>
      <div className={`quality-ring ${ringCls}`}>{Math.round(score * 100)}%</div>
      <div style={{fontSize:11,color:'var(--text3)',marginTop:4}}>Workflow Quality（自评）</div>
      <p className="section-title">Identified Gaps</p>
      {assess.gaps?.length > 0
        ? <ul className="gap-list" style={{textAlign:'left'}}>{assess.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul>
        : <p style={{color:'var(--text3)',fontSize:12}}>None identified</p>}
    </div>
  )
}

const OUTPUT_COMPONENTS = { Ask: AskOutput, Acquire: AcquireOutput, Appraise: AppraiseOutput, Apply: ApplyOutput, Assess: AssessOutput }

export default function StageCard({ stageName, stage }) {
  const [selectedCall, setSelectedCall] = useState(0)

  if (!stage.calls.length) {
    return (
      <div className="panel">
        <div className="panel-header">
          <div>
            <div>{stageName}</div>
            {STAGE_SUBTITLES[stageName] && <div style={{fontSize:11,color:'var(--text3)',fontWeight:400,marginTop:2}}>{STAGE_SUBTITLES[stageName]}</div>}
          </div>
        </div>
        <div className="panel-body"><p className="placeholder">Not yet executed.</p></div>
      </div>
    )
  }

  // Show latest call by default when new calls arrive
  const callIdx = Math.min(selectedCall, stage.calls.length - 1)
  const call = stage.calls[callIdx]
  const OutputComp = OUTPUT_COMPONENTS[stageName]

  return (
    <div className="panel">
      <div className="panel-header">
        <div style={{flex:1}}>
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <span>{stageName}</span>
            {stage.status === 'running' && <span style={{fontSize:12,color:'var(--blue)'}}>⏳ Running…</span>}
          </div>
          {STAGE_SUBTITLES[stageName] && <div style={{fontSize:11,color:'var(--text3)',fontWeight:400,marginTop:2}}>{STAGE_SUBTITLES[stageName]}</div>}
        </div>
        {call?.elapsed_s && <span style={{fontSize:11,color:'var(--text3)'}}>{call.elapsed_s}s</span>}
      </div>
      <div className="panel-body">
        {stage.calls.length > 1 && (
          <div className="call-tabs">
            {stage.calls.map((c, i) => {
              const judgeIcon = c.evaluation == null ? '·' : c.evaluation.pass_threshold ? '✓' : '✗'
              const judgeColor = c.evaluation == null ? 'var(--text3)' : c.evaluation.pass_threshold ? 'var(--green)' : 'var(--orange)'
              const action = c.decision?.action || ''
              const schedIcon = action.startsWith('backtrack') ? '↩' : action === 'retry' ? '↺' : action === 'proceed' ? '→' : action === 'terminate' ? '✖' : c.decision?.is_fastpath ? '⚡' : ''
              return (
                <button key={i} className={`call-tab ${i === callIdx ? 'active' : ''}`} onClick={() => setSelectedCall(i)}>
                  Call {c.call_count}
                  <span style={{marginLeft:5,fontSize:10,color:judgeColor}}>{judgeIcon}</span>
                  {schedIcon && <span style={{marginLeft:3,fontSize:10,color:'var(--text2)'}}>{schedIcon}</span>}
                </button>
              )
            })}
          </div>
        )}

        {/* Agent output */}
        {OutputComp && <OutputComp output={call?.output} />}

        <hr className="divider" />

        {/* Judge score */}
        <p className="section-title" style={{marginTop:10}}>Judge Score（第三方评分）</p>
        <JudgeScorePanel evaluation={call?.evaluation} />

        {/* Scheduling decision */}
        {call?.decision && <DecisionBadge decision={call.decision} />}
      </div>
    </div>
  )
}
