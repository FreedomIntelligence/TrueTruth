# Judge Rubrics 重设计规范

**日期**: 2026-04-22
**范围**: Ask / Acquire / Appraise / Apply 四个阶段的 Judge 评分架构重设计
**不在本次范围内**: Assess 阶段 Judge；`_score_*` Python 侧的具体实现代码；prompt 文件的逐字改写

---

## 一、整体架构

### 设计动机

原架构中 LLM Judge 输出 YES/PARTIAL/NO 分类标签，Python 侧将其映射为连续分数（如 PARTIAL→0.4）。这层映射对 LLM 和人工标注者均不透明，导致：

1. LLM 不知道自己的 PARTIAL 会被算成多少分，判断标准模糊
2. 标注数据集验证时，人工标注者无法复现评分逻辑

新架构采用 **Gate + Weighted Rubrics**：

- **Gate（一票否决）**：任一 gate 项 = NO → 整体 fail，跳过评分，直接触发对应决策动作
- **Weighted Rubrics**：每条 rubric 有固定权重（Critical=3 / Major=2 / Minor=1），YES=满分，PARTIAL=满分×0.5，NO=0
- **总分** = Σ(得分) / Σ(满分)，≥ 0.7 → pass

### 执行流程

```
LLM Judge
  ↓ 输出每条 rubric 的 YES / PARTIAL / NO
Python 侧
  ↓ Step 1: Gate 检查（任一 gate rubric = NO → 立即 fail，跳过评分）
  ↓ Step 2: Weighted rubric 评分（YES=满分, PARTIAL=半分, NO=0）
  ↓ Step 3: 总分 = Σ(得分) / Σ(满分)，≥ 0.7 → pass
决策模型
  ↓ 读取 gate 失败项 / 低分 rubric 群 → 生成定向 retry 指令
```

### 分值体系

| 类型 | 权重 | YES | PARTIAL | NO |
|---|---|---|---|---|
| Gate（一票否决） | 不参与评分 | 通过 | 不存在 | 整体 fail |
| Critical rubric | 3 | 3分 | 1.5分 | 0分 |
| Major rubric | 2 | 2分 | 1分 | 0分 |
| Minor rubric | 1 | 1分 | 0.5分 | 0分 |

### 标注数据集友好性原则

每条 rubric 在 prompt 中必须包含三行明确标准：
- **YES 标准**：明确的通过条件
- **PARTIAL 标准**：明确的部分通过条件（不是"大致符合"，而是具体描述）
- **NO 标准**：明确的不通过条件

人工标注者和 LLM 面对同一套判断标准，可直接对比输出结果以验证 LLM Judge 的忠实度。

---

## 二、Ask 阶段

### Gate 项

| Gate | YES | NO |
|---|---|---|
| `intent_not_distorted` | 结构化结果忠实反映原问题意图（方向性正确：人群、问题类型） | 方向性错误（问儿童→写成人；问治疗→写诊断） |
| `route_correct` | route_type 与问题类型匹配 | 明显错误（诊断准确性问题路由为 ebm_pico） |

`direct_answer` 路由额外 gate：

| Gate | YES | NO |
|---|---|---|
| `nonresearch_classification_correct` | 三条触发条件全部满足（立即操作性指导 + 延迟危及生命 + 公认标准流程） | 任一条件不满足，应重路由到 EBM 流程 |

### Rubric 评分项（仅适用于 EBM 路由，direct_answer 不评分）

**Critical（满分3）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `core_dimensions_present` | P + 主焦点维度（I/IndexTest/Exposure/PF）+ O 均有实质内容 | 三者中有一个描述极度模糊但方向正确 | 任一核心维度完全缺失或填写错误 |

**Major（满分2）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `secondary_dimensions_present` | 次要维度（C/R/TH）按路由要求填写，原问题未涉及的填 NA | 次要维度有轻微偏差但不影响检索方向 | 次要维度明显错误（如 PIRD 的 R 字段填了干预措施） |

**Minor（满分1）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `statement_unambiguous` | 表述无歧义，可直接用于检索 | 有轻微歧义但不影响检索方向 | 严重歧义，检索方向不确定 |

### 满分计算

EBM 路由：Critical(3) + Major(2) + Minor(1) = **6分满分**

### 决策模型

