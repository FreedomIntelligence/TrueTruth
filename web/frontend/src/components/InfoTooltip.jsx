import { useState } from 'react'

export default function InfoTooltip({ text }) {
  const [pos, setPos] = useState(null)

  function handleMouseEnter(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    setPos({ top: rect.bottom + 6, left: rect.left })
  }

  function handleMouseLeave() {
    setPos(null)
  }

  return (
    <span className="info-tooltip-wrap" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <span className="info-tooltip-icon">ⓘ</span>
      {pos && (
        <div className="info-tooltip-popover" style={{ top: pos.top, left: pos.left }}>
          {text}
        </div>
      )}
    </span>
  )
}
