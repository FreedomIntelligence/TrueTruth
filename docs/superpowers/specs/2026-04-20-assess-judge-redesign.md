# Assess Judge 改动规范

**日期**: 2026-04-20
**范围**: `assess_judge.txt`（修改）
**不在本次范围内**: `_score_assess` Python 侧权重调整；Assess Agent 本身的逻辑改动

---

## 背景与问题

现有 Assess Judge 存在以下问题：

1. **输入仍用 `{pico_query}`**：所有前序阶段已切换到 `route_type + ebm_query` 架构，Assess Judge 的全链路回顾应当感知路由类型
2. **`ask_to_acquire_link` 描述硬编码 P/I/O**：PIRD 场景下应检查 "Index Test 覆盖"，Prognosis 应检查 "Prognostic Factor"，现在全部写死为 "P/I/O 要素"，导致 PIRD/Prognosis 场景下审计逻辑错误
3. **`route_confidence` 未感知**：Ask Judge 可能降级（fallback → `route_confidence=low`），Assess 作为最终链路审查，应当认知这个状态并在完整性审计中特别标注，否则会将"因路由不确定性导致的证据缺失"误判为链路质量问题

---

## 改动一：输入字段更新

### `assess_judge.txt` 输入段替换

**原：**
```
## 完整推理链摘要
- PICO查询: {pico_query}
- 证据数量: {evidence_count}
- 证据质量分布: {grade_distribution}
- 最终推荐: {recommendation}
```

**替换为：**
```
## 完整推理链摘要
- 路由类型: {route_type}
- 路由置信度: {route_confidence}
- 结构化查询: {ebm_query}
- 证据数量: {evidence_count}
- 证据质量分布: {grade_distribution}
- 最终推荐: {recommendation}
```

`route_confidence` 取值为 `"normal"`（默认）或 `"low"`（Ask 阶段 fallback 时写入）。

---

## 改动二：`ask_to_acquire_link` 描述动态化

### 原描述

```
**ask_to_acquire_link**：Ask阶段的PICO是否有效指导了Acquire阶段的检索？
- `CLEAR`：检索策略直接来源于PICO，关键词与P/I/O要素对应明确
- `WEAK`：关联存在但不够紧密，检索词覆盖了PICO的主要方面但有跳跃
- `BROKEN`：检索策略与PICO脱节，检索了与PICO无关的主题
```

### 替换为

```
**ask_to_acquire_link**：Ask 阶段的结构化查询是否有效指导了 Acquire 阶段的检索？
各 route_type 对应的审计重点：
- ebm_pico:      关键词是否覆盖 Patient + Intervention + Outcome
- ebm_pird:      关键词是否覆盖 Patient + Index Test + Target Condition
- ebm_peo:       关键词是否覆盖 Patient + Exposure + Outcome
- ebm_prognosis: 关键词是否覆盖 Patient + Prognostic Factor + Outcome
- diagnostic_reasoning: 关键词是否覆盖 Clinical Presentation + 鉴别诊断方向
- direct_answer: 不经过 Acquire 阶段，此项标注为 NA

- `CLEAR`：检索策略直接来源于结构化查询，关键词与对应框架维度对应明确
- `WEAK`：关联存在但不够紧密，检索词覆盖了主要维度但存在跳跃或遗漏
- `BROKEN`：检索策略与结构化查询脱节，检索了完全无关的主题
- `NA`：route_type 为 direct_answer，不适用
```

---

## 改动三：新增 `route_confidence_noted` 审计项

### 在 `## 1. 回答完整性审计` 中新增

```
**route_confidence_noted**：若 route_confidence=low（Ask 阶段因路由不确定而降级处理），
最终回答是否已注明路由不确定性带来的局限？
- `YES`：输出中明确提及路由不确定性或结构化框架的局限，提示需结合临床判断
- `NO`：route_confidence=low 但输出未有任何提示（可能给用户错误的置信感）
- `NA`：route_confidence=normal，路由无不确定性，此项不适用

注意：route_confidence=low 时，Apply agent 应已自动追加 caveat（
"本问题的结构化框架存在路由不确定性（Ask 阶段降级处理），推荐结论需结合临床判断"）。
此处验证该 caveat 是否确实出现在最终输出中。
```

---

## 改动四：输出格式更新

```json
{
  "completeness_audit": {
    "original_question_answered": "YES | PARTIAL | NO",
    "evidence_limitations_stated": "YES | NO | NA",
    "route_confidence_noted": "YES | NO | NA"
  },
  "chain_audit": {
    "ask_to_acquire_link": "CLEAR | WEAK | BROKEN | NA",
    "acquire_to_appraise_link": "CLEAR | WEAK | BROKEN",
    "appraise_to_apply_link": "CLEAR | WEAK | BROKEN"
  },
  "consistency_audit": {
    "grade_to_strength_consistent": "YES | MINOR_ISSUE | MAJOR_CONTRADICTION",
    "no_internal_contradictions": "YES | MINOR_ISSUE | MAJOR_CONTRADICTION"
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | degraded"
}
```

---

## `_score_assess` 评分说明（无需改动）

`route_confidence_noted=NO` 时（即 route_confidence=low 但输出无提示），属于 minor issue，影响 `completeness` 维度得分，不构成一票否决，现有评分逻辑可直接处理。

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/judge/assess_judge.txt` | 修改 | 输入加 `{route_type}` / `{route_confidence}` / `{ebm_query}`；`ask_to_acquire_link` 描述动态化（含各路由审计重点 + direct_answer NA）；新增 `route_confidence_noted` 审计项；输出改为 `failures` + `overall_quality` 统一框架 |

---

## 明确不在本次范围内

- `_score_assess` Python 侧权重调整
- Assess Agent 本身的逻辑改动
- `ambiguity_flag=YES` 时的 UI 提示（仅写入日志）
