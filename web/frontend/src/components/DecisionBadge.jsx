import InfoTooltip from './InfoTooltip'

const FASTPATH_TIP = '当评分通过且无重大问题时，调度器自动跳过 LLM 决策直接进入下一阶段'
const SCHEDULING_TIP = 'LLM 根据 Judge 评分和问题特征决定下一步动作（继续/重试/回溯/终止）'

export default function DecisionBadge({ decision }) {
  if (!decision) return null
  const { action, reasoning, is_fastpath } = decision

  let cls = 'dec-proceed'
  let label = action
  if (is_fastpath) { cls = 'dec-fastpath'; label = '⚡ FAST-PATH' }
  else if (action === 'retry_current') { cls = 'dec-retry'; label = '↺ Retry' }
  else if (action?.startsWith('backtrack_to_')) { cls = 'dec-backtrack'; label = `↩ ${action.replace('backtrack_to_', 'Backtrack→')}` }
  else if (action === 'terminate') { cls = 'dec-terminate'; label = '✖ Terminate' }
  else if (action === 'proceed') { cls = 'dec-proceed'; label = '→ Proceed' }

  return (
    <div className="decision-row">
      <span className={`decision-action ${cls}`}>{label}</span>
      <InfoTooltip text={is_fastpath ? FASTPATH_TIP : SCHEDULING_TIP} />
      {reasoning && <div className="decision-reason">{reasoning.slice(0, 180)}{reasoning.length > 180 ? '…' : ''}</div>}
    </div>
  )
}
