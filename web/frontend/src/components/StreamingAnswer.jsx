export default function StreamingAnswer({ tokens, complete }) {
  if (!tokens) return null
  return (
    <div className="answer-text">
      {tokens}
      {!complete && <span className="answer-cursor" aria-hidden="true">▌</span>}
    </div>
  )
}
