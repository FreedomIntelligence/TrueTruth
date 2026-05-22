# Appraise Judge 改动规范

**日期**: 2026-04-20
**范围**: `appraise_judge.txt`（修改）
**不在本次范围内**: Appraise Judge 的 `_score_appraise` Python 侧权重调整；PIRD 场景下 CROSS_SECTIONAL 初始分逻辑

---

## 背景与问题

现有 Appraise Judge 存在以下问题，均源于与 Appraise Agent GRADE 修正（`2026-04-20-appraise-agent-grade-fix.md`）脱节：

1. **`study_type_correct` 未涵盖新 study_type**：SR/MA/NMA 现在需要 `included_study_type` 才能确定初始等级，Judge 没有审计该字段
2. **`downgrade_factors_appropriate` 未审计升级因素**：新增第三个升级因素 `confounding_bias_mitigates`，Judge 完全未覆盖升级因素合理性
3. **`upgrade_blocked_by_bias` 未审计**：Appraise 新增该字段，Judge 应验证："存在 SERIOUS 偏倚时，升级因素是否被正确阻断"
4. **`computed_grade_reasonable` 判断标准基于旧逻辑**：SR+included=OBSERVATIONAL → Low（正确），但 Judge 可能将其误判为不合理

---

## 改动一：`study_type_correct` 扩展为 `study_type_audit`

### 原审计段

```
**study_type_correct**：Appraise Agent对研究类型（study_type）的识别是否准确？
- `YES`：所有研究的study_type识别正确（RCT/COHORT/CASE_CONTROL/CASE_REPORT）
- `PARTIAL`：大部分正确，个别研究类型有可商榷之处
- `NO`：存在明显错误（如将观察性研究标记为RCT，或将RCT标记为COHORT）
```

### 替换为

```
**study_type_correct**：Appraise Agent对研究类型（study_type）的识别是否准确？
- `YES`：所有研究的 study_type 识别正确
- `PARTIAL`：大部分正确，个别研究类型有可商榷之处
- `NO`：存在明显错误（如将观察性研究标记为RCT）

**included_study_type_correct**（仅当 study_type 包含 SYSTEMATIC_REVIEW/META_ANALYSIS/NMA 时判断）：
SR/MA/NMA 的 `included_study_type` 字段填写是否正确？
- `YES`：字段与摘要描述的纳入研究类型相符（如摘要明确描述"纳入RCT"→ RCT；纳入队列研究 → OBSERVATIONAL）
- `PARTIAL`：字段基本合理，但摘要信息不足以确认（如摘要未描述纳入类型 → UNKNOWN 是合理选择）
- `NO`：明显错误（如摘要写"仅纳入RCT"但标注为 OBSERVATIONAL）
- `NA`：证据列表中没有 SR/MA/NMA 类型研究
```

---

## 改动二：新增升级因素合理性审计

### 在 `downgrade_factors_appropriate` 后新增

```
**upgrade_factors_appropriate**（仅当证据列表中存在 COHORT/CASE_CONTROL 研究时判断）：
升级因素（large_effect / dose_response / confounding_bias_mitigates）的标注是否合理？
- `YES`：升级因素的 YES/NO 标注与摘要信息相符
- `PARTIAL`：整体合理，个别因素有轻微偏差
- `NO`：存在明显错误（如无明确剂量效应数据但标注 dose_response=YES）
- `NA`：证据列表中没有 COHORT/CASE_CONTROL 研究

**upgrade_blocked_appropriate**（仅当存在 COHORT/CASE_CONTROL 且 risk_of_bias=SERIOUS/VERY_SERIOUS 时）：
存在严重偏倚风险时，升级因素是否被正确阻断（upgrade_blocked_by_bias=True）？
- `YES`：risk_of_bias=SERIOUS/VERY_SERIOUS 时，upgrade_blocked_by_bias 正确标注为 True，且最终等级未因升级因素提升
- `NO`：存在严重偏倚但升级因素仍被计入（系统 bug 信号，需上报）
- `NA`：无 COHORT/CASE_CONTROL 研究，或 risk_of_bias 均为 NOT_SERIOUS
```

---

## 改动三：更新 `computed_grade_reasonable` 判断标准说明

### 在该审计项说明中追加注意事项

```
**computed_grade_reasonable**：系统根据分类计算出的最终GRADE等级（computed_grade）是否合理？
- `YES`：计算结果与基于摘要的独立判断一致
- `PARTIAL`：整体合理，个别研究的等级有轻微偏差
- `NO`：计算结果明显不合理（通常是因为study_type或降级因素分类错误导致）

注意以下情况属于**合理结果**，不应判断为 NO：
- SR/MA 纳入观察性研究（included_study_type=OBSERVATIONAL）→ 初始分为 Low（2分），即使无降级因素也可能输出 Low/Very Low
- COHORT/CASE_CONTROL 存在 SERIOUS 偏倚时，即使 large_effect=YES 也不升级 → computed_grade 停在 Low
- COHORT/CASE_CONTROL 经升级后最高只能到 Moderate → 不应期望输出 High
- CROSS_SECTIONAL 无升级因素 → 最高只能到 Low（初始分即为2）
```

---

## 改动四：输出格式统一

将 `reasoning` 字段替换为 `failures` + `overall_quality`，与 Ask Judge 框架统一：

```json
{
  "grade_audit": {
    "study_type_correct": "YES | PARTIAL | NO",
    "included_study_type_correct": "YES | PARTIAL | NO | NA",
    "downgrade_factors_appropriate": "YES | PARTIAL | NO",
    "upgrade_factors_appropriate": "YES | PARTIAL | NO | NA",
    "upgrade_blocked_appropriate": "YES | NO | NA",
    "computed_grade_reasonable": "YES | PARTIAL | NO"
  },
  "conflict_audit": {
    "conflicts_exist": "YES | NO",
    "conflicts_identified": "YES | PARTIAL | NO | NA"
  },
  "data_audit": {
    "numerical_data_extracted": "YES | PARTIAL | NO | NA",
    "confidence_level_appropriate": "HIGH | MODERATE | LOW | VERY_LOW"
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | degraded"
}
```

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/judge/appraise_judge.txt` | 修改 | `study_type_correct` 扩展（新增 `included_study_type_correct`）；新增升级因素审计（`upgrade_factors_appropriate` / `upgrade_blocked_appropriate`）；更新 `computed_grade_reasonable` 注意事项；输出改为 `failures` + `overall_quality` 统一框架 |

---

## 明确不在本次范围内

- `_score_appraise` Python 侧权重调整
- PIRD 场景下 CROSS_SECTIONAL（横断面研究）应使用 QUADAS-2 的处理
- SR 纳入观察性研究时的升级因素适配
