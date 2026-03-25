import { studyTypeBadge, gradeBadge } from './helpers'

export default function EvidenceTable({ evidenceList }) {
  if (!evidenceList?.length) return <p className="placeholder">No evidence yet.</p>
  return (
    <table className="evidence-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Title</th>
          <th>Type</th>
          <th>Rel</th>
          <th>GRADE</th>
          <th>PMID</th>
        </tr>
      </thead>
      <tbody>
        {evidenceList.map((e, i) => (
          <tr key={i}>
            <td style={{color:'var(--text3)',fontSize:'11px'}}>{i + 1}</td>
            <td className="ev-title" style={{maxWidth:280}}>
              {e.pmid
                ? <a href={`https://pubmed.ncbi.nlm.nih.gov/${e.pmid}`} target="_blank" rel="noreferrer">{e.title}</a>
                : e.title}
              {e.key_sentences ? (
                <div style={{marginTop:4,padding:'4px 8px',background:'#0e2236',borderLeft:'2px solid var(--cyan)',borderRadius:3,fontSize:'11px',color:'var(--text)',lineHeight:1.4}}>
                  {e.key_sentences}
                </div>
              ) : null}
              {e.abstract_preview && (
                <details style={{marginTop:2}}>
                  <summary style={{color:'var(--text3)',fontSize:'10px',cursor:'pointer'}}>{e.key_sentences ? 'context' : 'abstract'}</summary>
                  <p style={{color:'var(--text2)',fontSize:'11px',marginTop:4,lineHeight:1.4}}>{e.abstract_preview}</p>
                </details>
              )}
            </td>
            <td>{studyTypeBadge(e.study_type)}</td>
            <td>
              <div className="rel-bar">
                <div className="rel-fill" style={{width:`${Math.round((e.relevance_score||0)*100)}%`}} />
              </div>
              <div style={{fontSize:'10px',color:'var(--text3)',marginTop:2}}>{e.relevance_score?.toFixed(2)}</div>
            </td>
            <td>{gradeBadge(e.grade_level)}</td>
            <td>
              {e.pmid && (
                <a className="badge badge-pmid" href={`https://pubmed.ncbi.nlm.nih.gov/${e.pmid}`} target="_blank" rel="noreferrer">
                  {e.pmid}
                </a>
              )}
              {e.pmcid && !e.pmid && <span className="badge badge-other">PMC{e.pmcid}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
