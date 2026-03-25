// Helpers shared across components

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
