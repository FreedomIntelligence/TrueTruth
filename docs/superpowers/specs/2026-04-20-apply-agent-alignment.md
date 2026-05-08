# Apply Agent 对齐设计规范

**日期**: 2026-04-20
**范围**: `apply_agent.py`（执行逻辑修改）+ `apply_agent.txt`（prompt 修改）
**不在本次范围内**: Apply Judge 的 route_type 适配；Consensus-based 推荐逻辑变更

---

## 背景与问题

Apply 阶段存在四处与前序改动脱节的问题：

1. **Step 1 硬编码 PICO 维度**：Ask 新架构定义了 PICO/PIRD/PEO/Prognosis 四种格式，Apply 仍用"Population/Intervention/Outcome"框架检查所有问题，PIRD 的"Index Test"被错误映射为"Intervention"，Prognosis 缺少"Time Horizon"检查
2. **`appraisal_summary` 仅注入自由文本**：LLM 无法区分"整体 GRADE=Moderate 但 inconsistency=SERIOUS"与"整体 GRADE=Moderate 且各因素均 NOT_SERIOUS"，可能产生错误的 Strong 推荐
3. **`evidence_summary` 不含证据内容**：只传 title/quality/source，LLM 看不到 Acquire 阶段 RAG 提取的 key_sentences，无法基于实际内容生成推荐
4. **Python 侧 GRADE enforcement 不完整**：只处理"Low/Very Low → 阻止 Strong"，未处理"inconsistency=SERIOUS → 阻止 Strong"

---

## 改动一：prompt 注入 `route_type` + `ebm_query`（解决问题1）

### `apply_agent.py` execute() 新增

```python
# 读取路由信息（兼容过渡期：优先 ebm_query，回退 pico_query）
route_type = state.get("route_type") or "ebm_pico"
ebm_query = state.get("ebm_query")
pico_query = state.get("pico_query")

if ebm_query:
    query_description = _format_ebm_query(ebm_query)
elif pico_query:
    query_description = _format_pico_query(pico_query)
else:
    query_description = "N/A"
```

`_format_ebm_query` 和 `_format_pico_query` 输出纯文本，格式模板如下：

```
# _format_ebm_query（按 query_type 选择标签）
PICO:      Patient: {patient} | Intervention: {primary_focus} | Comparator: {comparator} | Outcome: {outcome}
PIRD:      Patient: {patient} | Index Test: {primary_focus} | Reference Standard: {reference_standard} | Target Condition: {outcome}
PEO:       Patient: {patient} | Exposure: {primary_focus} | Outcome: {outcome}
Prognosis: Patient: {patient} | Prognostic Factor: {primary_focus} | Outcome: {outcome} | Time Horizon: {time_horizon}

# _format_pico_query（旧格式兼容）
Patient: {population} | Intervention: {intervention} | Comparator: {comparison} | Outcome: {outcome}
```

所有 `None` 值字段输出为 `"N/A"` 而非 Python `None`，避免 prompt 中出现 `None` 字面量。

### `apply_agent.txt` Step 1 替换

**原文：**
```
**Step 1 - PICO Consistency Check:**
- Population match
- Intervention match
- Outcome match
```

**替换为：**
```
**Step 1 - Query Consistency Check:**
Route Type: {route_type}
Structured Query: {query_description}

Check evidence applicability based on the route_type dimensions:

- PICO:      Population / Intervention / Comparator / Outcome
- PIRD:      Population / Index Test / Reference Standard / Target Condition
- PEO:       Population / Exposure / Outcome（no Comparator）
- Prognosis: Population / Prognostic Factor / Outcome / Time Horizon

For each dimension of the current route_type, assess:
  - Match: evidence directly matches the query dimension
  - Partial: approximate match (similar but not identical population, surrogate endpoint, analogous intervention)
  - Mismatch: fundamental mismatch — must flag explicitly in caveats
```

---

## 改动二：注入结构化 GRADE 字段（解决问题2）

### `apply_agent.py` 新增 appraisal_summary 构建

```python
# 从 grade_rationales 提取关键降级因素摘要
grade_rationales = state.get("grade_rationales", [])

def _summarize_downgrade_factors(rationales: list) -> str:
    """统计各降级因素中最严重的标签及出现频次。"""
    factor_counts = {}
    for r in rationales:
        for factor in ("risk_of_bias", "inconsistency", "indirectness", "imprecision"):
            val = r.get(factor, "NOT_SERIOUS")
            if val in ("SERIOUS", "VERY_SERIOUS"):
                factor_counts[factor] = factor_counts.get(factor, 0) + 1
    if not factor_counts:
        return "All downgrade factors: NOT_SERIOUS"
    return "; ".join(
        f"{k}: SERIOUS/VERY_SERIOUS ({v}/{len(rationales)} studies)"
        for k, v in factor_counts.items()
    )

key_downgrade_factors = _summarize_downgrade_factors(grade_rationales)

# inconsistency 专项标记：任一文章 inconsistency=SERIOUS/VERY_SERIOUS 则触发
has_serious_inconsistency = any(
    r.get("inconsistency") in ("SERIOUS", "VERY_SERIOUS")
    for r in grade_rationales
)
consistency_flag = "SERIOUS inconsistency detected" if has_serious_inconsistency else "Consistent"
```

