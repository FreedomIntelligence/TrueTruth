# EBM 5A System Prompt Flexibility Improvement Design

**Date**: 2026-02-25
**Design Type**: System Enhancement
**Target**: Agent/Judge/Scheduling Prompt Optimization
**Status**: Design Approved

---

## 1. Background and Motivation

### 1.1 System Overview

The EBM 5A Clinical Decision Support System is a multi-agent ReAct-based system that processes clinical questions through five stages:
- **Ask**: Extract PICO query from natural language question
- **Acquire**: Search evidence from PubMed
- **Appraise**: Evaluate evidence quality using GRADE framework
- **Apply**: Generate clinical recommendation
- **Assess**: Quality assessment of final recommendation

Each stage involves three LLM calls:
1. **Agent execution**: Perform stage-specific task
2. **Judge LLM evaluation**: Assess output quality with dimensional scoring
3. **Scheduling LLM decision**: Decide next action (proceed/backtrack/terminate)

### 1.2 Current System Goals

1. **Runtime Efficiency**: Minimize time from question input to final answer
2. **Answer Quality**:
   - **Primary (Most Important)**: Preserve model's native reasoning capabilities
     - Avoid over-engineering that restricts model flexibility
     - Prevent catastrophic forgetting from excessive prompt constraints
     - Maintain tool-calling accuracy and appropriate boundaries
   - **Secondary**: Ensure strict evidence-recommendation alignment per EBM principles

### 1.3 Key Challenge

**How to improve answer quality when specialized Agent LLMs are not yet trained, while maintaining model flexibility and system efficiency?**

---

## 2. Current System Assessment

### 2.1 Architecture Evaluation

**Strengths**:
- Clear separation of concerns (5A stages + Judge + Scheduling)
- Comprehensive quality control (dimensional scoring, gate system)
- Complete audit trail for clinical decision tracking

**Identified Issues**:

#### Issue A: Over-strict Judge Evaluation System
- Fixed 5-tier scoring (0, 0.25, 0.5, 0.75, 1.0) limits granularity
- Directive language: "必须回退" (must backtrack) removes LLM judgment
- May trigger unnecessary backtracks, reducing efficiency

#### Issue B: Rigid Agent Prompts (Primary Issue)
- Command-style language: "Return your response as JSON"
- Lacks acknowledgment of model's reasoning process
- Direct task assignment without engaging clinical reasoning capabilities
- May restrict model's native inference abilities

#### Issue C: Heavy Architecture
- 3 LLM calls per stage (Agent + Judge + Scheduling)
- Normal workflow: 15 calls, with backtracks: 20-30 calls
- Significant latency and token cost

#### Issue D: Evidence-Recommendation Alignment
- Current prompts don't strongly emphasize evidence support
- Secondary priority compared to preserving model capabilities

**Priority Ranking**: B > A > C ≈ D

### 2.2 Constraint Analysis

**Hard Constraints**:
1. **Latency & Token Cost**: Cannot significantly increase waiting time or token usage
2. **EBM Framework Compliance**: Reasoning must stay within evidence-based medicine methodology
   - Cannot allow unconstrained free reasoning
   - Must prevent reinforcement of incorrect medical logic
3. **ReAct Architecture**: Must maintain 5A + Judge + Scheduling structure

---

## 3. Solution Approach Selection

### 3.1 Considered Approaches

#### Approach 1: Lightweight Tone Adjustment (SELECTED)
**Core Idea**: Change prompt tone without structural changes, zero/minimal token increase

**Specific Changes**:
- **Agent Prompts**: Command-style → Guidance-style, acknowledge reasoning
- **Judge Prompts**: Fixed tiers → Continuous scoring ranges, "must" → "suggest"
- **Scheduling Prompts**: Decision matrix as "strict rules" → "reference guide"

**Trade-offs**:
- ✅ Token increase: <5% (negligible)
- ✅ Latency increase: None
- ✅ Risk: Very low (structure unchanged)
- ⚠️ Flexibility gain: Medium (mainly "feel" improvement)

