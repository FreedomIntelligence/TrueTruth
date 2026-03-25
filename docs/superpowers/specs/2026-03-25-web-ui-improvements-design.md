# Web UI Improvements Design

**Date:** 2026-03-25
**Project:** TrueTruth (formerly EBM 5A)
**Scope:** Five targeted improvements to the clinical decision support web interface, identified after initial user testing.

---

## 1. History Panel (localStorage Persistence)

### Problem
When a new question is submitted, the previous run's results are lost. There is no way to review a prior question without re-running it.

### Design

**Storage:** Completed workflow runs are serialized to `localStorage` under the key `truetruth_history`. Each entry stores:
```json
{
  "id": "<uuid>",
  "question": "...",
  "timestamp": "ISO-8601",
  "stages": { ... },
  "backtracks": [...],
  "finalResult": { ... }
}
```
The `stages` snapshot captures the full call history (outputs, evaluations, decisions) so it can be fully replayed in the UI. History is capped at 20 entries (oldest dropped when limit is exceeded).

**UI:** A collapsible left sidebar (~220px wide) lists past runs in reverse-chronological order. Each row shows:
- Question text (truncated to ~60 chars)
- Timestamp (relative: "2 hours ago")
- Status icon: ✓ Complete / ⚠ Terminated / ✗ Error

Clicking a history entry loads the stored state into the Zustand store in read-only mode (workflow cannot be re-run from this view, but all stage details, judge scores, and logs are visible). A "← New Question" button returns to the live view. The sidebar can be toggled with a ☰ button; state is preserved in localStorage as `truetruth_sidebar_open`.

**Implementation files:**
- `workflowStore.js`: add `saveToHistory()` action (called on `WORKFLOW_COMPLETED` and early termination), add `loadFromHistory(entry)` action
- `App.jsx`: add `<HistorySidebar>` component, adjust main layout to `[sidebar] [main]`
- `components/HistorySidebar.jsx`: new component

---

## 2. Contextual Tooltips and Stage Descriptions

### Problem
Technical terms (FAST-PATH, CAVEATS, PICO, GRADE, Judge dimensions, Scheduling Decision, Backtrack) are opaque to users unfamiliar with the EBM 5A framework. Stage cards give no overview of what each step does.

### Design

**Tooltip component:** A small `<InfoTooltip text="...">` component renders a `ⓘ` icon that shows a popover on hover (or tap on mobile). Implemented in pure CSS (no external library) using `position: absolute` and `:hover` CSS to avoid JS overhead.

**Stage header descriptions:** Each stage card gets a one-line subtitle explaining its role:
- **Ask** — "将临床问题结构化为 PICO 格式，提取检索关键词"
- **Acquire** — "从证据库中检索相关文献段落，筛选最相关条目"
- **Appraise** — "评估证据质量和等级（GRADE），识别研究间冲突"
- **Apply** — "基于证据生成临床推荐意见及推荐强度"
- **Assess** — "自评推荐质量，识别证据缺口，决定是否需要回溯"

**Term glossary (tooltip text):**

| Term | Tooltip |
|------|---------|
| FAST-PATH | 当评分通过且无重大问题时，调度器自动跳过 LLM 决策直接进入下一阶段 |
| PICO | 临床问题四要素：P=患者/病症, I=干预措施, C=对照, O=结局指标 |
| GRADE | 证据质量分级体系：High→Moderate→Low→Very Low |
| Caveats | 使用本推荐意见时需注意的例外、限制或特殊情况 |
| Backtrack | 当前阶段质量不足时，系统回到更早阶段重新执行 |
| Scheduling Decision | LLM 根据 Judge 评分和问题特征决定下一步动作（继续/重试/回溯/终止）|
| Judge Score | 独立评估模块对当前阶段输出质量的打分，跨多个维度加权平均 |
| Quality Score (Assess) | Assess agent 对整个 workflow 输出质量的自评分，独立于 Judge Score |

**Implementation files:**
- `components/InfoTooltip.jsx`: new component
- `components/StageCard.jsx`: add stage subtitle + tooltips on section titles
- `components/JudgeScorePanel.jsx`: tooltip on "Judge Evaluation" header and dimension names
- `components/DecisionBadge.jsx`: tooltip on "Scheduling Decision"
- `components/RecommendationPanel.jsx`: tooltip on "Caveats"
- `index.css`: tooltip styles

---

## 3. Span-Level Evidence Retrieval

### Problem
The local evidence DB currently retrieves articles as evidence candidates and passes them to the Acquire agent. With a small database (10 articles), the agent is forced to select from the same 10 articles every time, leading to artificially high selection counts. Clinical evidence should cite specific passages, not whole articles.

### Design

**Span extraction algorithm** (added to `local_evidence_db.py`):

