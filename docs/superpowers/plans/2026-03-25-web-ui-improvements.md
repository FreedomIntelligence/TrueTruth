# Web UI Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply five improvements to the TrueTruth web UI: branding, display-confusion fixes, contextual tooltips, localStorage history panel, and span-level evidence retrieval.

**Architecture:** Pure frontend tasks (Problems 5, 4, 2, 1) modify React components and the Zustand store; they are independent of the backend. Problem 3 (span retrieval) requires coordinated changes across the Python backend (schema → local_evidence_db → acquire_agent → judge_llm → serializers) before the frontend EvidenceTable change. All tasks follow the dependency order prescribed in the spec.

**Tech Stack:** React 18 + Zustand 5 + Vite 4 (frontend); FastAPI + Python 3.10 (backend). No test framework is installed — build verification uses `npm run build` for frontend and inline `python3 -c` scripts for backend logic.

**Spec:** `docs/superpowers/specs/2026-03-25-web-ui-improvements-design.md`

---

## File Map

| File | Action | Reason |
|------|--------|--------|
| `web/frontend/src/App.jsx` | Modify | Branding, layout (sidebar), read-only history mode |
| `web/frontend/index.html` | Modify | `<title>` → TrueTruth |
| `web/frontend/src/index.css` | Modify | Header styles, tooltip styles, key_sentences highlight |
| `web/backend/app.py` | Modify | `FastAPI(title=...)` → TrueTruth |
| `web/frontend/src/components/StageCard.jsx` | Modify | Call-tab dual indicator, stage subtitles, AssessOutput label |
| `web/frontend/src/components/JudgeScorePanel.jsx` | Modify | Explanatory note, severity sort + count summary, header label |
| `web/frontend/src/components/RecommendationPanel.jsx` | Modify | Quality Assessment label |
| `web/frontend/src/components/InfoTooltip.jsx` | **Create** | Fixed-position tooltip popover |
| `web/frontend/src/components/EvidenceTable.jsx` | Modify | Render `key_sentences` as primary evidence |
| `web/frontend/src/store/workflowStore.js` | Modify | `saveToHistory`, `loadFromHistory`, `historyView` flag |
| `web/frontend/src/components/HistorySidebar.jsx` | **Create** | Collapsible history list |
| `src/state/schema.py` | Modify | Add `key_sentences` field to `Evidence` |
| `src/tools/local_evidence_db.py` | Modify | Add `_extract_spans`, call from `search_local` |
| `src/agents/acquire_agent.py` | Modify | `_listwise_rank` uses `key_sentences`; fix NameError |
| `src/judge/judge_llm.py` | Modify | Exclude `key_sentences` in Appraise branch |
| `web/backend/serializers.py` | Modify | Include `key_sentences` in `serialize_evidence_list` |

---

## Task 1: Branding — TrueTruth

**Files:**
- Modify: `web/frontend/src/App.jsx`
- Modify: `web/frontend/index.html`
- Modify: `web/frontend/src/index.css`
- Modify: `web/backend/app.py`

- [ ] **Step 1: Update index.html title**

Open `web/frontend/index.html`. Change:
```html
<title>Vite + React</title>
```
to:
```html
<title>TrueTruth</title>
```

- [ ] **Step 2: Update FastAPI app title**

In `web/backend/app.py`, change:
```python
app = FastAPI(title="EBM 5A Clinical Decision Support", version="1.0.0")
```
to:
```python
app = FastAPI(title="TrueTruth Clinical Decision Support", version="1.0.0")
```

- [ ] **Step 3: Update App.jsx header**

In `web/frontend/src/App.jsx`, replace the header div:
```jsx
      {/* Header */}
      <div className="header">
        <h1>EBM 5A</h1>
        <span className="header-badge">Clinical Decision Support</span>
        {status === 'completed' && <span className="header-badge" style={{background:'var(--green-dim)',color:'#86efac'}}>✓ Complete</span>}
        {status === 'error' && <span className="header-badge" style={{background:'#7f1d1d',color:'#fca5a5'}}>✗ Error</span>}
      </div>
```
with:
```jsx
      {/* Header */}
      <div className="header">
        <div className="header-brand">
          <h1>TrueTruth</h1>
          <span className="header-subtitle">AI-Powered Clinical Evidence Synthesis</span>
        </div>
        <div className="header-badges">
          {status === 'completed' && <span className="header-badge" style={{background:'var(--green-dim)',color:'#86efac'}}>✓ Complete</span>}
          {status === 'error' && <span className="header-badge" style={{background:'#7f1d1d',color:'#fca5a5'}}>✗ Error</span>}
        </div>
      </div>
```

- [ ] **Step 4: Update header CSS**