#### Approach 2: Precision-Guided Injection
**Core Idea**: Add brief guiding questions only at key reasoning stages

**Specific Changes**:
- Keep Ask/Acquire simple (information extraction)
- Add 2-3 guiding questions for Appraise/Apply (e.g., "Does evidence quality match recommendation strength?")
- Simplify Judge dimension descriptions
- Compress Scheduling matrix explanation

**Trade-offs**:
- ⚠️ Token increase: 15-20% (mainly in Appraise/Apply)
- ⚠️ Latency increase: 10-15%
- ✅ Flexibility gain: High (true reasoning space)
- ⚠️ Risk: Medium (needs validation for EBM compliance)

#### Approach 3: Layered Simplification
**Core Idea**: Drastically simplify Judge/Scheduling, let Agents handle more judgment

**Trade-offs**:
- ✅ Token decrease: 20-30%
- ✅ Latency decrease: 15-20%
- ✅ Flexibility gain: Highest
- ❌ Risk: High (weakened quality control, may need more human review)

### 3.2 Decision: Approach 1 + Potential Hybrid

**Primary Choice**: Approach 1 (Lightweight Tone Adjustment)

**Rationale**:
1. **Zero-risk startup**: No structural changes, won't break existing system
2. **Minimal cost**: Near-zero token/latency increase
3. **Iterative-friendly**: Can implement Approach 1 first, then selectively add Approach 2 elements
4. **Constraint-compliant**: Fully meets "no token increase" and "maintain EBM compliance" requirements

**Future Option**: Approach 1 + Approach 2 Hybrid
- Use Approach 1 for most components
- Add Approach 2 guiding questions only for Apply stage (most critical reasoning)
- Only if willing to accept 15% token increase

---

## 4. Detailed Design Specification

### 4.1 Design Principles

#### Principle 1: Command-style → Guidance-style
- Old: `"Your task is to..."`, `"Return JSON"`
- New: `"Please based on..."`, `"Based on your clinical reasoning, provide..."`

#### Principle 2: Hard Rules → Reference Guidelines
- Old: `"必须回退"`, `"0.75 means..."`
- New: `"通常建议..."`, `"0.7-0.85 indicates...consider..."`

#### Principle 3: Fixed Tiers → Flexible Ranges
- Old: Can only score 0/0.25/0.5/0.75/1.0
- New: Can score any value like 0.72, 0.83

#### Principle 4: Acknowledge Reasoning Process
- Old: Directly request output
- New: Acknowledge model will think first, then output

### 4.2 Agent Prompts Modification

**Modification Scope**: 5 files
- `ask_agent.txt`
- `acquire_agent.txt`
- `appraise_agent.txt`
- `apply_agent.txt`
- `assess_agent.txt`

#### Example 1: Ask Agent

**Before**:
```
You are a clinical question refinement expert. Your task is to convert a natural language clinical question into a structured PICO format.

PICO stands for:
- P (Patient/Problem): Who is the patient or what is the problem?
- I (Intervention): What is the main intervention or exposure?
- C (Comparison): What is the alternative or comparison?
- O (Outcome): What are the relevant outcomes?

Clinical Question: {question}

{backtrack_context}

Return your response as a JSON object:
{{
  "patient": "description of patient/problem",
  "intervention": "main intervention",
  "comparison": "comparison or alternative",
  "outcome": "relevant outcomes",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Be specific and use medical terminology where appropriate.
```

**After**:
```
You are a clinical question refinement expert. Please analyze the following clinical question and structure it into PICO format based on your clinical reasoning.

PICO framework:
- P (Patient/Problem): The target patient population or clinical problem
- I (Intervention): The intervention or exposure being considered
- C (Comparison): The alternative or comparison group
- O (Outcome): The clinically relevant outcomes

Clinical Question: {question}

{backtrack_context}

Based on your analysis, provide a structured PICO query as JSON:
{{
  "patient": "description of patient/problem",
  "intervention": "main intervention",
  "comparison": "comparison or alternative",
  "outcome": "relevant outcomes",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Use specific medical terminology where appropriate to facilitate evidence search.
```