### `apply_agent.txt` 替换 `{appraisal_summary}` 注入格式

**原注入：**
```
Overall Appraisal: {appraisal_summary}
```

**替换为：**
```
Overall GRADE: {overall_grade}
Key downgrade factors: {downgrade_factors}
Evidence consistency: {consistency_flag}
Appraisal narrative: {appraisal_narrative}
```

### `apply_agent.txt` Step 3 新增 inconsistency 规则

在现有 Strength 规则后追加：

```
- If inconsistency was rated SERIOUS in appraisal (consistency_flag = "SERIOUS inconsistency
  detected") → treat results as "inconsistent" → cap strength at Weak,
  regardless of overall GRADE level
```

---

## 改动三：evidence_summary 注入 key_sentences（解决问题3）

### `apply_agent.py` evidence_summary 构建修改

**原：**
```python
evidence_summary = "\n\n".join([
    f"Evidence {i+1}:\nTitle: {e.title}\nQuality: {e.grade_level}\nSource: {e.source}"
    for i, e in enumerate(appraisal.evidence)
])
```

**替换为：**
```python
evidence_summary = "\n\n".join([
    f"Evidence {i+1}:\n"
    f"Title: {e.title}\n"
    f"GRADE: {e.grade_level}\n"
    f"Study Type: {e.study_type}\n"
    f"Key Findings:\n{e.key_sentences or e.abstract or '（无摘要）'}"
    for i, e in enumerate(appraisal.evidence)
])
```

`key_sentences` 由 Acquire 阶段 RAG 提取写入，此处首次被 LLM 实际消费用于生成推荐。若 key_sentences 为空（过渡期未完成 RAG 改造时），回退到 abstract。

---

## 改动四：Python 侧 GRADE enforcement 补全（解决问题4）

### `apply_agent.py` strength enforcement 修改

**原：**
```python
if evidence_quality in ("Very Low", "Low") and llm_strength == "Strong":
    strength = "Weak"
else:
    strength = llm_strength
```

**替换为：**
```python
llm_strength = rec_dict.get("strength", "Weak")

# evidence_quality：从 state["appraisal_result"].overall_grade 读取（Appraise 阶段写入）
# 取值范围："High" | "Moderate" | "Low" | "Very Low"
evidence_quality = state.get("appraisal_result", {}).get("overall_grade", "Very Low")

# Rule 1: Low/Very Low 证据不可为 Strong
if evidence_quality in ("Very Low", "Low") and llm_strength == "Strong":
    strength = "Weak"
# Rule 2: inconsistency=SERIOUS 时强制 Weak（无论 GRADE 等级）
# 触发策略：任一文章 inconsistency=SERIOUS/VERY_SERIOUS 即触发（保守策略）
# 设计意图：单篇严重不一致足以使整体证据体的方向性结论不可靠，
#           不设比例阈值，避免"多数通过"掩盖关键异质性
elif has_serious_inconsistency and llm_strength == "Strong":
    strength = "Weak"
else:
    strength = llm_strength
```

两条规则均在 Python 侧强制执行，防止 LLM 违反 GRADE 原则。

---

## prompt 模板变量更新汇总

| 变量 | 原来 | 现在 |
|---|---|---|
| `{route_type}` | 无 | 新增，来自 `state["route_type"]` |
| `{query_description}` | 无 | 新增，由 `ebm_query` 或 `pico_query` 格式化 |
| `{appraisal_summary}` | 自由文本 | 拆分为4个结构化字段 |
| `{overall_grade}` | 无 | 新增，来自 Python 计算的 evidence_quality |
| `{downgrade_factors}` | 无 | 新增，来自 grade_rationales 摘要 |
| `{consistency_flag}` | 无 | 新增，"SERIOUS inconsistency detected" or "Consistent" |
| `{appraisal_narrative}` | `{appraisal_summary}` | 重命名，保留原自由文本叙述 |

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/apply_agent.txt` | 修改 | Step 1 按 route_type 动态一致性检查维度；新增结构化 GRADE 输入字段；Step 3 新增 inconsistency 触发 Weak 规则 |
| `src/agents/apply_agent.py` | 修改 | 注入 route_type + query_description；构建结构化 appraisal_summary（downgrade_factors、consistency_flag、appraisal_narrative）；evidence_summary 加入 key_sentences；Python enforcement 补全 inconsistency Rule 2 |

---

## 明确不在本次范围内

- Apply Judge（`judge_llm.py` `_score_apply`）的 route_type 适配
- Consensus-based 推荐的引用格式变更
