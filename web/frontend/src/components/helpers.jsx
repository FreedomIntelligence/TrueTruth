// Helpers shared across components

const EV_TYPE_ZH = {
  RCT: 'RCT研究', META: 'Meta分析', SR: '系统综述',
  COHORT: '队列研究', CASE: '病例报告', GUIDELINE: '指南',
}

// Build a lookup map from evidence_id → paper entry, given the Acquire evidence_list.
export function buildEvidenceMap(evidenceList = []) {
  const map = {}
  for (const p of evidenceList) {
    if (p.evidence_id) map[p.evidence_id] = p
  }
  return map
}

// Replace internal "EV-RCT-2008-SALIM-001 [results_1]" citations with readable labels.
// With evidenceMap: "[Telmisartan, Ramipril… (2008年RCT研究)]"
// Without map:      "[2008年RCT研究]"
export function cleanRationale(text, evidenceMap = {}) {
  if (!text) return text

  const makeLabel = (fullId, type, year) => {
    const entry = evidenceMap[fullId]
    const typeName = EV_TYPE_ZH[type] || type
    if (entry?.title) {
      const t = entry.title
      const short = t.length > 32 ? t.slice(0, 31) + '…' : t
      return `[${short} (${year}年${typeName})]`
    }
    return `[${year}年${typeName}]`
  }

  return text
    // "[EV-TYPE-YEAR-AUTH-NNN / section]" or "[EV-TYPE-YEAR-AUTH-NNN]"
    .replace(/\[(EV-([A-Z]+)-(\d{4})-[A-Z0-9]+-\d{3})[^\]]*\]/g,
      (_, id, t, y) => makeLabel(id, t, y))
    // "EV-TYPE-YEAR-AUTH-NNN [section]" or bare "EV-TYPE-YEAR-AUTH-NNN"
    .replace(/(EV-([A-Z]+)-(\d{4})-[A-Z0-9]+-\d{3})(?:\s*\[[^\]]+\])?/g,
      (_, id, t, y) => makeLabel(id, t, y))
    .replace(/\s{2,}/g, ' ')
    .trim()
}


export function studyTypeBadge(type) {
  if (!type) return <span className="badge badge-other">Unknown</span>
  const t = type.toLowerCase()
  if (t.includes('systematic') || t.includes('meta') || t.includes('nma')) return <span className="badge badge-sr">{type}</span>
  if (t.includes('rct') || t.includes('randomized') || t.includes('randomised')) return <span className="badge badge-rct">{type}</span>
  if (t.includes('cohort') || t.includes('observ')) return <span className="badge badge-cohort">{type}</span>
  if (t.includes('guideline')) return <span className="badge badge-guideline">{type}</span>
  return <span className="badge badge-other">{type}</span>
}

export function gradeBadge(grade) {
  if (!grade) return null
  const g = grade.toLowerCase()
  if (g.includes('high')) return <span className="badge badge-high">High</span>
  if (g.includes('moderate')) return <span className="badge badge-moderate">Moderate</span>
  if (g.includes('very')) return <span className="badge badge-vlow">Very Low</span>
  if (g.includes('low')) return <span className="badge badge-low">Low</span>
  return <span className="badge badge-other">{grade}</span>
}

export function strengthClass(strength) {
  if (!strength) return 'str-insufficient'
  const s = strength.toLowerCase()
  if (s.includes('strong')) return 'str-strong'
  if (s.includes('conditional')) return 'str-conditional'
  if (s.includes('consensus')) return 'str-consensus'
  if (s.includes('weak')) return 'str-weak'
  return 'str-insufficient'
}