**Key Changes**:
- `"Your task is to convert"` → `"Please analyze...based on your clinical reasoning"`
- `"Return your response"` → `"Based on your analysis, provide"`
- `"Be specific"` → `"Use specific...to facilitate..."` (explains purpose, not just commands)

#### Example 2: Apply Agent

**Before**:
```
You are a clinical recommendation expert. Based on the appraised evidence, generate a clinical recommendation.

Original Question: {question}

Evidence Summary:
{evidence_summary}

Overall Appraisal: {appraisal_summary}

Generate a clinical recommendation with:
- Clear recommendation text
- Strength: "Strong" or "Weak"
- Rationale explaining the recommendation
- Caveats or limitations

Return your response as JSON:
{{
  "recommendation": "clear recommendation text",
  "strength": "Strong" or "Weak",
  "rationale": "explanation of the recommendation",
  "caveats": ["caveat1", "caveat2", ...]
}}
```

**After**:
```
You are a clinical recommendation expert. Please synthesize the appraised evidence to formulate a clinical recommendation, considering both the evidence quality and clinical applicability.

Original Question: {question}

Evidence Summary:
{evidence_summary}

Overall Appraisal: {appraisal_summary}

Based on your clinical judgment and the evidence above, provide a recommendation that includes:
- Clear, actionable recommendation text
- Strength: "Strong" or "Weak" (aligned with evidence quality)
- Rationale explaining your reasoning
- Important caveats or limitations for clinical application

Please structure your recommendation as JSON:
{{
  "recommendation": "clear recommendation text",
  "strength": "Strong" or "Weak",
  "rationale": "explanation of the recommendation",
  "caveats": ["caveat1", "caveat2", ...]
}}
```

**Key Changes**:
- `"generate a clinical recommendation"` → `"synthesize...to formulate...considering..."`
- `"Generate a recommendation with"` → `"Based on your clinical judgment...provide a recommendation that includes"`
- `"Return your response"` → `"Please structure your recommendation"`
- Added parenthetical guidance: `"(aligned with evidence quality)"` - provides direction without rigidity

#### Other Agents Modification Principles

**Acquire Agent**:
- Emphasize: "construct effective search strategy based on PICO" vs. "generate keywords"
- Tone: `"Please formulate search queries"` vs. `"Generate queries"`

**Appraise Agent**:
- Emphasize: "apply GRADE framework for evaluation" vs. "apply GRADE"
- Tone: `"Based on your appraisal"` vs. `"Rate the evidence"`

**Assess Agent**:
- Emphasize: "holistically evaluate recommendation quality" vs. "check completeness"
- Tone: `"Consider whether"` vs. `"Check if"`

**Token Impact**:
- Per Agent prompt increase: 10-20 tokens
- 5 Agents total increase: 50-100 tokens
- Percentage of total workflow: <3%

### 4.3 Judge Prompts Modification

**Modification Scope**: 5 files in `src/config/prompts/judge/`
- `ask_judge.txt`
- `acquire_judge.txt`
- `appraise_judge.txt`
- `apply_judge.txt`
- `assess_judge.txt`

#### Change 1: Scoring Standard (Fixed Tiers → Continuous Ranges)

**Before** (Ask Judge - PICO Completeness dimension):
```
### 1. PICO完整性 (pico_completeness, 权重35%)
- 评价标准：PICO四要素（Patient/Intervention/Comparison/Outcome）是否都明确提取
- 1.0: 所有四个要素都清晰明确
- 0.75: 三个要素明确，一个要素略显模糊
- 0.5: 两个要素明确，其他要素缺失或模糊
- 0.25: 只有一个要素明确
- 0.0: 所有要素都缺失或极度模糊
```