```
route_type = direct_answer
  nonresearch_classification_correct = YES → terminate（流程终止，直接回答）
  nonresearch_classification_correct = NO  → retry_route（重路由到 ebm_pico）

route_type = ebm_*
  Gate 失败
    intent_not_distorted = NO → retry，指令：重新理解原问题意图，不得改变人群/问题类型
    route_correct = NO        → retry_route，指令：重新判断问题类型并选择正确路由框架

  评分 < 0.7（无 gate 失败）
    core_dimensions_present 低 → retry_structure，指令：补全缺失的核心维度
    secondary_dimensions 低    → retry_structure，指令：修正次要维度
    超过 max_retry             → fallback：强制 ebm_pico，写入 route_confidence=low

  评分 ≥ 0.7 且无 gate 失败 → proceed
```

---

## 三、Acquire 阶段

### Gate 项

| Gate | YES | NO |
|---|---|---|
| `search_terms_valid` | 检索词方向正确，能对应到 PICO/PIRD/PEO/Prognosis 的核心概念 | 检索词方向完全错误（如问心衰治疗却检索肾功能指标） |

### 特殊路径：evidence_gap

检索词有效但结果为零（`search_exhausted=true`）→ 不触发 gate，直接 proceed，写入 `evidence_gap_detected=true`，跳过评分。

### Rubric 评分项

**Critical（满分3）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `keywords_cover_pico_dimensions` | 关键词覆盖 P + 主焦点维度（I/IndexTest/Exposure/PF），且至少含一个可在 MeSH 验证的标准词 | 覆盖了 P 或主焦点之一，但另一维度无对应关键词；或有覆盖但无 MeSH 标准词 | 关键词全部指向同一概念，未覆盖多个维度 |
| `primary_focus_match` | 证据中的核心干预/暴露/测试与查询主焦点维度精准匹配 | 同类方法但有差异（不同剂量/版本），相关性高 | 完全不同的测试/干预/暴露 |
| `outcome_match` | 证据报告了临床关心的直接结局指标 | 报告了代理指标或部分相关结局 | 未报告任何相关结局 |

**Major（满分2）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `keywords_have_synonyms` | 核心概念有同义词/变体（如 SGLT2i + empagliflozin + dapagliflozin） | 有部分同义词但不完整 | 无任何同义词扩展，仅有单一术语 |
| `keywords_count_sufficient` | 关键词数量 ≥ 5 个 | 3-4 个 | ≤ 2 个 |
| `study_design_matches_route` | 纳入文献的研究设计与 route_type 的优先级匹配（见下方匹配表） | 有次优先级文献但无第一优先级，或混入少量不匹配设计 | 大量纳入与 route_type 不匹配的研究设计 |
| `population_match` | 证据中的研究人群与查询 Patient 匹配（年龄段、疾病状态） | 有轻微差异（年龄范围略不同），结论可审慎外推 | 严重不匹配（成人证据用于儿科；完全不同疾病） |

**Minor（满分1）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `top_selection_appropriate` | 排名靠前的文献是相关性最高、研究设计级别最高的 | 排序有轻微偏差，个别文献位置不最优 | 排名靠前的文献明显不如排名靠后的文献 |
| `selection_count_appropriate` | 选取数量合理（有效候选多时选足，质量差时不强行凑数） | 数量略多或略少，但不影响后续评价 | 明显不合理（大量高质量候选却只选1-2篇，或质量极差仍凑满10篇） |
| `key_sentences_present` | Top 文章的 key_sentences 非空，RAG 流程正常执行 | 部分文章 key_sentences 为空（摘要极短导致 chunk 失败） | 所有文章 key_sentences 均为空，RAG 流程可能失败 |

### 研究设计与 route_type 匹配表

| route_type | 第一优先级 | 第二优先级 | 第三优先级 | 通常排除 |
|---|---|---|---|---|
| ebm_pico（治疗） | SR/Meta分析（基于RCT） | RCT | 观察性研究 | 机制综述、专家意见、病例报告 |
| ebm_pird（诊断） | SR/Meta分析（基于诊断准确性研究） | 诊断准确性研究（横断面） | 回顾性诊断研究 | 机制综述、治疗类RCT |
| ebm_peo（病因/危害） | SR/Meta分析（基于观察性研究） | 前瞻性队列研究 | 病例对照研究 | RCT、机制综述 |
| ebm_prognosis（预后） | SR/Meta分析（基于队列研究） | 前瞻性队列研究 | 回顾性队列研究 | 机制综述、病例报告 |

