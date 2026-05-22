# Apply Judge 改动规范

**日期**: 2026-04-20
**范围**: `apply_judge.txt`（修改）
**不在本次范围内**: `_score_apply` Python 侧权重调整；Consensus-based 推荐引用格式变更

---

## 背景与问题

现有 Apply Judge 存在以下问题，均源于与 Apply Agent 对齐改动（`2026-04-20-apply-agent-alignment.md`）脱节：

1. **输入仍用 `{pico_query}`**：Apply 新架构注入了 `route_type + query_description`，Judge 对路由框架无感知，无法审计"维度一致性检查是否按正确路由框架执行"
2. **`strength_matches_evidence_quality` 规则缺少 inconsistency 条款**：Apply enforcement Rule 2 规定 `inconsistency=SERIOUS → 强制 Weak`，但 Judge 的评判规则没有这条，会将正确的"Moderate 证据给 Weak"误标为 MINOR_MISMATCH
3. **无路由维度一致性审计**：Apply Step 1 现按路由框架做维度一致性检查，但 Judge 没有审计"Apply 是否选用了正确的维度框架（PICO/PIRD/PEO/Prognosis）"

---

## 改动一：输入字段更新

### `apply_judge.txt` 输入段替换

**原：**
```
## PICO查询
{pico_query}
```

**替换为：**
```
## 查询信息
路由类型：{route_type}
结构化查询：{query_description}
```

---

## 改动二：新增路由维度一致性审计

### 在 `## 1. 推荐-证据匹配审计` 前新增

```
## 0. 路由维度一致性审计

**route_dimension_consistent**：Apply 的维度一致性检查（Step 1）是否使用了与 route_type 匹配的维度框架？
各 route_type 对应的正确框架：
- ebm_pico:      Population / Intervention / Comparator / Outcome
- ebm_pird:      Population / Index Test / Reference Standard / Target Condition
- ebm_peo:       Population / Exposure / Outcome（无 Comparator）
- ebm_prognosis: Population / Prognostic Factor / Outcome / Time Horizon
- direct_answer: 不做维度一致性检查（直接操作性指导，无需 PICO 框架）

- `YES`：维度框架与 route_type 匹配，评估覆盖了该框架的全部维度
- `PARTIAL`：框架大致正确，但遗漏了个别维度（如 Prognosis 遗漏了 Time Horizon 检查）
- `NO`：使用了错误框架（如 PIRD 问题用 PICO 框架，Index Test 被错误映射为 Intervention）
- `NA`：route_type 为 direct_answer，不适用
```

---

## 改动三：`strength_matches_evidence_quality` 规则补全

### 原规则说明（节选）

```
EBM原则：
- Strong推荐需要High/Moderate直接证据；
- Weak推荐适用于Low质量证据或结果不一致；
- ...
- Very Low证据且不一致 → 只能支持Weak/Conditional/Consensus-based或证据不足声明。
```

### 在规则列表末尾追加

```
- 若 Appraise 阶段任一研究的 inconsistency 被评为 SERIOUS/VERY_SERIOUS（即
  consistency_flag = "SERIOUS inconsistency detected"），则无论整体 GRADE 等级如何，
  推荐强度上限为 Weak——此时即使 GRADE=Moderate/High，给出 Weak 也是**正确行为**，
  不应标注为 MISMATCH。
```

### 同时更新 `MINOR_MISMATCH` 和 `MAJOR_MISMATCH` 描述

```
- `YES`：推荐强度与证据质量严格匹配（含 Conditional/Consensus-based 使用正确；
         含 inconsistency=SERIOUS 时 Moderate→Weak 的降强推荐）
- `MINOR_MISMATCH`：有轻微偏差（如 Moderate 证据给 Strong，但结果高度一致且无 inconsistency 问题），临床上可接受
- `MAJOR_MISMATCH`：严重不匹配（如 Very Low/Low 证据给 Strong，或有充分直接高质量证据却输出 No Recommendation）
```

---

## 改动四：输出格式更新

### JSON 输出新增 `route_dimension_consistent` 字段，并统一为 `failures` + `overall_quality` 框架

```json
{
  "route_audit": {
    "route_dimension_consistent": "YES | PARTIAL | NO | NA"
  },
  "grounding_audit": {
    "recommendation_based_on_evidence": "YES | PARTIAL | NO",
    "uses_external_knowledge": "YES | NO"
  },
  "strength_audit": {
    "insufficient_evidence_appropriate": "YES | NO | NA",
    "strength_matches_evidence_quality": "YES | MINOR_MISMATCH | MAJOR_MISMATCH"
  },
  "actionability_audit": {
    "recommendation_specific": "YES | PARTIAL | NO",
    "caveats_documented": "YES | PARTIAL | NO | NA"
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | degraded"
}
```

---

## `_score_apply` 评分说明（无需改动）

`route_dimension_consistent=NO` 属于 MAJOR 问题，Apply 阶段应触发 retry。现有 `_score_apply` 已有 major issue → 降分逻辑，无需额外适配。

Python 侧如需针对 `route_dimension_consistent=NO` 做一票否决，可在后续迭代中与其他 Judge 的 critical 路径对齐处理。

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/judge/apply_judge.txt` | 修改 | 输入换为 `{route_type}` + `{query_description}`；新增 `route_dimension_consistent` 审计；`strength_matches_evidence_quality` 规则补全 inconsistency=SERIOUS 条款；输出改为 `failures` + `overall_quality` 统一框架 |

---

## 明确不在本次范围内

- `_score_apply` Python 侧权重调整
- Apply Judge 对 `route_dimension_consistent=NO` 的一票否决路径
- Consensus-based 推荐的引用格式审计