**After**:
```
### 1. PICO完整性 (pico_completeness, 权重35%)
- 评价标准：PICO四要素（Patient/Intervention/Comparison/Outcome）是否都明确提取
- 评分指南：
  - 0.9-1.0: 所有四个要素都清晰明确
  - 0.7-0.89: 三个要素明确，一个要素略显模糊但可用
  - 0.5-0.69: 两个要素明确，其他要素需要改进
  - 0.25-0.49: 只有一个要素明确，严重影响检索
  - 0.0-0.24: 要素缺失或极度模糊
- 请基于实际情况在0-1范围内给出合理评分
```

**Key Changes**:
- Fixed values → Scoring ranges
- Added qualifiers: "但可用" (but usable), "需要改进" (needs improvement)
- Added guidance at end: `"请基于实际情况在0-1范围内给出合理评分"`

#### Change 2: Issue Severity Definition

**Before**:
```
## 问题严重程度定义
- **critical（致命）**: 必须立即回退修复，否则会导致错误的临床推荐
  - 例如：PICO要素严重缺失（缺少P或I或O）
  - 例如：关键词完全错误，会检索到无关文献
- **major（重大）**: 显著影响质量，强烈建议回退修复
  - 例如：某个PICO要素模糊不清
  - 例如：关键词过于宽泛，会检索到大量无关文献
- **minor（轻微）**: 可以改进但不影响整体质量，可以继续
  - 例如：关键词可以更精确
  - 例如：某些细节可以补充
```

**After**:
```
## 问题严重程度定义
请基于问题对最终临床推荐的影响程度判断严重性：

- **critical（致命）**: 严重缺陷，会直接导致错误的临床推荐
  - 例如：PICO核心要素严重缺失（如缺少P或I或O）
  - 例如：关键词完全错误，会检索到无关文献
  - 影响：如不修复，后续流程无法产生可靠结果

- **major（重大）**: 显著问题，可能影响推荐质量
  - 例如：某个PICO要素模糊不清
  - 例如：关键词过于宽泛，可能混入大量无关文献
  - 影响：建议修复以提升整体质量

- **minor（轻微）**: 可改进之处，但不影响核心质量
  - 例如：关键词可以更精确
  - 例如：某些细节可以补充
  - 影响：可以继续，后续阶段可以补偿
```

**Key Changes**:
- Added guidance at start: `"请基于问题对最终临床推荐的影响程度判断严重性"`
- `"必须立即回退修复"` → `"如不修复，后续流程无法产生可靠结果"` (describe consequence, not command action)
- `"强烈建议回退修复"` → `"建议修复以提升整体质量"`
- Added "影响" (impact) explanation for each severity level

#### Change 3: Apply Judge Example

**Before** (Strength Appropriateness dimension):
```
### 2. 推荐强度合理性 (strength_appropriateness, 权重35%)
- 评价标准：推荐强度等级是否与证据质量相匹配
- 1.0: 推荐强度与证据质量完全匹配
- 0.75: 推荐强度基本合理，略有偏差
- 0.5: 推荐强度与证据质量不太匹配
- 0.25: 推荐强度严重不匹配（如低质量证据给强推荐）
- 0.0: 推荐强度完全不合理
```

**After**:
```
### 2. 推荐强度合理性 (strength_appropriateness, 权重35%)
- 评价标准：推荐强度等级是否与证据质量相匹配
- 评分指南：
  - 0.9-1.0: 推荐强度与证据质量匹配良好
  - 0.7-0.89: 推荐强度基本合理，有轻微偏差但可接受
  - 0.5-0.69: 推荐强度与证据质量不够匹配，需要调整
  - 0.25-0.49: 明显不匹配（如中低质量证据给强推荐）
  - 0.0-0.24: 严重不合理，与EBM原则相悖
- 请综合考虑证据质量、一致性、临床重要性后评分
```