In `web/frontend/src/index.css`, replace the existing `.header` rule (find it by searching for `.header {`) with:
```css
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 72px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.header-brand { display: flex; flex-direction: column; gap: 2px; }
.header-brand h1 { font-size: 32px; font-weight: 700; color: var(--text); margin: 0; letter-spacing: -0.5px; }
.header-subtitle { font-size: 12px; color: var(--text3); font-style: italic; }
.header-badges { display: flex; gap: 8px; align-items: center; }
```

- [ ] **Step 5: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```
Expected: `✓ built in ...`

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/App.jsx web/frontend/index.html web/frontend/src/index.css web/backend/app.py
git commit -m "feat: rebrand to TrueTruth, enlarge header"
```

---

## Task 2: Display Fix — Call Tab Dual Indicator

**Files:**
- Modify: `web/frontend/src/components/StageCard.jsx`

- [ ] **Step 1: Update call tab render in StageCard.jsx**

Find the call tabs section (search for `className={`call-tab`). Replace:
```jsx
              <button key={i} className={`call-tab ${i === callIdx ? 'active' : ''}`} onClick={() => setSelectedCall(i)}>
                Call {c.call_count}
                {c.evaluation && (
                  <span style={{marginLeft:4,fontSize:10}}>{c.evaluation.pass_threshold ? '✓' : '✗'}</span>
                )}
              </button>
```
with:
```jsx
              <button key={i} className={`call-tab ${i === callIdx ? 'active' : ''}`} onClick={() => setSelectedCall(i)}>
                Call {c.call_count}
                <span style={{marginLeft:6,fontSize:10,display:'inline-flex',gap:3}}>
                  {c.evaluation
                    ? <span style={{color: c.evaluation.pass_threshold ? 'var(--green)' : 'var(--orange)'}}>{c.evaluation.pass_threshold ? '✓' : '✗'}</span>
                    : <span style={{color:'var(--text3)'}}>·</span>}
                  {c.decision && (
                    <span style={{color:'var(--text2)'}}>
                      {c.decision.is_fastpath ? '⚡' :
                       c.decision.action === 'proceed' ? '→' :
                       c.decision.action === 'retry' ? '↺' :
                       c.decision.action?.startsWith('backtrack') ? '↩' :
                       c.decision.action === 'terminate' ? '✖' : ''}
                    </span>
                  )}
                </span>
              </button>
```

- [ ] **Step 2: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/components/StageCard.jsx
git commit -m "feat: show judge pass/fail and scheduling action on call tabs"
```

---

## Task 3: Display Fix — JudgeScorePanel Note and Severity Summary

**Files:**
- Modify: `web/frontend/src/components/JudgeScorePanel.jsx`

- [ ] **Step 1: Read the current file**

```bash
cat /data/wuyuang/ebm5a/web/frontend/src/components/JudgeScorePanel.jsx
```

- [ ] **Step 2: Add explanatory note below score circle, severity summary before issue list**

The file renders: score circle → dimension bars → issues list. Make these changes:

After the score circle div (the one with `className="judge-overall"`), add:
```jsx
      <p style={{fontSize:11,color:'var(--text3)',textAlign:'center',marginTop:4,marginBottom:10}}>
        总分为各维度加权平均；Minor 问题不大幅影响分数，但仍列出供参考。
      </p>
```

Before the issues list, add a severity count summary. The backend emits severity values in **lowercase** (`"critical"`, `"major"`, `"minor"`). Replace the full issues rendering block with:
```jsx
      {ev.issues?.length > 0 && (() => {
        const sorted = [...ev.issues].sort((a,b)=>{
          const o={critical:0,major:1,minor:2}; return (o[a.severity]??3)-(o[b.severity]??3)
        })
        const counts = sorted.reduce((acc,i)=>{acc[i.severity]=(acc[i.severity]||0)+1;return acc},{})
        const summary = Object.entries(counts)
          .map(([s,n])=>`${n} ${s.charAt(0).toUpperCase()+s.slice(1)}`).join(' · ')
        return (
          <div>
            <p className="section-title" style={{marginTop:10}}>
              Issues <span style={{fontWeight:400,color:'var(--text3)',fontSize:11}}>({summary})</span>
            </p>
            {sorted.map((issue, i) => (
              <div key={i} className={`issue-item issue-${issue.severity?.toLowerCase()}`}>
                <span className="issue-severity">{issue.severity}</span>
                <span className="issue-dim">{issue.dimension}</span>
                <span className="issue-desc">{issue.description?.slice(0,200)}</span>
              </div>
            ))}
          </div>
        )
      })()}
```

Also update the "Judge Evaluation" section title (find `section-title` used for "Judge Evaluation" text) to read "Judge Score (第三方评分)":
```jsx
      <p className="section-title">Judge Score <span style={{fontSize:11,fontWeight:400,color:'var(--text3)'}}>（第三方评分）</span></p>
```

- [ ] **Step 3: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/frontend/src/components/JudgeScorePanel.jsx
git commit -m "feat: add scoring explanation note and severity summary to JudgeScorePanel"
```

---

## Task 4: Display Fix — Assess Score Labels (Required Before Task 5)

**Files:**
- Modify: `web/frontend/src/components/StageCard.jsx`
- Modify: `web/frontend/src/components/RecommendationPanel.jsx`

- [ ] **Step 1: Label quality ring in AssessOutput**

In `StageCard.jsx`, find `AssessOutput` (search for `function AssessOutput`). Find the quality ring div:
```jsx
      <div className={`quality-ring ${ringCls}`}>{Math.round(score * 100)}%</div>
      <p className="section-title">Identified Gaps</p>
```
Replace with:
```jsx
      <p className="section-title">Workflow Quality <span style={{fontSize:11,fontWeight:400,color:'var(--text3)'}}>（自评）</span></p>
      <div className={`quality-ring ${ringCls}`}>{Math.round(score * 100)}%</div>
      <p className="section-title" style={{marginTop:12}}>Identified Gaps</p>
```

- [ ] **Step 2: Label quality ring in RecommendationPanel**

In `RecommendationPanel.jsx`, find the "Quality Assessment" section:
```jsx
      {assess && (
        <div className="rec-section">
          <div className="rec-section-title">Quality Assessment</div>
```
Replace with:
```jsx
      {assess && (
        <div className="rec-section">
          <div className="rec-section-title">Workflow Quality <span style={{fontSize:11,fontWeight:400,color:'var(--text3)'}}>（自评）</span></div>
```

- [ ] **Step 3: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/frontend/src/components/StageCard.jsx web/frontend/src/components/RecommendationPanel.jsx
git commit -m "feat: label Workflow Quality and Judge Score distinctly in Assess stage"
```

---

## Task 5: Tooltips — InfoTooltip Component

**Files:**
- Create: `web/frontend/src/components/InfoTooltip.jsx`
- Modify: `web/frontend/src/index.css`

- [ ] **Step 1: Create InfoTooltip.jsx**

```jsx
// web/frontend/src/components/InfoTooltip.jsx
import { useState, useCallback } from 'react'

export default function InfoTooltip({ text }) {
  const [pos, setPos] = useState(null)

  const show = useCallback((e) => {
    const r = e.currentTarget.getBoundingClientRect()
    setPos({ top: r.bottom + 6, left: r.left })
  }, [])

  const hide = useCallback(() => setPos(null), [])

  return (
    <span className="info-tooltip-wrap" onMouseEnter={show} onMouseLeave={hide}>
      <span className="info-tooltip-icon">ⓘ</span>
      {pos && (
        <div className="info-tooltip-popover" style={{ top: pos.top, left: pos.left }}>
          {text}
        </div>
      )}
    </span>
  )
}
```

- [ ] **Step 2: Add CSS for tooltip**

Append to `web/frontend/src/index.css`:
```css
/* InfoTooltip */
.info-tooltip-wrap { position: relative; display: inline-flex; align-items: center; margin-left: 4px; }
.info-tooltip-icon { font-size: 11px; color: var(--text3); cursor: default; user-select: none; }
.info-tooltip-icon:hover { color: var(--text2); }
.info-tooltip-popover {
  position: fixed;
  z-index: 9999;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text2);
  line-height: 1.5;
  max-width: 280px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  pointer-events: none;
}
```

- [ ] **Step 3: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/frontend/src/components/InfoTooltip.jsx web/frontend/src/index.css
git commit -m "feat: add InfoTooltip component with fixed-position popover"
```

---

## Task 6: Tooltips — Add to Components and Stage Descriptions

**Files:**
- Modify: `web/frontend/src/components/StageCard.jsx`
- Modify: `web/frontend/src/components/JudgeScorePanel.jsx`
- Modify: `web/frontend/src/components/DecisionBadge.jsx`
- Modify: `web/frontend/src/components/RecommendationPanel.jsx`

- [ ] **Step 1: Add stage subtitles and tooltips in StageCard.jsx**

Add `import InfoTooltip from './InfoTooltip'` at the top of StageCard.jsx.

Define a constant near the top of the file (before the component functions):
```jsx
const STAGE_DESCRIPTIONS = {
  Ask: '将临床问题结构化为 PICO 格式，提取检索关键词',
  Acquire: '从证据库中检索相关文献段落，筛选最相关条目',
  Appraise: '评估证据质量和等级（GRADE），识别研究间冲突',
  Apply: '基于证据生成临床推荐意见及推荐强度',
  Assess: '自评推荐质量，识别证据缺口，决定是否需要回溯',
}

const TOOLTIPS = {
  PICO: '临床问题四要素：P=患者/病症, I=干预措施, C=对照, O=结局指标',
  GRADE: '证据质量分级体系：High→Moderate→Low→Very Low',
  CAVEATS: '使用本推荐意见时需注意的例外、限制或特殊情况',
  BACKTRACK: '当前阶段质量不足时，系统回到更早阶段重新执行',
  WORKFLOW_QUALITY: 'Assess agent 对整个 workflow 输出质量的自评分，独立于 Judge Score',
}
```

In the `StageCard` component's panel-header, add the stage description subtitle:
```jsx
      <div className="panel-header">
        <div>
          <span>{stageName}</span>
          {STAGE_DESCRIPTIONS[stageName] && (
            <div style={{fontSize:11,color:'var(--text3)',fontWeight:400,marginTop:2}}>{STAGE_DESCRIPTIONS[stageName]}</div>
          )}
        </div>
        {stage.status === 'running' && <span style={{fontSize:12,color:'var(--blue)'}}>⏳ Running…</span>}
        {call?.elapsed_s && <span style={{fontSize:11,color:'var(--text3)',marginLeft:'auto'}}>{call.elapsed_s}s</span>}
      </div>
```

In `AskOutput`, add InfoTooltip next to the "PICO" table header. Find the table and add:
```jsx
  return (
    <div>
      <div style={{display:'flex',alignItems:'center',gap:4,marginBottom:6,fontSize:12,color:'var(--text3)'}}>
        PICO Query <InfoTooltip text={TOOLTIPS.PICO} />
      </div>
      <table className="pico-table">
```

In `AssessOutput`, add InfoTooltip next to "Workflow Quality":
```jsx
      <p className="section-title">Workflow Quality <span style={{fontSize:11,fontWeight:400,color:'var(--text3)'}}>（自评）</span><InfoTooltip text={TOOLTIPS.WORKFLOW_QUALITY} /></p>
```

- [ ] **Step 2: Add tooltips in JudgeScorePanel.jsx**

Add `import InfoTooltip from './InfoTooltip'` at top.

Find the "Judge Score" section title and add tooltip:
```jsx
      <p className="section-title">Judge Score <span style={{fontSize:11,fontWeight:400,color:'var(--text3)'}}>（第三方评分）</span><InfoTooltip text="独立评估模块对当前阶段输出质量的打分，跨多个维度加权平均" /></p>
```

- [ ] **Step 3: Add tooltip in DecisionBadge.jsx**

Add `import InfoTooltip from './InfoTooltip'` at top.

**First, read `index.css` and confirm the current `.decision-row` CSS rule before editing** — the plan replaces the component root div class from `decision-row` to a plain `div`, which removes that class from the wrapper. If `.decision-row` has styles that should be preserved (border, padding, etc.), move them to a CSS rule on the inner badge span or inline style instead.

Then replace the component's return:
```jsx
  return (
    <div style={{marginTop:10}}>
      <p className="section-title" style={{display:'flex',alignItems:'center',gap:0}}>
        Scheduling Decision
        <InfoTooltip text="LLM 根据 Judge 评分和问题特征决定下一步动作（继续/重试/回溯/终止）" />
      </p>
```

- [ ] **Step 4: Add tooltip in RecommendationPanel.jsx**

Add `import InfoTooltip from './InfoTooltip'` at top.

Find the "Caveats" section title and add tooltip:
```jsx
          <div className="rec-section-title">Caveats <InfoTooltip text="使用本推荐意见时需注意的例外、限制或特殊情况" /></div>
```

Also find "Workflow Quality" section title:
```jsx
          <div className="rec-section-title">Workflow Quality <span style={{fontSize:11,fontWeight:400,color:'var(--text3)'}}>（自评）</span><InfoTooltip text="Assess agent 对整个 workflow 输出质量的自评分，独立于 Judge Score" /></div>
```

- [ ] **Step 5: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/components/StageCard.jsx web/frontend/src/components/JudgeScorePanel.jsx web/frontend/src/components/DecisionBadge.jsx web/frontend/src/components/RecommendationPanel.jsx
git commit -m "feat: add stage descriptions and term tooltips across components"
```

---

## Task 7: History Panel — Store Actions

**Files:**
- Modify: `web/frontend/src/store/workflowStore.js`

- [ ] **Step 1: Change `create` signature and add history helpers to workflowStore.js**

**First**, change the `create` call signature at line 26 from:
```js
export const useWorkflowStore = create((set) => ({
```
to:
```js
export const useWorkflowStore = create((set, get) => ({
```
This makes `get()` available in the factory scope (needed for `saveToHistory` and `loadFromHistory`).

**Then** add the following helper functions at the top of the file (before `create`):

```js
const HISTORY_KEY = 'truetruth_history'
const MAX_HISTORY = 20
const MAX_ENTRY_BYTES = 200_000

function pruneStagesForStorage(stages) {
  // Strip per-call logs to reduce size
  const pruned = {}
  for (const [name, stage] of Object.entries(stages)) {
    pruned[name] = {
      ...stage,
      calls: stage.calls.map(c => ({ ...c, logs: [] }))
    }
  }
  return pruned
}

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
}

function persistHistory(entries) {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(entries)) } catch {}
}
```

Then inside the `create((set, get) => ({` callback, add after the existing dispatch function:

```js
  history: loadHistory(),
  historyView: false,

  saveToHistory(status) {
    const state = get()
    const entry = {
      id: crypto.randomUUID(),
      question: state.question,
      timestamp: new Date().toISOString(),
      status,
      backtracks: state.backtracks,
      finalResult: state.finalResult,
      stages: null,
    }
    const withStages = { ...entry, stages: pruneStagesForStorage(state.stages) }
    const serialized = JSON.stringify(withStages)
    const chosen = serialized.length <= MAX_ENTRY_BYTES ? withStages : entry
    const history = [chosen, ...get().history].slice(0, MAX_HISTORY)
    persistHistory(history)
    set({ history })
  },

  loadFromHistory(entry) {
    set({
      historyView: true,
      question: entry.question,
      status: entry.status === 'error' ? 'error' : 'completed',
      stages: entry.stages || Object.fromEntries(
        ['Ask','Acquire','Appraise','Apply','Assess'].map(n => [n, { status: 'pending', calls: [] }])
      ),
      backtracks: entry.backtracks || [],
      finalResult: entry.finalResult,
      logs: [],
      error: null,
      currentAgent: null,
    })
  },

  exitHistoryView() {
    set({
      historyView: false,
      ...INITIAL,
      stages: Object.fromEntries(STAGE_NAMES.map(n => [n, makeStage()])),
    })
  },
```

Note: change the `create` call signature from `create((set) => ({` to `create((set, get) => ({` to allow `get()` access.

- [ ] **Step 2: Wire saveToHistory into dispatch**

Inside the `dispatch` function's switch statement, at the end of `WORKFLOW_COMPLETED` case:
```js
        case 'WORKFLOW_COMPLETED': {
          const newState = { status: 'completed', finalResult: payload, currentAgent: null }
          // Save to history (terminated if no recommendation)
          setTimeout(() => {
            get().saveToHistory(payload.recommendation ? 'completed' : 'terminated')
          }, 0)
          return newState
        }
```

And add `WORKFLOW_ERROR` history save:
```js
        case 'WORKFLOW_ERROR': {
          setTimeout(() => { get().saveToHistory('error') }, 0)
          return { status: 'error', error: payload.error, currentAgent: null }
        }
```

- [ ] **Step 3: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/frontend/src/store/workflowStore.js
git commit -m "feat: add history persistence to workflowStore (localStorage)"
```

---

## Task 8: History Panel — Sidebar Component and Layout

**Files:**
- Create: `web/frontend/src/components/HistorySidebar.jsx`
- Modify: `web/frontend/src/App.jsx`
- Modify: `web/frontend/src/index.css`

- [ ] **Step 1: Create HistorySidebar.jsx**

```jsx
// web/frontend/src/components/HistorySidebar.jsx
import { useWorkflowStore } from '../store/workflowStore'

const SIDEBAR_KEY = 'truetruth_sidebar_open'

function relativeTime(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
}

const STATUS_ICON = { completed: '✓', terminated: '⚠', error: '✗' }
const STATUS_COLOR = { completed: 'var(--green)', terminated: 'var(--orange)', error: 'var(--red)' }

export default function HistorySidebar({ open, onToggle }) {
  const { history, loadFromHistory, exitHistoryView, historyView } = useWorkflowStore()

  return (
    <div className={`history-sidebar ${open ? 'open' : 'closed'}`}>
      <div className="history-header">
        <span className="history-title">{open ? '历史记录' : ''}</span>
        <button className="history-toggle" onClick={onToggle} title={open ? '收起' : '展开历史'}>
          ☰
        </button>
      </div>
      {open && (
        <>
          {historyView && (
            <button className="history-back-btn" onClick={exitHistoryView}>← 新问题</button>
          )}
          {history.length === 0 && (
            <p style={{fontSize:12,color:'var(--text3)',padding:'12px 10px'}}>暂无历史记录</p>
          )}
          {history.map(entry => (
            <div
              key={entry.id}
              className={`history-item ${historyView ? '' : ''}`}
              onClick={() => loadFromHistory(entry)}
            >
              <div className="history-item-q">{entry.question.slice(0, 60)}{entry.question.length > 60 ? '…' : ''}</div>
              <div className="history-item-meta">
                <span style={{color: STATUS_COLOR[entry.status] || 'var(--text3)'}}>
                  {STATUS_ICON[entry.status] || '·'}
                </span>
                <span style={{color:'var(--text3)',fontSize:11}}>{relativeTime(entry.timestamp)}</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Add sidebar CSS**

Append to `web/frontend/src/index.css`:
```css
/* History Sidebar */
.history-sidebar {
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
  flex-shrink: 0;
  overflow: hidden;
}
.history-sidebar.open { width: 220px; }
.history-sidebar.closed { width: 36px; }
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 8px;
  border-bottom: 1px solid var(--border);
  min-height: 40px;
}
.history-title { font-size: 12px; font-weight: 600; color: var(--text2); white-space: nowrap; }
.history-toggle { background: none; border: none; color: var(--text3); cursor: pointer; font-size: 14px; padding: 2px 4px; }
.history-toggle:hover { color: var(--text); }
.history-back-btn {
  display: block; width: 100%; padding: 8px 10px; background: var(--bg3);
  border: none; border-bottom: 1px solid var(--border); color: var(--blue);
  font-size: 12px; cursor: pointer; text-align: left;
}
.history-back-btn:hover { background: var(--bg2); }
.history-item {
  padding: 10px; border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background 0.1s;
}
.history-item:hover { background: var(--bg3); }
.history-item-q { font-size: 12px; color: var(--text); line-height: 1.4; margin-bottom: 4px; }
.history-item-meta { display: flex; gap: 8px; align-items: center; font-size: 11px; }
```

- [ ] **Step 3: Integrate sidebar into App.jsx**

Add imports at top of App.jsx:
```jsx
import { useState } from 'react'  // already present
import HistorySidebar from './components/HistorySidebar'
```

Add sidebar open state (after the existing `useState` calls):
```jsx
  const [sidebarOpen, setSidebarOpen] = useState(
    () => localStorage.getItem('truetruth_sidebar_open') !== 'false'
  )

  function toggleSidebar() {
    const next = !sidebarOpen
    setSidebarOpen(next)
    localStorage.setItem('truetruth_sidebar_open', String(next))
  }
```

Also destructure `historyView` from the store:
```jsx
  const { status, stages, logs, backtracks, finalResult, error, historyView } = useWorkflowStore()
```

Wrap the existing `<div className="app">` contents in a flex layout:
```jsx
  return (
    <div className="app-shell">
      <HistorySidebar open={sidebarOpen} onToggle={toggleSidebar} />
      <div className="app">
        {/* ... all existing content unchanged ... */}
      </div>
    </div>
  )
```

In history view mode, disable the question form. Find the `<form>` element and add:
```jsx
      <form className="question-form" onSubmit={handleSubmit} style={historyView ? {opacity:0.5,pointerEvents:'none'} : {}}>
```

- [ ] **Step 4: Add app-shell CSS**

In `index.css`, add before the `.app` rule:
```css
.app-shell { display: flex; height: 100vh; overflow: hidden; }
.app { flex: 1; overflow-y: auto; min-width: 0; }
```

- [ ] **Step 5: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/components/HistorySidebar.jsx web/frontend/src/App.jsx web/frontend/src/index.css
git commit -m "feat: add collapsible history sidebar with localStorage persistence"
```

---

## Task 9: Span Retrieval — Schema Change

**Files:**
- Modify: `src/state/schema.py`

- [ ] **Step 1: Add key_sentences field to Evidence**

Read `src/state/schema.py` and find the `Evidence` dataclass. It currently ends with `full_text: Optional[str] = None`. Add after it:
```python
    key_sentences: Optional[str] = None  # extracted evidence span (local DB only)
```

- [ ] **Step 2: Verify import works**

```bash
cd /data/wuyuang/ebm5a && python3 -c "
from src.state.schema import Evidence
e = Evidence(title='test', source='test')
print('key_sentences default:', repr(e.key_sentences))
assert e.key_sentences is None
print('OK')
"
```
Expected: `key_sentences default: None` and `OK`

- [ ] **Step 3: Commit**

```bash
git add src/state/schema.py
git commit -m "feat: add key_sentences field to Evidence dataclass"
```

---

## Task 10: Span Retrieval — Extract Spans in local_evidence_db.py

**Files:**
- Modify: `src/tools/local_evidence_db.py`

- [ ] **Step 1: Add _extract_spans function**

After the `_rrf_fuse` function (before `search_local`), add:

```python
import re as _re

def _extract_spans(abstract_text: str, query_keywords: list, max_spans: int = 3, max_chars: int = 200) -> str | None:
    """Extract the most relevant sentence spans from an abstract.

    Adjacent sentences that both contain query keywords are merged into a single span.
    If >=60% of sentences are relevant, return the full abstract as one span.

    Args:
        abstract_text: The article abstract.
        query_keywords: Lowercase keyword tokens from the search query.
        max_spans: Maximum number of spans to return.
        max_chars: Maximum characters per span.

    Returns:
        Concatenated spans separated by ' … ', or None if no relevant sentences found.
    """
    if not abstract_text or not query_keywords:
        return None

    # Split into sentences on common delimiters
    sentences = [s.strip() for s in _re.split(r'(?<=[.!?。！？])\s+', abstract_text) if s.strip()]
    if not sentences:
        return None

    # Score each sentence by keyword overlap (case-insensitive)
    kw_set = {kw.lower() for kw in query_keywords if len(kw) > 2}
    scores = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for kw in kw_set if kw in sent_lower)
        scores.append(score)

    threshold = 1  # at least one keyword match

    # If >=60% of sentences match, return full abstract
    matching = sum(1 for s in scores if s >= threshold)
    if len(sentences) > 0 and matching / len(sentences) >= 0.6:
        return abstract_text[:max_chars * max_spans]

    # Merge adjacent high-scoring sentences into spans
    spans = []
    i = 0
    while i < len(sentences):
        if scores[i] >= threshold:
            # Start a new span; merge adjacent matching sentences
            span_sents = [sentences[i]]
            j = i + 1
            while j < len(sentences) and scores[j] >= threshold:
                span_sents.append(sentences[j])
                j += 1
            span_text = ' '.join(span_sents)[:max_chars]
            span_score = max(scores[i:j])
            spans.append((span_score, span_text))
            i = j
        else:
            i += 1

    if not spans:
        return None

    # Return top-N spans by score
    spans.sort(key=lambda x: x[0], reverse=True)
    return ' … '.join(text for _, text in spans[:max_spans])
```

- [ ] **Step 2: Call _extract_spans in search_local**

In `search_local`, after building each `Evidence` object (inside the loop), add span extraction. Find the `results.append(Evidence(...))` call and modify the surrounding code:

```python
    # Extract query keywords for span matching
    query_keywords = [t for t in tokens if len(t) > 2]  # reuse tokens from BM25

    results: List[Evidence] = []
    n = min(top_k, len(fused))
    for rank, (pmcid, _score) in enumerate(fused[:top_k]):
        a = articles.get(pmcid)
        if a is None:
            continue
        relevance = round(1.0 - (rank / max(n, 1)) * 0.9, 3) if n > 1 else 1.0
        abstract = a.get("abstract", "")
        key_sentences = _extract_spans(abstract, query_keywords)
        results.append(Evidence(
            title=a.get("title", ""),
            source=a.get("journal", "PMC"),
            pmid=a.get("pmid"),
            abstract=abstract,
            relevance_score=relevance,
            study_type=None,
            publication_date=a.get("publication_date"),
            grade_level=None,
            pmcid=pmcid,
            full_text=a.get("full_text"),
            key_sentences=key_sentences,
        ))

    return results
```

- [ ] **Step 3: Verify span extraction works**

```bash
cd /data/wuyuang/ebm5a && python3 -c "
from src.tools.local_evidence_db import _extract_spans
abstract = 'Preeclampsia is a serious condition. Magnesium sulfate is the drug of choice for seizure prevention. Other drugs may be used in mild cases. Blood pressure monitoring is essential. Regular urine protein tests should be performed.'
result = _extract_spans(abstract, ['magnesium', 'seizure', 'preeclampsia'])
print('span:', result)
assert result is not None
assert 'magnesium' in result.lower() or 'preeclampsia' in result.lower()
print('OK')
"
```
Expected: prints a span containing relevant sentences and `OK`.

- [ ] **Step 4: Commit**

```bash
git add src/tools/local_evidence_db.py
git commit -m "feat: add span-level evidence extraction to local_evidence_db"
```

---

## Task 11: Span Retrieval — acquire_agent.py Changes

**Files:**
- Modify: `src/agents/acquire_agent.py`

- [ ] **Step 1: Fix NameError — initialize search_query_used before try block**

At the start of the `execute` method in `AcquireAgent`, find the point just before the `try:` block that contains the search step. Add:
```python
        search_query_used = ""
```
This ensures the variable is always defined even if the try block raises before assignment, so the `except` handler can safely return `"search_query": search_query_used`.

Remove the old `"search_query": filtered_query` in the except block (line ~262) and replace with `"search_query": search_query_used`.

- [ ] **Step 2: Update _listwise_rank to prefer key_sentences**

Find the `_listwise_rank` method. Inside the candidate block construction, find `e.abstract[:150]` and replace with:
```python
e.key_sentences if e.key_sentences else e.abstract[:150]
```

- [ ] **Step 3: Verify import still works**

```bash
cd /data/wuyuang/ebm5a && python3 -c "
from src.agents.acquire_agent import AcquireAgent
print('import OK')
"
```
Expected: `import OK`

- [ ] **Step 4: Commit**

```bash
git add src/agents/acquire_agent.py
git commit -m "feat: use key_sentences in listwise ranking; fix latent NameError in exception handler"
```

---

## Task 12: Span Retrieval — judge_llm.py Exclusion

**Files:**
- Modify: `src/judge/judge_llm.py`

- [ ] **Step 1: Exclude key_sentences in Appraise branch**

Find the loop in the Appraise branch that does:
```python
                for ev in appraisal_d.get("evidence", []):
                    ev.pop("abstract", None)
                    ev.pop("full_text", None)
```
Add one line:
```python
                    ev.pop("key_sentences", None)
```

- [ ] **Step 2: Verify import**

```bash
cd /data/wuyuang/ebm5a && python3 -c "from src.judge.judge_llm import JudgeLLM; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/judge/judge_llm.py
git commit -m "feat: exclude key_sentences from Appraise judge prompt"
```

---

## Task 13: Span Retrieval — serializers.py

**Files:**
- Modify: `web/backend/serializers.py`

- [ ] **Step 1: Include key_sentences in serialize_evidence_list**

In `serialize_evidence_list`, add `key_sentences` to the dict:
```python
        result.append({
            "title": e.title,
            "pmid": getattr(e, "pmid", None),
            "pmcid": getattr(e, "pmcid", None),
            "source": getattr(e, "source", ""),
            "study_type": getattr(e, "study_type", None),
            "relevance_score": getattr(e, "relevance_score", 0.0),
            "grade_level": getattr(e, "grade_level", None),
            "abstract_preview": (getattr(e, "abstract", "") or "")[:200],
            "key_sentences": getattr(e, "key_sentences", None),
        })
```

- [ ] **Step 2: Verify**

```bash
cd /data/wuyuang/ebm5a && python3 -c "
from src.state.schema import Evidence
from web.backend.serializers import serialize_evidence_list
e = Evidence(title='Test', source='PMC', abstract='Hello world. This is a test.', key_sentences='Hello world.')
result = serialize_evidence_list([e])
print('key_sentences in output:', 'key_sentences' in result[0])
assert result[0]['key_sentences'] == 'Hello world.'
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add web/backend/serializers.py
git commit -m "feat: include key_sentences in evidence serializer output"
```

---

## Task 14: Span Retrieval — EvidenceTable.jsx

**Files:**
- Modify: `web/frontend/src/components/EvidenceTable.jsx`
- Modify: `web/frontend/src/index.css`

- [ ] **Step 1: Read current EvidenceTable.jsx**

```bash
cat /data/wuyuang/ebm5a/web/frontend/src/components/EvidenceTable.jsx
```

- [ ] **Step 2: Add key_sentences display**

In the evidence row, find the `<td className="ev-title">` cell. Inside that cell, after the title/link/badge line and before the closing `</td>`, replace the existing `<details>` abstract block with:
```jsx
              {/* key_sentences highlight — shown when span extraction found relevant sentences */}
              {e.key_sentences && (
                <div className="evidence-key-sentences">{e.key_sentences}</div>
              )}
              {e.abstract_preview && (
                <details style={{marginTop:4}}>
                  <summary style={{fontSize:11,color:'var(--text3)',cursor:'pointer'}}>
                    {e.key_sentences ? 'Context Preview' : 'Abstract Preview'}
                  </summary>
                  <div style={{fontSize:12,color:'var(--text2)',lineHeight:1.5,marginTop:4,paddingLeft:8}}>
                    {e.abstract_preview}
                  </div>
                </details>
              )}
```
This entire replacement stays inside the existing `<td className="ev-title">` — do not remove or restructure the `<td>` wrapper.

- [ ] **Step 3: Add CSS for key_sentences highlight**

Append to `web/frontend/src/index.css`:
```css
/* Key sentences evidence highlight */
.evidence-key-sentences {
  font-size: 12px;
  color: var(--text);
  line-height: 1.6;
  margin-top: 6px;
  padding: 6px 10px;
  background: rgba(59,130,246,0.08);
  border-left: 3px solid var(--blue);
  border-radius: 0 4px 4px 0;
}
```

- [ ] **Step 4: Build and verify**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/components/EvidenceTable.jsx web/frontend/src/index.css
git commit -m "feat: display key_sentences as highlighted evidence spans in EvidenceTable"
```

---

## Task 15: Rebuild Frontend and Restart Backend

- [ ] **Step 1: Final frontend build**

```bash
cd /data/wuyuang/ebm5a/web/frontend && npm run build 2>&1
```
Expected: `✓ built in ...` with no errors or warnings.

- [ ] **Step 2: Kill and restart backend**

```bash
pkill -f "uvicorn web.backend.app" 2>/dev/null || true
sleep 1
cd /data/wuyuang/ebm5a
uvicorn web.backend.app:app --port 8888 > /tmp/ebm_backend.log 2>&1 &
sleep 2
curl -s http://localhost:8888/api/health
```
Expected: `{"status":"ok",...}`

- [ ] **Step 3: Smoke test SSE**

```bash
cd /data/wuyuang/ebm5a
SESSION=$(curl -s -X POST http://localhost:8888/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"question":"妊娠期高血压需要做哪些实验室检查？"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "session: $SESSION"
curl -s -N --max-time 20 "http://localhost:8888/api/run?session_id=$SESSION" | head -30
```
Expected: `workflow_started` event followed by `agent_started` for Ask.

- [ ] **Step 4: Final commit**

```bash
git add -A
git status  # verify no untracked important files
git commit -m "chore: final build artifacts after web UI improvements"
```