### 满分计算

Critical(3×3) + Major(2×4) + Minor(1×3) = **9 + 8 + 3 = 20分满分**

### 决策模型

```
evidence_gap_detected = true → proceed（标记 evidence_gap，Apply 阶段处理）

Gate 失败
  search_terms_valid = NO → retry，指令：根据 PICO/PIRD/PEO/Prognosis 重新构建检索词

评分 < 0.7（无 gate 失败）
  keywords_* 低                          → retry，指令：补充同义词/MeSH词/覆盖缺失维度
  primary_focus_match / outcome_match 低 → retry，指令：调整检索词以匹配主焦点和结局
  study_design_matches_route 低          → retry，指令：调整研究设计过滤器
  population_match = NO                  → backtrack 到 Ask，指令：重新确认 Patient 维度定义
  超过 max_retry                         → proceed（降级，写入 evidence_quality_warning）

评分 ≥ 0.7 且无 gate 失败 → proceed
```

---

## 四、Appraise 阶段

### 两层架构

Appraise Judge 分两层执行，Layer 1 通过则不调用 LLM。

#### Layer 1：Python 硬编码校验（Gate 等价）

| 检查项 | 通过条件 | 失败动作 |
|---|---|---|
| `all_studies_have_study_type` | 每篇文献都有 study_type 字段且值合法 | 触发 Layer 2 LLM Judge |
| `all_studies_have_rob_fields` | 每篇文献都有 risk_of_bias 字段 | 触发 Layer 2 LLM Judge |
| `grade_inputs_complete` | GRADE 计算所需字段无缺失 | 触发 Layer 2 LLM Judge |
| `grade_output_in_legal_range` | 最终等级在 {High/Moderate/Low/Very Low} 内 | 抛出系统异常，不重试 |

全部通过 → 直接 proceed，不调 LLM Judge。

#### Layer 2：LLM Judge Gate 项

| Gate | YES | NO |
|---|---|---|
| `study_type_correct` | 所有研究的 study_type 识别正确 | 存在明显错误（观察性研究标记为 RCT） |
| `computed_grade_reasonable` | 计算出的 GRADE 等级与基于摘要的独立判断一致 | 明显不合理（通常是 study_type 或降级因素错误导致） |

注意：以下情况属于**合理结果**，`computed_grade_reasonable` 不应判断为 NO：
- SR/MA 纳入观察性研究（included_study_type=OBSERVATIONAL）→ 初始分为 Low，即使无降级因素也可能输出 Low/Very Low
- COHORT/CASE_CONTROL 存在 SERIOUS 偏倚时，即使 large_effect=YES 也不升级
- CROSS_SECTIONAL 无升级因素 → 最高只能到 Low

### Rubric 评分项

**Critical（满分3）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 | 适用条件 |
|---|---|---|---|---|
| `downgrade_factors_appropriate` | 四个降级因素（risk_of_bias/inconsistency/indirectness/imprecision）的严重程度标注与摘要信息相符 | 整体合理，个别因素有轻微偏差（过宽或过严） | 存在明显错误（未盲法 RCT 标记为 NOT_SERIOUS 偏倚风险） | 始终 |
| `included_study_type_correct` | SR/MA/NMA 的 included_study_type 与摘要描述的纳入研究类型相符 | 摘要信息不足以确认（填 UNKNOWN 是合理选择） | 明显错误（摘要写"仅纳入RCT"但标注为 OBSERVATIONAL） | 仅当证据列表含 SR/MA/NMA |

**Major（满分2）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 | 适用条件 |
|---|---|---|---|---|
| `upgrade_factors_appropriate` | 升级因素（large_effect/dose_response/confounding_bias_mitigates）标注与摘要信息相符 | 整体合理，个别因素有轻微偏差 | 明显错误（无剂量效应数据但标注 dose_response=YES） | 仅当证据列表含 COHORT/CASE_CONTROL |
| `upgrade_blocked_appropriate` | 存在 SERIOUS/VERY_SERIOUS 偏倚时，upgrade_blocked_by_bias=True 且最终等级未因升级因素提升 | — | 存在严重偏倚但升级因素仍被计入 | 仅当含 COHORT/CASE_CONTROL 且 risk_of_bias=SERIOUS/VERY_SERIOUS |
| `conflicts_identified` | 证据间存在实质性冲突时，冲突被正确识别并描述 | 冲突识别不完整，遗漏了部分冲突说明 | 存在明显冲突但完全未识别 | 始终 |