**Key Changes**:
- Fixed values → Ranges
- Added degree qualifiers: "良好" (good), "可接受" (acceptable), "需要调整" (needs adjustment)
- Added guidance at end: `"请综合考虑证据质量、一致性、临床重要性后评分"`

#### Unified Changes Across All Judge Prompts

Apply to all 5 Judge files:
1. **Scoring standards**: Fixed tiers → Scoring ranges
2. **Issue severity**: Command-style → Consequence-description style
3. **Evaluation requirements**: Add guidance `"请基于...综合判断"`

**Token Impact**:
- Per Judge prompt increase: 20-40 tokens
- 5 Judges total increase: 100-200 tokens
- Percentage of total workflow: <5%

### 4.4 Scheduling Prompt Modification

**Modification Scope**: 1 file
- `src/config/prompts/scheduling_llm.txt`

#### Change 1: Opening Guidance

**Before**:
```
你是EBM 5A临床决策支持系统的调度协调器。你的任务是基于当前阶段的观察结果（observe），决定下一步应该采取什么行动。
```

**After**:
```
你是EBM 5A临床决策支持系统的调度协调器。请基于当前阶段的观察结果（observe）和整体workflow状态，运用你的推理能力判断下一步最合理的行动。
```

**Key Changes**:
- `"你的任务是...决定"` → `"请基于...运用你的推理能力判断"`
- Emphasize reasoning vs. task execution

#### Change 2: Decision Matrix

**Before**:
```
#### 3.3 决策矩阵（严格遵守）

| 问题严重度 | 剩余预算充足 (>10步) | 剩余预算紧张 (5-10步) | 剩余预算极少 (<5步) |
|-----------|---------------------|---------------------|-------------------|
| Critical  | 必须回退/重试         | 必须回退/重试         | 回退/请求人类介入   |
| Major     | 强烈建议回退          | 权衡收益后决定        | 倾向于继续/人类介入 |
| Minor     | **继续**（不回退）    | **继续**            | **继续**          |

**重要**：
- 如果**所有问题都是Minor**且**整体评分通过**，则**必须选择proceed**
- Minor问题不应触发回退，除非有多个Minor问题累积导致整体评分未通过
- 医疗场景需要高质量，但过度追求完美会导致效率低下和资源浪费
```

**After**:
```
#### 3.3 决策参考矩阵

| 问题严重度 | 剩余预算充足 (>10步) | 剩余预算紧张 (5-10步) | 剩余预算极少 (<5步) |
|-----------|---------------------|---------------------|-------------------|
| Critical  | 通常应回退/重试       | 通常应回退/重试       | 考虑回退或请求人类介入 |
| Major     | 建议回退             | 权衡收益后决定        | 倾向于继续或人类介入 |
| Minor     | **继续**             | **继续**            | **继续**          |

**判断原则**：
- 如果**所有问题都是Minor**且**整体评分通过**，通常应选择proceed
- Minor问题一般不触发回退，除非多个Minor问题累积影响整体质量
- 医疗场景对质量要求高，但也需考虑效率和资源合理利用
- 请基于具体情况综合判断，矩阵仅供参考
```

**Key Changes**:
- Title: `"（严格遵守）"` → removed
- Matrix content: `"必须"` → `"通常应"`，`"强烈建议"` → `"建议"`
- Section title: `"重要"` → `"判断原则"`
- `"必须选择proceed"` → `"通常应选择proceed"`
- Added: `"请基于具体情况综合判断，矩阵仅供参考"`

#### Change 3: Trade-off Principles

**Before**:
```
#### 3.1 质量优先原则
- **医疗场景对可靠性要求极高**
- 对于critical和major问题，应该优先解决
- 宁可多花几步也要确保质量
```

**After**:
```
#### 3.1 质量优先原则
- **医疗场景对可靠性要求极高**
- 对于critical和major问题，通常优先解决
- 在预算允许的情况下，质量优于效率
```

**Key Changes**:
- `"应该优先解决"` → `"通常优先解决"`
- `"宁可多花几步"` → `"在预算允许的情况下"` (more rational trade-off)