```
For each retrieved chunk:
  1. Split chunk into sentences (split on。/./!/?)
  2. Score each sentence with BM25 against the query keywords
  3. Merge adjacent sentences where both score > threshold into a span
  4. If >60% of sentences in the chunk score above threshold, return whole chunk as one span
  5. Return top-3 spans from this chunk (by max sentence score within span), max 200 chars each
```

**Evidence schema change** (`schema.py`): Add optional field `key_sentences: Optional[str] = None` — the extracted span text. The `abstract` field retains the chunk-level context.

**`search_local()` output change:** Returns Evidence objects where `key_sentences` contains the extracted span and `abstract` contains the surrounding chunk context (for display). `full_text` is still excluded from prompts.

**Acquire agent change:** The evidence list passed to the LLM now surfaces `key_sentences` rather than `abstract`, focusing the LLM on specific passages. The candidate pool is now spans (potentially multiple per article), not articles, so with 10 articles × up to 3 spans each, there are up to 30 candidates.

**Frontend change:** `EvidenceTable.jsx` shows `key_sentences` as the primary evidence text (highlighted in a distinct color), with the chunk abstract collapsible below as context.

**Implementation files:**
- `src/tools/local_evidence_db.py`: add `_extract_spans(chunk_text, query)` function, update `search_local()` return
- `src/state/schema.py`: add `key_sentences` field
- `src/agents/acquire_agent.py`: update evidence serialization to prefer `key_sentences`
- `src/judge/judge_llm.py`: exclude `key_sentences` from Appraise judge input if too long
- `web/frontend/src/components/EvidenceTable.jsx`: render `key_sentences` prominently
- `web/backend/serializers.py`: include `key_sentences` in serialized evidence

---

## 4. Display Confusion Fixes

### 4a. Call Tab: Judge Pass vs. Scheduling Decision

**Problem:** A Call tab showing ✓ (Judge passed) alongside a subsequent retry creates confusion — users expect ✓ to mean "this call succeeded overall."

**Fix:** The call tab displays two independent indicators:
- Left: Judge result — `✓` (green, pass_threshold=True) or `✗` (orange, fail)
- Right: Scheduling action icon — `→` (proceed), `↺` (retry), `↩` (backtrack), `⚡` (fastpath)

Example: Call 1 might show `✓ ↺` (judge passed but scheduler chose to retry for quality reasons).

### 4b. JudgeScorePanel: Score vs. Issues Explanation

**Problem:** A high overall score (e.g., 0.85) alongside a list of issues seems contradictory.

**Fix:** Add a one-line note below the score circle: "总分为各维度加权平均；Minor 问题不大幅影响分数，但仍列出供参考。" Also sort issues by severity (Critical → Major → Minor) and show severity counts as a summary line before the list.

### 4c. Assess Stage: Two Distinct Scores

**Problem:** Assess stage shows two numerical scores with no clear distinction — the Assess agent's `quality_score` (self-assessment of the workflow) and the Judge's `overall_score` (evaluation of the Assess agent's work).

**Fix:** Label them explicitly:
- Assess output section: **"Workflow Quality (自评)"** with the quality ring
- Judge Evaluation section: **"Judge Score (第三方评分)"** with the judge circle

Visually separate them with a horizontal rule and distinct section headers.

**Implementation files:**
- `components/StageCard.jsx`: update call tab render, add dual indicator
- `components/JudgeScorePanel.jsx`: add explanatory note, sort issues, add severity summary
- `components/AssessOutput` (in StageCard.jsx): label quality ring as "Workflow Quality"

---

## 5. Branding: TrueTruth

### Problem
The title "EBM 5A" is internal project nomenclature, not a product name. The header is small relative to modern AI application standards.

### Design

**Name change:** All occurrences of "EBM 5A" → "TrueTruth" in the UI. The document `<title>` also updates.

**Header redesign:**
```
┌─────────────────────────────────────────────────────────────────┐
│  TrueTruth                                    [Complete] [Error] │
│  AI-Powered Clinical Evidence Synthesis                          │
└─────────────────────────────────────────────────────────────────┘
```
- "TrueTruth": 36px, bold, white
- Subtitle: 13px, muted gray, italic
- Status badges right-aligned
- Header height increases from ~48px to ~72px

**Implementation files:**
- `App.jsx`: update header JSX, rename title text
- `index.html`: update `<title>` tag
- `index.css`: update `.header` styles

---

## Implementation Order

These changes are independent and can be implemented in any order. Suggested sequence based on risk/complexity:

1. **Problem 5** (Title) — trivial, 5 min
2. **Problem 4** (Display fixes) — frontend-only, low risk
3. **Problem 2** (Tooltips) — frontend-only, additive
4. **Problem 1** (History panel) — moderate complexity, localStorage only
5. **Problem 3** (Span retrieval) — backend + frontend, highest complexity

---

## Out of Scope

- Redesigning the overall layout or color scheme
- Multi-user / server-side session persistence
- Sentence-level re-indexing of the ChromaDB vector store (span extraction is done at query time)
- Exporting results to PDF/Word (noted for future consideration)
