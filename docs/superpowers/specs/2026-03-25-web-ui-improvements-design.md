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
  "status": "completed | terminated | error",
  "stages": { ... },
  "backtracks": [...],
  "finalResult": { ... }
}
```

**Save trigger:** `saveToHistory()` is called in the Zustand store on three events:
- `WORKFLOW_COMPLETED` (status = `"completed"` if recommendation exists, `"terminated"` if null)
- `WORKFLOW_ERROR` (status = `"error"`)

**Storage budget:** Raw `stages` data can be large (evidence lists, per-call logs). Before saving, strip the per-call `logs` arrays (available in the LogConsole during live runs but not needed in history replay) and truncate long text fields. Target: ≤ 100 KB per entry. History is capped at 20 entries; oldest is dropped when the limit is exceeded. If `JSON.stringify` of an entry exceeds 200 KB after pruning, the entry is saved without the `stages` field (summary-only mode, showing only the final result).

**UI:** A collapsible left sidebar (~220px wide) lists past runs in reverse-chronological order. Each row shows:
- Question text (truncated to ~60 chars)
- Timestamp (relative: "2 hours ago")
- Status icon: ✓ Complete / ⚠ Terminated / ✗ Error

Clicking a history entry loads the stored state into the Zustand store in read-only mode (workflow cannot be re-run from this view, but all stage details, judge scores, and the final recommendation are visible). A "← New Question" button returns to the live view. The sidebar can be toggled with a ☰ button; collapse state is preserved in `localStorage` as `truetruth_sidebar_open`.

**Implementation files:**
- `web/frontend/src/store/workflowStore.js`: add `saveToHistory()` action (called on `WORKFLOW_COMPLETED` and `WORKFLOW_ERROR`), add `loadFromHistory(entry)` action, add `historyView: boolean` flag to distinguish read-only mode
- `web/frontend/src/App.jsx`: add `<HistorySidebar>` to layout, adjust grid to `[sidebar] [main]`
- `web/frontend/src/components/HistorySidebar.jsx`: new component

---

## 2. Contextual Tooltips and Stage Descriptions

### Problem
Technical terms (FAST-PATH, CAVEATS, PICO, GRADE, Judge dimensions, Scheduling Decision, Backtrack) are opaque to users unfamiliar with the EBM 5A framework. Stage cards give no overview of what each step does.

### Design

**Tooltip component:** A small `<InfoTooltip text="...">` component renders a `ⓘ` icon that shows a popover on hover. To avoid clipping inside scrolling containers, the popover uses `position: fixed` (computed via a `getBoundingClientRect()` call on mount of the hover event) rather than `position: absolute`. This ensures the popover always appears above all layout constraints. The component uses a single `useState` for the computed position, with `onMouseEnter`/`onMouseLeave` event handlers.

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
| Workflow Quality | Assess agent 对整个 workflow 输出质量的自评分，独立于 Judge Score |

Note: The "Workflow Quality" tooltip requires first adding a visible label "Workflow Quality (自评)" to the quality ring in `AssessOutput` (currently the ring has no label). This label is also required by Problem 4c.

**Implementation files:**
- `web/frontend/src/components/InfoTooltip.jsx`: new component (position: fixed popover)
- `web/frontend/src/components/StageCard.jsx`: add stage subtitle + tooltips; add "Workflow Quality (自评)" label to `AssessOutput` quality ring
- `web/frontend/src/components/JudgeScorePanel.jsx`: tooltip on "Judge Evaluation" header and dimension names
- `web/frontend/src/components/DecisionBadge.jsx`: tooltip on "Scheduling Decision"
- `web/frontend/src/components/RecommendationPanel.jsx`: tooltip on "Caveats"
- `web/frontend/src/index.css`: tooltip/popover styles

---

## 3. Span-Level Evidence Retrieval

### Problem
The local evidence DB currently retrieves articles as evidence candidates and passes them to the Acquire agent. With a small database (10 articles), the agent is forced to select from the same 10 articles every time, leading to artificially high selection counts. Clinical evidence should cite specific passages, not whole articles.

### Design

**Input surface clarification:** The current `search_local()` in `local_evidence_db.py` aggregates ChromaDB chunk hits back to article level. The span extraction operates on the article **abstract** (250–400 words), not on raw chunks, since that is the text currently stored on each `Evidence` object. This avoids changes to the ChromaDB retrieval path.

**Span extraction algorithm** (new function `_extract_spans(abstract_text, query_keywords)` in `local_evidence_db.py`):

```
1. Split abstract into sentences (on 。.!? boundaries)
2. Score each sentence: count of query_keywords it contains (case-insensitive)
3. threshold = 1 (at least one keyword match required; tune empirically)
4. Merge adjacent sentences that both score ≥ threshold into a single span
5. If ≥ 60% of sentences score ≥ threshold, return the full abstract as one span
6. Return top-3 spans ranked by (max sentence score in span), each capped at 200 chars
7. If no sentence scores ≥ threshold, return None (no span extracted)
```

**Evidence schema change** (`src/state/schema.py`): Add optional field:
```python
key_sentences: Optional[str] = None
```
The `abstract` field is kept (retains the full abstract for context display). `full_text` remains excluded from all prompts.

**`search_local()` change:** After building each `Evidence` object, call `_extract_spans(ev.abstract, query_keywords)` and assign the result to `ev.key_sentences`. The candidate pool remains article-level (10 articles); span extraction is a display/prompt enrichment step, not a re-ranking step. If span extraction yields no result for an article, the article is still returned (with `key_sentences=None`).

**Acquire agent changes** (`src/agents/acquire_agent.py`):
1. In `_listwise_rank`, the candidate block currently uses `e.abstract[:150]`. Change to use `e.key_sentences if e.key_sentences else e.abstract[:150]`, so the LLM sees the extracted span instead of a truncated abstract when available.
2. Fix pre-existing latent NameError: in the `except` handler of the search step (~line 262), `filtered_query` is referenced but only assigned in the PubMed branch. Since `_use_local_db()` currently always returns True this is never triggered, but change `filtered_query` → `search_query_used` to match the variable that is actually assigned in the local DB branch.

**Serializer change** (`web/backend/serializers.py`, function `serialize_evidence_list`): Include `key_sentences` in the serialized evidence dict (alongside `abstract`). This field is served in the `AGENT_COMPLETED` SSE event for the Acquire stage.

**Judge change** (`src/judge/judge_llm.py`): Add `ev.pop("key_sentences", None)` alongside the existing `ev.pop("full_text", None)` in the **Appraise stage** serialization only (the loop over `appraisal_d["evidence"]`). The Acquire stage's condensed evidence block is built field-by-field and already excludes `key_sentences` by construction — no change needed there.

**Frontend change** (`web/frontend/src/components/EvidenceTable.jsx`): When `key_sentences` is present, display it as the primary evidence text in a highlighted block (e.g., light blue background, left border accent). The existing `abstract_preview` field (200-char truncation, already sent by the serializer) serves as the collapsible "Context Preview" below. No full abstract is added to avoid payload bloat. When `key_sentences` is `null` or absent, `abstract_preview` is displayed directly as before (no highlighted block).

**Internal dependency order within Problem 3:**
1. `schema.py` — add `key_sentences` field
2. `local_evidence_db.py` — add `_extract_spans`, update `search_local`
3. `acquire_agent.py` — update `_listwise_rank` candidate block
4. `judge_llm.py` — add `key_sentences` exclusion
5. `serializers.py` — include `key_sentences` in output
6. `EvidenceTable.jsx` — render `key_sentences`

**Implementation files:**
- `src/state/schema.py`
- `src/tools/local_evidence_db.py`
- `src/agents/acquire_agent.py` (`_listwise_rank` candidate block only)
- `src/judge/judge_llm.py`
- `web/backend/serializers.py`
- `web/frontend/src/components/EvidenceTable.jsx`

---

## 4. Display Confusion Fixes

### 4a. Call Tab: Judge Pass vs. Scheduling Decision

**Problem:** A Call tab showing ✓ (Judge passed) alongside a subsequent retry creates confusion — users expect ✓ to mean "this call succeeded overall."

**Fix:** When `stage.calls.length > 1` (tabs are rendered), each tab displays two independent indicators:
- Left: Judge result — `✓` (green, `pass_threshold=true`) or `✗` (orange, false), or `·` (gray, judge not yet available)
- Right: Scheduling action icon — `→` proceed, `↺` retry, `↩` backtrack, `⚡` fastpath, or nothing if decision not yet received

Example: Call 1 tab shows `✓ ↺` (judge passed but scheduler chose to retry). Call 2 shows `✓ →` (passed and proceeded).

For single-call stages (no tabs rendered), no additional indicator is needed — the Judge Evaluation section below already shows the full score.

**Implementation files:**
- `web/frontend/src/components/StageCard.jsx`: update call tab render logic

### 4b. JudgeScorePanel: Score vs. Issues Explanation

**Problem:** A high overall score (e.g., 0.85) alongside a list of issues seems contradictory.

**Fix:** Add a one-line note below the score circle: "总分为各维度加权平均；Minor 问题不大幅影响分数，但仍列出供参考。" Sort issues by severity (Critical → Major → Minor) and show a severity count summary line (e.g., "1 Critical · 2 Minor") before the list.

**Implementation files:**
- `web/frontend/src/components/JudgeScorePanel.jsx`

### 4c. Assess Stage: Two Distinct Scores

**Problem:** Assess stage shows two numerical scores with no clear distinction — the Assess agent's `quality_score` (self-assessment of the workflow) and the Judge's `overall_score` (evaluation of the Assess agent's work).

**Fix:** Label them explicitly:
- `AssessOutput` in `StageCard.jsx`: quality ring labeled **"Workflow Quality (自评)"**
- `JudgeScorePanel` below the divider: already titled "Judge Evaluation" — ensure the header reads **"Judge Score (第三方评分)"**
- In `RecommendationPanel.jsx` (final banner): the "Quality Assessment" section also renders a quality ring — add the same "Workflow Quality (自评)" label there for consistency.

**Implementation files:**
- `web/frontend/src/components/StageCard.jsx` (`AssessOutput` section)
- `web/frontend/src/components/JudgeScorePanel.jsx` (header label)
- `web/frontend/src/components/RecommendationPanel.jsx` (Quality Assessment label)

---

## 5. Branding: TrueTruth

### Problem
The title "EBM 5A" is internal project nomenclature, not a product name. The header is small relative to modern AI application standards.

### Design

**Name change:** All occurrences of "EBM 5A" → "TrueTruth" in the UI, including:
- `App.jsx` header text
- `web/frontend/index.html` `<title>` tag
- `web/backend/app.py` `FastAPI(title=...)` parameter

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
- `web/frontend/src/App.jsx`
- `web/frontend/index.html`
- `web/backend/app.py`
- `web/frontend/src/index.css` (`.header` height and title font-size)

---

## Implementation Order

Problems 1–5 are independent at the problem level. Suggested sequence:

1. **Problem 5** (Title/branding) — trivial
2. **Problem 4** (Display fixes) — frontend-only, low risk
3. **Problem 2** (Tooltips) — frontend-only, additive; depends on Problem 4c adding the "Workflow Quality" label first
4. **Problem 1** (History panel) — moderate complexity, localStorage only
5. **Problem 3** (Span retrieval) — backend + frontend, highest complexity; must follow the internal dependency order listed in that section

---

## Out of Scope

- Redesigning the overall layout or color scheme
- Multi-user / server-side session persistence
- Sentence-level re-indexing of the ChromaDB vector store (span extraction operates on abstracts at query time)
- Exporting results to PDF/Word (noted for future consideration)