#### Change 4: Decision Requirements

**Before**:
```
## 注意事项

- 医疗场景对可靠性要求极高，但也要考虑效率和资源利用
- **严格遵守决策矩阵**：Minor问题且通过评估时必须proceed，不要过度保守
- 你的reasoning将被记录用于审计，请清晰说明决策依据
- 只有在Critical或Major问题时才考虑回退
- 避免无意义的重复，如果多次回退仍无改善，应该考虑终止或人类介入
```

**After**:
```
## 决策要求

- 医疗场景对可靠性要求极高，同时也需考虑效率和资源合理利用
- **参考决策矩阵**：Minor问题且通过评估时通常应proceed，避免过度保守
- 你的reasoning将被记录用于审计和系统改进，请清晰阐述决策逻辑和权衡考虑
- Critical或Major问题通常需要回退，但请结合具体情况判断
- 避免无效重复：如果多次回退仍无显著改善，考虑终止或请求人类介入
```

**Key Changes**:
- Title: `"注意事项"` → `"决策要求"` (more active)
- `"严格遵守"` → `"参考"`
- `"必须proceed"` → `"通常应proceed"`
- `"只有在...才考虑"` → `"通常需要...但请结合具体情况"`
- `"请清晰说明"` → `"请清晰阐述决策逻辑和权衡考虑"` (more detailed guidance)

**Token Impact**:
- Scheduling prompt increase: 30-50 tokens
- Percentage of total workflow: <3%

### 4.5 Unchanged Components

The following remain unchanged to preserve system stability:

1. **JSON Output Format**: All structured data schemas
2. **Judge Dimensions & Weights**: 3-4 dimensions per stage, weight distribution
3. **Judge Pass Threshold**: 0.7 threshold, no critical issues
4. **Scheduling Actions**: proceed, backtrack_to_X, retry_current, terminate, request_human_review
5. **Workflow Architecture**: 5A stages, Judge LLM, Scheduling LLM
6. **Hard Gates**: 4 hard-rule gates (evidence quality, empty results, max iterations, conflict)
7. **Python Code**: No code changes, only prompt text files

---

## 5. Implementation Guide

### 5.1 Files to Modify

**Total**: 11 prompt text files

**Agent Prompts** (5 files):
- `src/config/prompts/ask_agent.txt`
- `src/config/prompts/acquire_agent.txt`
- `src/config/prompts/appraise_agent.txt`
- `src/config/prompts/apply_agent.txt`
- `src/config/prompts/assess_agent.txt`

**Judge Prompts** (5 files):
- `src/config/prompts/judge/ask_judge.txt`
- `src/config/prompts/judge/acquire_judge.txt`
- `src/config/prompts/judge/appraise_judge.txt`
- `src/config/prompts/judge/apply_judge.txt`
- `src/config/prompts/judge/assess_judge.txt`

**Scheduling Prompt** (1 file):
- `src/config/prompts/scheduling_llm.txt`

### 5.2 Implementation Steps

1. **Backup Current Prompts**
   - Create backup copies of all 11 files
   - Tag current git commit for easy rollback

2. **Modify Agent Prompts**
   - Apply tone changes: command → guidance style
   - Add reasoning acknowledgment phrases
   - Maintain JSON schema specifications

3. **Modify Judge Prompts**
   - Convert fixed-tier scoring to continuous ranges
   - Soften severity language (must → suggest)
   - Add contextual guidance phrases

4. **Modify Scheduling Prompt**
   - Update decision matrix header and content
   - Soften directive language
   - Add judgment emphasis

5. **Testing Strategy**
   - Use existing test cases from `tests/` directory
   - Compare outputs before/after modification
   - Monitor token usage and latency
   - Validate JSON output format compliance

6. **Validation Criteria**
   - Token increase: <5% per workflow
   - Latency increase: negligible
   - JSON parsing: 100% success rate
   - Clinical quality: maintained or improved (subjective evaluation)