**Minor（满分1）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 | 适用条件 |
|---|---|---|---|---|
| `numerical_data_extracted` | 摘要中存在效应量/CI/P值时均被提取 | 部分提取，有遗漏但不影响 GRADE 结论 | 存在数值数据但完全未提取 | 始终 |

### 满分计算（最大情形）

Critical(3×2) + Major(2×3) + Minor(1×1) = **6 + 6 + 1 = 13分满分**（NA 项不参与分母）

### 决策模型

```
Layer 1 全部通过 → proceed（不调 LLM Judge）

Layer 1 失败 → 触发 LLM Judge
  grade_output_in_legal_range 失败 → 系统异常，终止

  LLM Judge Gate 失败
    study_type_correct = NO        → retry（重新执行整个 Appraise）
    computed_grade_reasonable = NO → retry（重新执行整个 Appraise）

  LLM Judge 定位问题根因
    某篇文献字段缺失 + 根因 = LLM漏读   → 重新提取该文献，回到 Appraise 重算
    某篇文献字段缺失 + 根因 = 文献本身不足 → 标记该文献剔除，回到 Appraise 重算

  评分 < 0.7（无 gate 失败）
    downgrade_factors 低   → retry，指令：重新评估指定降级因素
    conflicts_identified 低 → retry，指令：补充冲突识别

  所有文献标记"信息不足"后 GRADE = Very Low 且文献数量不足
    → backtrack 到 Acquire，指令：扩大检索范围

  评分 ≥ 0.7 且无 gate 失败 → proceed
```

---

## 五、Apply 阶段

### Gate 项

| Gate | YES | NO |
|---|---|---|
| `recommendation_grounded_in_evidence` | 推荐意见基于本次检索的证据，方向与证据一致 | 推荐与证据无关或方向相反 |
| `route_dimension_consistent` | Apply 的维度一致性检查使用了与 route_type 匹配的框架（PICO/PIRD/PEO/Prognosis） | 使用了错误框架（如 PIRD 问题用 PICO 框架，Index Test 被映射为 Intervention） |
| `strength_not_grossly_inflated` | 推荐强度未严重超出证据上限 | Very Low 或 Low 证据给出 Strong 推荐，或有充分高质量证据却输出 No Recommendation |

### Rubric 评分项

**Critical（满分3）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `effect_size_correctly_reported` | 效应量、置信区间、GRADE 等级被正确转述，无数据失真 | 数值基本正确，有轻微表述偏差但不影响结论方向 | 效应量或 GRADE 等级被错误转述，导致结论方向改变 |
| `strength_matches_evidence` | 推荐强度与证据等级严格匹配（含 inconsistency=SERIOUS 时 Moderate→Weak 的降强推荐属正确行为） | 有轻微偏差（如 Moderate 证据给 Strong，但结果高度一致且无 inconsistency 问题），临床上可接受 | 推荐强度与证据等级明显不符（不触发 gate 的中等程度不匹配） |

**Major（满分2）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `population_applicability_addressed` | 明确说明证据人群与当前患者的匹配程度，包括可外推性或外推限制 | 有提及人群差异但说明不充分 | 完全未讨论人群适配性 |
| `uncertainty_source_explained` | 不确定性的来源被明确说明（如样本量不足、间接证据、研究设计局限） | 提及了不确定性但未说明来源 | 未提及不确定性，或仅说"证据有限"而无来源说明 |
| `citation_traceable` | 推荐依据有文献溯源（PMID 或标题可追溯） | 部分推荐有溯源，部分缺失 | 无任何文献溯源 |

**Minor（满分1）**

| Rubric | YES 标准 | PARTIAL 标准 | NO 标准 |
|---|---|---|---|
| `recommendation_specific` | 推荐内容具体，临床医生可据此执行（含适应症、关键参数等） | 推荐方向明确但缺少关键细节 | 推荐过于模糊，无法指导临床决策 |
| `patient_preference_considered` | 患者偏好或价值观被纳入推荐表述（或明确说明不适用） | 有提及但表述笼统 | 完全未提及患者偏好 |

