# Acquire Judge 改动规范

**日期**: 2026-04-20
**范围**: `acquire_judge.txt`（修改）+ `judge_llm.py` `_score_acquire` 遗留问题记录
**不在本次范围内**: `_score_acquire` Python 侧的路由分支权重适配

---

## 背景与问题

现有 Acquire Judge 存在以下问题：

1. **输入仍用 `{pico_query}`**：Acquire 新架构改为 `EBMQuery`，Judge 对 `route_type` 无感知，导致 PIRD/PEO/Prognosis 场景下"干预维度"的概念错配
2. **`pico_p_match` / `pico_i_match` / `pico_o_match` 字段名硬编码 PICO**：在 PIRD 场景下审计的是 "Intervention" 而非 "Index Test"，语义错误
3. **`has_full_text` 未纳入审计**：新 Acquire 流程引入 PMC 全文拉取，Judge 应审计全文覆盖率
4. **`key_sentences` 质量未审计**：RAG 提取的 key_sentences 是 Apply 阶段的核心输入，全为空说明 RAG 流程失败

---

## 改动一：输入字段更新

### `acquire_judge.txt` 输入段替换

**原：**
```
## PICO查询
{pico_query}
```

**替换为：**
```
## 查询信息
路由类型：{route_type}
结构化查询：{ebm_query}
```

Python 侧（`judge_llm.py` `evaluate_stage` Ask 阶段）已将 `route_type` 和 `ebm_query` 写入 state，此处直接读取注入。

---

## 改动二：维度匹配审计字段通用化

### 字段名映射

| route_type | 原字段名（硬编码） | 新字段名（通用） | 审计对象 |
|---|---|---|---|
| `ebm_pico` | `pico_i_match` | `primary_focus_match` | Intervention |
| `ebm_pird` | `pico_i_match` | `primary_focus_match` | Index Test |
| `ebm_peo` | `pico_i_match` | `primary_focus_match` | Exposure |
| `ebm_prognosis` | `pico_i_match` | `primary_focus_match` | Prognostic Factor |

### 更新后的 PICO 匹配度审计段

```
## 3. 查询维度匹配度审计
**基于证据列表中查询维度匹配度最好的那篇证据进行判断。**

各 route_type 对应的审计维度：
- ebm_pico:      Patient / Intervention / Outcome
- ebm_pird:      Patient / Index Test / Target Condition
- ebm_peo:       Patient / Exposure / Outcome
- ebm_prognosis: Patient / Prognostic Factor / Outcome

**p_match**：证据中的研究人群是否与查询的 Patient 匹配？
- `YES`：精准匹配（相同年龄段、相同疾病状态）
- `PARTIAL`：有轻微差异（如年龄范围略不同），结论可审慎外推
- `NO`：严重不匹配（如成人证据用于儿科问题，或完全不同的疾病）

**primary_focus_match**：证据中的核心干预/暴露/测试是否与查询的主焦点维度匹配？
（ebm_pico → Intervention；ebm_pird → Index Test；ebm_peo → Exposure；ebm_prognosis → Prognostic Factor）
- `YES`：精准匹配
- `PARTIAL`：有轻微差异（同类方法，不同剂量/版本），相关性高
- `NO`：严重不匹配（完全不同的测试/干预/暴露）

**o_match**：证据中报告的结局是否与查询的 Outcome / Target Condition 匹配？
- `YES`：报告了临床关心的直接结局指标
- `PARTIAL`：报告了代理指标或部分相关结局
- `NO`：未报告任何相关结局
```

同时，JSON 输出中原 `pico_p_match` / `pico_i_match` / `pico_o_match` 对应替换为 `p_match` / `primary_focus_match` / `o_match`。

---

## 改动三：新增 `full_text_audit`

### 审计段新增

```
## 5. 全文与 RAG 质量审计

**full_text_coverage**：Top 文章（排名前3）中，has_full_text=True 的比例是否合理？
- `GOOD`：≥2/3 篇有全文，RAG 质量有保障
- `PARTIAL`：1/3 篇有全文，或全文获取部分失败，仍有可用摘要
- `NONE`：Top 3 篇均无全文（has_full_text 全为 False），仅凭摘要进行 RAG

**key_sentences_present**：key_sentences 字段是否有实质内容？
- `YES`：Top 文章的 key_sentences 非空，说明 RAG 流程正常执行
- `PARTIAL`：部分文章的 key_sentences 为空（可能是摘要极短导致 chunk 失败）
- `NO`：所有文章的 key_sentences 均为空，RAG 流程可能失败

注意：key_sentences 为空时 Apply 阶段会回退到 abstract，不构成一票否决，但影响 evidence_quality 维度得分。
```

---

## 改动四：更新系统错误检测段

原有"首先检查 `error` 字段"逻辑保留，固定输出中 `pico_p_match` / `pico_i_match` / `pico_o_match` 替换为新字段名：

```python
# 错误时固定输出
"query_match": {
    "p_match": "NO",
    "primary_focus_match": "NO",
    "o_match": "NO"
},
"full_text_audit": {
    "full_text_coverage": "NONE",
    "key_sentences_present": "NO"
}
```

---

## 完整更新后的 JSON 输出格式

```json
{
  "search_audit": {
    "search_terms_valid": "YES | NO"
  },
  "evidence_audit": {
    "best_study_type": "SR_META | RCT | COHORT | CASE_CONTROL | CASE_REPORT | NONE",
    "best_evidence_answers_query": "YES | PARTIAL | NO"
  },
  "query_match": {
    "p_match": "YES | PARTIAL | NO",
    "primary_focus_match": "YES | PARTIAL | NO",
    "o_match": "YES | PARTIAL | NO"
  },
  "listwise_audit": {
    "top_selection_appropriate": "YES | PARTIAL | NO",
    "selection_count_appropriate": "YES | PARTIAL | NO"
  },
  "full_text_audit": {
    "full_text_coverage": "GOOD | PARTIAL | NONE",
    "key_sentences_present": "YES | PARTIAL | NO"
  },
  "search_exhausted": false,
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | degraded"
}
```

`reasoning` 字段删除，替换为结构化的 `failures` + `overall_quality`，与 Ask Judge 统一输出框架。

---

## `_score_acquire` 遗留问题记录（不在本次范围）

当前 `_score_acquire` Python 侧对所有路由使用相同的 `pico_i_match` 权重。正确做法应当：
- `ebm_pico`：`primary_focus_match`（Intervention）权重维持现有
- `ebm_pird`：`primary_focus_match`（Index Test）权重应等同于 `p_match`（诊断研究核心）
- `ebm_peo`：`primary_focus_match`（Exposure）权重应与 `o_match` 相当（病因研究两者并重）
- `ebm_prognosis`：`primary_focus_match`（Prognostic Factor）权重较低，`p_match` 和 `o_match` 更重要

**后续迭代处理**，本次仅将字段名统一化，不改变权重逻辑。

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/judge/acquire_judge.txt` | 修改 | 输入换为 `{route_type}` + `{ebm_query}`；维度字段通用化（`p_match` / `primary_focus_match` / `o_match`）；新增 `full_text_audit`；输出改为 `failures` + `overall_quality` 统一框架；删除 `reasoning` |

---

## 明确不在本次范围内

- `_score_acquire` Python 侧各路由的维度权重分支
- Acquire Judge 对 diagnostic_reasoning 子问题多路检索的专项审计