### 5.3 Rollback Plan

If issues arise:
1. Restore from backup files
2. Or revert to git tag
3. Analyze specific failure points
4. Apply modifications incrementally (e.g., Agents first, then Judges)

---

## 6. Expected Outcomes

### 6.1 Quantitative Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Token/workflow | ~15,000 | <15,750 | <5% increase |
| Latency | ~60s | ~60-62s | <3% increase |
| JSON parse success | 95% | 95%+ | Maintain or improve |
| Backtrack frequency | ~30% | 25-30% | May decrease slightly |

### 6.2 Qualitative Improvements

**Primary Goal - Model Flexibility**:
- ✅ Less command-driven, more reasoning-engaged prompts
- ✅ Acknowledgment of model's clinical reasoning capabilities
- ✅ Reduced over-engineering perception
- ✅ Maintained EBM methodology compliance

**Secondary Goals**:
- ✅ More flexible scoring reduces unnecessary backtracks
- ✅ Better alignment with model's natural response patterns
- ✅ Improved system "feel" - less robotic, more collaborative

### 6.3 Risk Assessment

**Low Risk Changes**:
- All modifications are text-only (no code changes)
- JSON schemas unchanged (parsing logic unaffected)
- Core workflow logic intact
- Easy rollback capability

**Potential Issues**:
- Model may interpret continuous scoring inconsistently → Monitor initial runs
- Softer language may reduce backtrack frequency → Validate quality impact
- Token usage may exceed 5% on complex cases → Monitor p95/p99 metrics

**Mitigation**:
- Gradual rollout: Test on sample cases before full deployment
- A/B testing: Run old vs. new prompts in parallel
- Human review: Sample outputs for quality validation

---

## 7. Future Enhancements

### 7.1 Potential Next Steps

If Approach 1 proves successful, consider:

**Option A: Hybrid with Approach 2**
- Add brief guiding questions to Apply Agent only
- Estimated token increase: 10-15% total
- Higher flexibility at critical reasoning stage

**Option B: Dynamic Prompt Adjustment**
- Use different prompt strictness based on query complexity
- Simple queries: minimal prompts
- Complex queries: more structured guidance

**Option C: Feedback-based Refinement**
- Collect clinical expert feedback on recommendations
- Iteratively refine prompts based on quality patterns

### 7.2 Long-term Vision

**Specialized Agent Training**:
- Once custom Agent LLMs are trained, may revert to more structured prompts
- Fine-tuned models can handle stricter templates without losing flexibility
- Current design provides baseline for training data collection

**Quality vs. Efficiency Optimization**:
- Continuous monitoring of backtrack frequency and quality scores
- Data-driven adjustment of Judge thresholds and Scheduling criteria

---

## 8. Conclusion

This design provides a **low-risk, high-value** improvement to the EBM 5A system's prompt architecture. By adjusting tone and language without structural changes, we aim to:

1. **Preserve model reasoning capabilities** (primary goal)
2. **Reduce unnecessary rigidity** in evaluation and scheduling
3. **Maintain EBM compliance** and quality standards
4. **Keep token/latency impact minimal** (<5%)

The lightweight nature of these changes allows for easy implementation, testing, and rollback if needed. Success will be measured primarily by qualitative assessment of answer flexibility and model engagement, with quantitative metrics serving as guardrails.

**Status**: Design approved, ready for implementation planning.

---

## Appendix: Design Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-25 | Selected Approach 1 over 2/3 | Minimizes risk and token cost while addressing core issue |
| 2026-02-25 | Continuous scoring vs. fixed tiers | Allows more nuanced quality assessment |
| 2026-02-25 | Soften Scheduling matrix language | Trusts LLM judgment while maintaining framework |
| 2026-02-25 | No code changes | Text-only modifications for easy rollback |
| 2026-02-25 | Keep JSON schemas unchanged | Prevents parsing failures and system instability |
