# Appraise Agent GRADE 修正规范

**日期**: 2026-04-20
**范围**: `appraise_agent.py`（`_compute_grade` 重写）+ `appraise_agent.txt`（新增字段说明）
**不在本次范围内**: PIRD 语境下 CROSS_SECTIONAL 的初始分问题；SR 纳入观察性研究时的升级因素；Appraise Judge 的格式适配

---

## 背景与问题

对照《循证医学的核心方法与主要模型》（表4）及 GRADE 原始文献（Guyatt 2011），现有实现存在以下错误：

1. **升级因素缺失第三条**：GRADE 列出3个升级因素，现实现只有2个，漏掉"负偏倚（confounding_bias_mitigates）"
2. **SR/MA/NMA 初始等级固定为 High**：应取决于纳入研究类型（RCT→High；观察性→Low；混合→Moderate）
3. **CROSS_SECTIONAL 不应适用升级因素**：横断面研究不评价因果效应，升级因素在概念上不适用
4. **观察性研究升级上限缺失**：观察性研究即使有升级因素，最多升至 Moderate，不应达到 High
5. **严重偏倚风险时升级因素不应适用**：`risk_of_bias = VERY_SERIOUS` 时允许升级违背 GRADE 核心原则

---

## 修正后的完整计算逻辑

### 数据表变更

```python
# 移除 SYSTEMATIC_REVIEW / META_ANALYSIS / NMA（改为动态计算）
_INITIAL_POINTS: Dict[str, int] = {
    "RCT":              4,
    "COHORT":           2,
    "CASE_CONTROL":     2,
    "CROSS_SECTIONAL":  2,
    "NARRATIVE_REVIEW": 1,
    "CASE_REPORT":      1,
    "GUIDELINE":        3,   # 务实简化：基于其引用的基础证据质量，保守取 Moderate
    "EXPERT_OPINION":   1,
}

# SR/MA/NMA 初始分取决于纳入研究类型
_SR_INITIAL_POINTS: Dict[str, int] = {
    "RCT":           4,   # 纳入研究以 RCT 为主（≥80%）→ High
    "OBSERVATIONAL": 2,   # 纳入研究以观察性研究为主（≥80%）→ Low
    "MIXED":         3,   # RCT 占比 20%~79%（含灰区）→ Moderate（保守）
    "UNKNOWN":       3,   # 无法判断 → 保守取 Moderate
}

# 仅 COHORT / CASE_CONTROL 适用升级因素
# CROSS_SECTIONAL 不适用（不评价因果效应）
# SR/MA/NMA 当前迭代不适用升级因素（即使 included_study_type=OBSERVATIONAL）
_UPGRADE_STUDY_TYPES = {"COHORT", "CASE_CONTROL"}
```

### 修正后的 `_compute_grade`

```python
def _compute_grade(appraisal: Dict) -> str:
    study_type = appraisal.get("study_type", "CASE_REPORT")

    # 1. 初始分
    if study_type in ("SYSTEMATIC_REVIEW", "META_ANALYSIS", "NMA"):
        included = appraisal.get("included_study_type", "UNKNOWN")
        points = _SR_INITIAL_POINTS.get(included, 3)
    else:
        points = _INITIAL_POINTS.get(study_type, 1)

    # 2. 降级（5个因素，顺序在升级之前）
    for factor in ("risk_of_bias", "inconsistency", "indirectness", "imprecision"):
        points -= _DOWNGRADE_PENALTY.get(appraisal.get(factor, "NOT_SERIOUS"), 0)
    if appraisal.get("publication_bias") == "SUSPECTED":
        points -= 1

    # 3. 升级（仅 COHORT / CASE_CONTROL）
    if study_type in _UPGRADE_STUDY_TYPES:
        # 前置条件：存在严重偏倚风险时，升级因素不适用
        # 依据：GRADE（Guyatt 2011）升级因素不能抵消严重方法学缺陷
        has_serious_bias = appraisal.get("risk_of_bias") in ("SERIOUS", "VERY_SERIOUS")

        if not has_serious_bias:
            if appraisal.get("large_effect") == "YES":
                points += 1
            if appraisal.get("dose_response") == "YES":
                points += 1
            if appraisal.get("confounding_bias_mitigates") == "YES":
                points += 1

        # 观察性研究升级上限：Moderate（3分），不可达到 High
        points = min(points, 3)

    # 4. 全局上下限
    points = max(1, min(4, points))
    return _POINTS_TO_GRADE[points]
```

### 各 study_type 的行为汇总

