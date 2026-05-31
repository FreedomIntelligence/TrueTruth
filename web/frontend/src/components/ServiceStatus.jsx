import { useEffect, useState } from 'react'

export default function ServiceStatus() {
  const [svc, setSvc] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => setSvc(d.services))
      .catch(() => {})
  }, [])

  if (!svc) return null

  const allOk = svc.docker && svc.qdrant && svc.hypertensiondb
  const color = allOk ? 'var(--green)' : 'var(--orange)'
  const tip = `Docker: ${svc.docker ? '✓' : '✗'} | Qdrant: ${svc.qdrant ? '✓' : '✗'} | DB: ${svc.hypertensiondb ? '✓' : '✗'}`

  return (
    <div className="svc-status" title={tip}>
      <span className="svc-dot" style={{ background: color }} />
      <span style={{ color, fontSize: 11 }}>{allOk ? '服务就绪' : '服务异常'}</span>
    </div>
  )
}