### 满分计算

Critical(3×2) + Major(2×3) + Minor(1×2) = **6 + 6 + 2 = 14分满分**

### 决策模型

```
Gate 失败
  recommendation_grounded_in_evidence = NO
    → retry，指令：严格基于本次检索证据重新生成推荐，不得引入外部知识

  route_dimension_consistent = NO
    → retry，指令：按 {route_type} 对应框架重新执行维度一致性检查

  strength_not_grossly_inflated = NO
    → retry，指令：依据 GRADE 原则重新确定推荐强度

评分 < 0.7（无 gate 失败）
  effect_size_correctly_reported 低
    → retry，指令：修正数据转述，对照 Appraise 输出逐项核查效应量和 GRADE 等级

  strength_matches_evidence 低
    → retry，指令：加强推荐强度约束

  strength_matches_evidence = PARTIAL 且推荐强度 < 证据下限（过度保守）
    → backtrack 到 Appraise，指令：重新检查 GRADE 评估是否存在隐含降级

  population_applicability / uncertainty_source 低
    → retry，指令：补充外推性分析和不确定性来源说明

  citation_traceable 低
    → retry，指令：补充文献溯源

  clinical_fit 低且根因 = 证据根本不适用当前患者
    → backtrack 到 Acquire，指令：检索更匹配的文献（Judge 需说明不适用的具体原因）

超过 max_retry
  → 输出"当前证据不足以形成推荐意见"+ 证据摘要（合法终止路径）

评分 ≥ 0.7 且无 gate 失败 → proceed（输出最终推荐）
```

---

## 六、标注数据集设计说明

### 验证目标

通过人工标注 vs LLM Judge 输出的对比，验证 LLM Judge 是否能忠实执行上述 rubric 规则。

### 标注样本结构

每个标注样本包含：

```json
{
  "stage": "Ask | Acquire | Appraise | Apply",
  "input": {
    "original_question": "...",
    "stage_output": { ... },
    "context": { ... }
  },
  "rubric_labels": {
    "gate_items": {
      "intent_not_distorted": "YES | NO",
      ...
    },
    "scored_rubrics": {
      "core_dimensions_present": "YES | PARTIAL | NO",
      ...
    }
  },
  "overall_verdict": "pass | fail | gate_fail",
  "annotator_notes": "..."
}
```

### 标注质量保障

1. **Gate 项只有 YES/NO**：标注者无需判断程度，降低歧义
2. **每条 rubric 有三行明确标准**：YES/PARTIAL/NO 标准均有具体描述，不依赖标注者主观判断
3. **NA 项明确标注**：适用条件不满足时标注 NA，不参与一致性计算
4. **分歧处理**：Gate 项分歧 → 讨论解决；Scored rubric 分歧 → 允许 ±1 级（如一人 YES 一人 PARTIAL）视为一致

### 一致性指标

- Gate 项：Cohen's κ（二分类）
- Scored rubrics：Weighted κ（三分类 YES/PARTIAL/NO）
- 目标：κ ≥ 0.7（substantial agreement）

---

## 七、与现有代码的对接说明

### `judge_llm.py` 改动方向

| 函数 | 改动 |
|---|---|
| `_score_ask` | 按新 rubric 体系重写；增加 gate 检查；移除 keywords 相关评分 |
| `_score_acquire` | 按新 rubric 体系重写；增加 keywords 评分（从 Ask 迁移）；字段名更新（`primary_focus_match` 替代 `pico_i_match`） |
| `_score_appraise` | 增加 Layer 1 Python 校验前置；Layer 2 LLM Judge 按新 rubric 重写 |
| `_score_apply` | 按新 rubric 体系重写；增加 gate 检查 |
| `STAGE_WEIGHTS` | 替换为 rubric 权重表（Critical=3/Major=2/Minor=1） |

### prompt 文件改动方向

每个阶段的 `*_judge.txt` 需要：
1. 将每条 rubric 以独立段落呈现，包含 YES/PARTIAL/NO 三行标准
2. Gate 项单独列出，明确标注"一票否决"
3. 输出格式统一为 `gate_results` + `rubric_results` + `failures` + `overall_quality`

具体 prompt 改写不在本规范范围内，由实现阶段处理。