| study_type | 初始分 | 能否升级 | 实际上限 |
|---|---|---|---|
| RCT | 4 | 否 | High（4） |
| SR/MA/NMA（含RCT） | 4 | 否（当前迭代） | High（4） |
| SR/MA/NMA（混合） | 3 | 否（当前迭代） | Moderate（3） |
| SR/MA/NMA（含观察性） | 2 | 否（当前迭代） | Low（2） |
| GUIDELINE | 3 | 否 | Moderate（3） |
| COHORT / CASE_CONTROL | 2 | 是（无严重偏倚时） | Moderate（3） |
| CROSS_SECTIONAL | 2 | 否 | Low（2） |
| NARRATIVE_REVIEW / CASE_REPORT / EXPERT_OPINION | 1 | 否 | Very Low（1） |

---

## appraise_agent.txt 新增字段说明

### 新增：`included_study_type`（仅 SR/MA/NMA 时填写）

```
included_study_type（仅当 study_type 为 SYSTEMATIC_REVIEW/META_ANALYSIS/NMA 时填写）：

- RCT：纳入研究以 RCT 为主（≥80%），适用于治疗性 SR
- OBSERVATIONAL：纳入研究以观察性研究为主（≥80%），如队列研究的 MA
- MIXED：RCT 和观察性研究均占实质性比例（RCT 20%~79% 之间）
          注意：若同时包含 RCT 和病例报告/专家意见，应视实际构成决定，
          不要因少量低质量研究而选 MIXED
- UNKNOWN：文章未报告纳入研究类型，或无法从摘要判断

判断规则（优先级从高到低）：
  1. RCT ≥80% → RCT
  2. 观察性研究（队列/病例对照/横断面）≥80% → OBSERVATIONAL
  3. 其余（含灰区 RCT 20%~79%）→ MIXED（保守取 Moderate）
  4. 无法判断 → UNKNOWN（同 MIXED，保守取 Moderate）
```

### 新增升级因素：`confounding_bias_mitigates`（仅 COHORT/CASE_CONTROL）

```
confounding_bias_mitigates（负偏倚，仅适用于 COHORT / CASE_CONTROL）：

- YES：所有合理的残余混杂因素均使观察到的效应偏向无效（低估真实效应），
        即实际效应可能比观测值更大 → +1级
        例：未校正的混杂因素会降低而非夸大所观察到的关联
- NO：残余混杂方向不确定，或偏向夸大效应（高估真实效应）
- NA：不适用（非 COHORT/CASE_CONTROL，或无法判断混杂方向）
```

### 更新：升级因素适用范围说明

```
### 三、升级因素（仅适用于 COHORT / CASE_CONTROL，且 risk_of_bias 为 NOT_SERIOUS 时）

注意：
- CROSS_SECTIONAL 研究不适用升级因素（不评价因果效应）
- 存在 SERIOUS 或 VERY_SERIOUS 偏倚风险时，升级因素不适用
- 观察性研究即使所有升级因素均触发，最终等级上限为 Moderate
```

---

## `grade_rationales` 新增字段

`appraise_agent.py` 的 `grade_rationales` 记录中新增：

```python
grade_rationales.append({
    ...
    "included_study_type": appraisal.get("included_study_type", "NA"),  # SR/MA/NMA 专用
    "confounding_bias_mitigates": appraisal.get("confounding_bias_mitigates", "NA"),
    "upgrade_blocked_by_bias": (
        study_type in _UPGRADE_STUDY_TYPES
        and appraisal.get("risk_of_bias") in ("SERIOUS", "VERY_SERIOUS")
    ),
    ...
})
```

`upgrade_blocked_by_bias` 字段用于向 Judge 和下游传递"升级因素因偏倚风险被阻断"的信息，供审计使用。

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/agents/appraise_agent.py` | 修改 | `_compute_grade` 重写；`_INITIAL_POINTS` 移除 SR/MA/NMA；新增 `_SR_INITIAL_POINTS`、`_UPGRADE_STUDY_TYPES`；升级前置条件（偏倚检查）；升级上限 `min(points, 3)`；`grade_rationales` 新增3个字段 |
| `src/config/prompts/appraise_agent.txt` | 修改 | 新增 `included_study_type` 字段（SR/MA/NMA 必填，含判断规则）；新增 `confounding_bias_mitigates` 升级因素；更新升级因素适用范围说明 |

---

## 已知遗留问题（后续迭代）

- **CROSS_SECTIONAL 在 PIRD（诊断准确性）语境下**：DTA 研究的标准设计是横断面研究，应使用 QUADAS-2 而非 RoB 2 评价偏倚，初始分逻辑可能需按 `route_type` 分支处理
- **SR 纳入观察性研究时的升级因素**：理论上如果纳入的队列研究有 large_effect，该 SR 也可升级，当前迭代保守不处理
