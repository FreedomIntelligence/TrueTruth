# Judge Rubrics 重设计实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Ask/Acquire/Appraise/Apply 四个阶段的 Judge 改造为 Gate + Weighted Rubrics 架构，使评分逻辑对 LLM 和人工标注者均透明可验证。

**Architecture:** LLM Judge 输出每条 rubric 的 YES/PARTIAL/NO；Python 侧先做 Gate 检查（任一 NO → 立即 fail），再按 Critical=3/Major=2/Minor=1 权重计算总分，≥0.7 → pass。决策模型读取 gate 失败项和低分 rubric 群生成定向 retry 指令。

**Tech Stack:** Python 3.10+, LangChain LLM, pytest

---

## 文件改动清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `src/config/prompts/judge/ask_judge.txt` | 重写 | Gate + rubric 结构，动态路由段注入 |
| `src/config/prompts/judge/acquire_judge.txt` | 重写 | Gate + rubric 结构，keywords 评分迁入 |
| `src/config/prompts/judge/appraise_judge.txt` | 重写 | Gate + rubric 结构，新增升级因素审计 |
| `src/config/prompts/judge/apply_judge.txt` | 重写 | Gate + rubric 结构，route_dimension 审计 |
| `src/judge/judge_llm.py` | 修改 | `_score_*` 函数全部重写；新增 `_check_gates`；`STAGE_WEIGHTS` 替换为 rubric 权重表；Appraise 新增 Layer 1 Python 校验 |
| `tests/test_judge_rubrics.py` | 新建 | 各阶段 rubric 评分单元测试 |

---

## Task 1: 重写 `ask_judge.txt`

**Files:**
- Modify: `src/config/prompts/judge/ask_judge.txt`

- [ ] **Step 1: 写入新 prompt**

完整替换 `ask_judge.txt` 内容为以下内容（注意 JSON 输出示例中的双花括号是 Python format 转义，实际文件写单花括号）：

```
# Role
你是一个严格的EBM审计员。对 Ask Agent 的输出进行客观分类判断，只输出结构化 JSON，不要打分。

# Input
原始问题：{original_question}
路由类型：{route_type}
Ask Agent 输出：{stage_output}

# 一票否决项（Gate）
以下任一项为 NO 时，整体判定为 gate_fail，无需继续评分。

## G1. intent_not_distorted
结构化结果是否忠实反映原问题意图（方向性：人群、问题类型）？
- YES：意图一致
- NO：方向性错误（问儿童→写成人；问治疗→写诊断）

## G2. route_correct（仅当 route_type != direct_answer 时判断，否则填 NA）
route_type 与问题类型是否匹配？
- YES：匹配
- NO：明显错误（如诊断准确性问题路由为 ebm_pico）
- NA：route_type = direct_answer，不适用

## G3. nonresearch_classification_correct（仅当 route_type = direct_answer 时判断，否则填 NA）
以下三条触发条件是否全部满足？
1. 问题要求立即操作性指导（动词：如何处理/立即给/紧急处置）
2. 延迟回答会直接危及患者生命安全
3. 答案来自已有公认标准流程（BLS/ACLS/指南操作章节）
- YES：三条均满足
- NO：任一条不满足（应重路由到 EBM 流程）
- NA：route_type != direct_answer，不适用

# Rubric 评分项（仅适用于 EBM 路由；direct_answer 路由时所有 rubric 填 NA）

## R1. core_dimensions_present【Critical，权重3】
P + 主焦点维度（ebm_pico→I；ebm_pird→IndexTest；ebm_peo→Exposure；ebm_prognosis→PF）+ O 是否均有实质内容？
- YES：三个核心维度均有实质内容
- PARTIAL：三者中有一个描述极度模糊（如 O="outcomes"）但方向正确
- NO：任一核心维度完全缺失或填写错误

## R2. secondary_dimensions_present【Major，权重2】
次要维度（ebm_pico→C；ebm_pird→R；ebm_prognosis→TH；ebm_peo 无次要维度填 NA）是否按路由要求填写？原问题未涉及的填 NA。
- YES：次要维度填写正确，或原问题未涉及时正确填 NA
- PARTIAL：次要维度有轻微偏差但不影响检索方向
- NO：次要维度明显错误（如 PIRD 的 R 字段填了干预措施）
- NA：ebm_peo 路由（无次要维度）

## R3. statement_unambiguous【Minor，权重1】
结构化表述是否无歧义，可直接用于检索？
- YES：表述明确，无歧义
- PARTIAL：有轻微歧义但不影响检索方向
- NO：严重歧义，检索方向不确定

# Output Format
仅输出以下 JSON，不要包含任何其他文本：

{
  "gate_results": {
    "intent_not_distorted": "YES | NO",
    "route_correct": "YES | NO | NA",
    "nonresearch_classification_correct": "YES | NO | NA"
  },
  "rubric_results": {
    "core_dimensions_present": "YES | PARTIAL | NO | NA",
    "secondary_dimensions_present": "YES | PARTIAL | NO | NA",
    "statement_unambiguous": "YES | PARTIAL | NO | NA"
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | gate_fail"
}
```

- [ ] **Step 2: 验证格式**

```bash
python3 -c "
from pathlib import Path
txt = Path('src/config/prompts/judge/ask_judge.txt').read_text()
assert '{original_question}' in txt
assert '{route_type}' in txt
assert '{stage_output}' in txt
assert 'gate_results' in txt
assert 'rubric_results' in txt
print('ask_judge.txt OK')
"
```

---

## Task 2: 重写 `acquire_judge.txt`

**Files:**
- Modify: `src/config/prompts/judge/acquire_judge.txt`

- [ ] **Step 1: 写入新 prompt**

完整替换 `acquire_judge.txt` 内容为：

```
# Role
你是一个严格的EBM审计员。对 Acquire Agent 的输出进行客观分类判断，只输出结构化 JSON，不要打分。

# 核心EBM原则
证据质量 ≠ 证据数量。1篇Cochrane系统评价 > 10篇RCT > 100篇病例报告。

# Input
路由类型：{route_type}
结构化查询：{ebm_query}
Acquire Agent 输出（已排序的证据列表）：{stage_output}

# 预处理：系统错误检测
首先检查输入数据中是否包含 error 字段（如 "error": "Connection timeout"）：
如果存在 error 字段，说明 PubMed API 调用本身失败，与检索词无关。
此时跳过所有审计项，直接输出：search_terms_valid=YES，所有 rubric 填 NA，search_exhausted=false，failures=[]，overall_quality=pass。

# 一票否决项（Gate）

## G1. search_terms_valid
检索词方向是否正确，能对应到查询的核心概念？
- YES：检索词方向正确
- NO：检索词方向完全错误（如问心衰治疗却检索肾功能指标）

# Rubric 评分项

各 route_type 对应的主焦点维度：
- ebm_pico：Intervention
- ebm_pird：Index Test
- ebm_peo：Exposure
- ebm_prognosis：Prognostic Factor

## R1. keywords_cover_pico_dimensions【Critical，权重3】
关键词是否覆盖 P + 主焦点维度，且至少含一个可在 MeSH 验证的标准词？
- YES：覆盖 P + 主焦点维度，且含 MeSH 标准词
- PARTIAL：覆盖了 P 或主焦点之一，但另一维度无对应关键词；或有覆盖但无 MeSH 标准词
- NO：关键词全部指向同一概念，未覆盖多个维度

## R2. primary_focus_match【Critical，权重3】
基于证据列表中主焦点匹配度最好的那篇证据判断：证据中的核心干预/暴露/测试是否与查询主焦点维度匹配？
- YES：精准匹配
- PARTIAL：同类方法但有差异（不同剂量/版本），相关性高
- NO：完全不同的测试/干预/暴露

## R3. outcome_match【Critical，权重3】
基于证据列表中结局匹配度最好的那篇证据判断：证据是否报告了临床关心的结局指标？
- YES：报告了直接结局指标
- PARTIAL：报告了代理指标或部分相关结局
- NO：未报告任何相关结局

## R4. keywords_have_synonyms【Major，权重2】
核心概念是否有同义词/变体（如 SGLT2i + empagliflozin + dapagliflozin）？
- YES：有同义词/变体
- PARTIAL：有部分同义词但不完整
- NO：无任何同义词扩展，仅有单一术语

## R5. keywords_count_sufficient【Major，权重2】
关键词数量是否充足？
- YES：≥ 5 个
- PARTIAL：3-4 个
- NO：≤ 2 个

## R6. study_design_matches_route【Major，权重2】
纳入文献的研究设计是否与 route_type 的优先级匹配？
匹配表：
- ebm_pico：第一优先级=SR/Meta分析(基于RCT)，第二=RCT，第三=观察性研究，排除=机制综述/专家意见/病例报告
- ebm_pird：第一优先级=SR/Meta分析(基于诊断准确性研究)，第二=诊断准确性研究(横断面)，第三=回顾性诊断研究，排除=机制综述/治疗类RCT
- ebm_peo：第一优先级=SR/Meta分析(基于观察性研究)，第二=前瞻性队列，第三=病例对照，排除=RCT/机制综述
- ebm_prognosis：第一优先级=SR/Meta分析(基于队列研究)，第二=前瞻性队列，第三=回顾性队列，排除=机制综述/病例报告
- YES：有第一优先级文献
- PARTIAL：有次优先级文献但无第一优先级，或混入少量不匹配设计
- NO：大量纳入与 route_type 不匹配的研究设计

## R7. population_match【Major，权重2】
基于证据列表中人群匹配度最好的那篇证据判断：研究人群是否与查询 Patient 匹配？
- YES：精准匹配（相同年龄段、相同疾病状态）
- PARTIAL：有轻微差异，结论可审慎外推
- NO：严重不匹配（成人证据用于儿科；完全不同疾病）

## R8. top_selection_appropriate【Minor，权重1】
排名靠前的文献（排名第1-3位）是否确实是列表中最优的证据选择？
- YES：排名前列的文献研究层级高且匹配度好
- PARTIAL：总体合理，但有个别文献位置不最优
- NO：排名顺序明显不合理（如病例报告排在SR/RCT前面）

## R9. selection_count_appropriate【Minor，权重1】
选取数量是否合理？
- YES：数量与候选质量相符
- PARTIAL：数量略多或略少，但整体可接受
- NO：明显不合理（大量高质量候选却只选1-2篇，或质量极差仍凑满10篇）

## R10. key_sentences_present【Minor，权重1】
Top 文章的 key_sentences 字段是否有实质内容？
- YES：Top 文章的 key_sentences 非空，RAG 流程正常执行
- PARTIAL：部分文章 key_sentences 为空（摘要极短导致 chunk 失败）
- NO：所有文章 key_sentences 均为空，RAG 流程可能失败

# Output Format
仅输出以下 JSON，不要包含任何其他文本：

{
  "gate_results": {
    "search_terms_valid": "YES | NO"
  },
  "rubric_results": {
    "keywords_cover_pico_dimensions": "YES | PARTIAL | NO",
    "primary_focus_match": "YES | PARTIAL | NO",
    "outcome_match": "YES | PARTIAL | NO",
    "keywords_have_synonyms": "YES | PARTIAL | NO",
    "keywords_count_sufficient": "YES | PARTIAL | NO",
    "study_design_matches_route": "YES | PARTIAL | NO",
    "population_match": "YES | PARTIAL | NO",
    "top_selection_appropriate": "YES | PARTIAL | NO",
    "selection_count_appropriate": "YES | PARTIAL | NO",
    "key_sentences_present": "YES | PARTIAL | NO"
  },
  "search_exhausted": false,
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | gate_fail"
}
```

- [ ] **Step 2: 验证格式**

```bash
python3 -c "
from pathlib import Path
txt = Path('src/config/prompts/judge/acquire_judge.txt').read_text()
assert '{route_type}' in txt
assert '{ebm_query}' in txt
assert '{stage_output}' in txt
assert 'gate_results' in txt
assert 'rubric_results' in txt
assert 'search_exhausted' in txt
print('acquire_judge.txt OK')
"
```

---

## Task 3: 重写 `appraise_judge.txt`

**Files:**
- Modify: `src/config/prompts/judge/appraise_judge.txt`

- [ ] **Step 1: 写入新 prompt**

完整替换 `appraise_judge.txt` 内容为：

```
# Role
你是一个严格的EBM审计员。对 Appraise Agent 的GRADE评价进行客观分类判断，只输出结构化 JSON，不要打分。

# 背景说明
Appraise Agent 输出结构化的GRADE分类标签（study_type、risk_of_bias等），最终GRADE等级由系统代码根据这些标签自动计算。你的审计重点是：
1. LLM对研究类型（study_type）的识别是否正确
2. 各降级/升级因素的分类是否合理
3. 系统计算出的GRADE等级（computed_grade）是否与你的独立判断一致

# Input
证据列表：{evidence_list}
Appraise Agent 输出（包含分类标签和计算结果）：{stage_output}

# 一票否决项（Gate）

## G1. study_type_correct
所有研究的 study_type 识别是否正确？
- YES：所有研究的 study_type 识别正确
- NO：存在明显错误（如将观察性研究标记为RCT）

## G2. computed_grade_reasonable
系统计算出的最终GRADE等级（computed_grade）是否合理？
- YES：计算结果与基于摘要的独立判断一致
- NO：明显不合理（通常是 study_type 或降级因素错误导致）

注意：以下情况属于合理结果，不应判断为 NO：
- SR/MA 纳入观察性研究（included_study_type=OBSERVATIONAL）→ 初始分为 Low，即使无降级因素也可能输出 Low/Very Low
- COHORT/CASE_CONTROL 存在 SERIOUS 偏倚时，即使 large_effect=YES 也不升级
- CROSS_SECTIONAL 无升级因素 → 最高只能到 Low

# Rubric 评分项

## R1. downgrade_factors_appropriate【Critical，权重3】
四个降级因素（risk_of_bias/inconsistency/indirectness/imprecision）的严重程度标注是否与摘要信息相符？
- YES：各因素的严重程度标签（NOT_SERIOUS/SERIOUS/VERY_SERIOUS）与摘要信息相符
- PARTIAL：整体合理，但个别因素评估过于宽松或严苛
- NO：存在明显错误（如未盲法 RCT 标记为 NOT_SERIOUS 偏倚风险）

## R2. included_study_type_correct【Critical，权重3】
（仅当证据列表含 SYSTEMATIC_REVIEW/META_ANALYSIS/NMA 时判断，否则填 NA）
SR/MA/NMA 的 included_study_type 字段是否与摘要描述的纳入研究类型相符？
- YES：字段与摘要描述的纳入研究类型相符（如摘要明确描述"纳入RCT"→ RCT）
- PARTIAL：摘要信息不足以确认（如摘要未描述纳入类型 → UNKNOWN 是合理选择）
- NO：明显错误（如摘要写"仅纳入RCT"但标注为 OBSERVATIONAL）
- NA：证据列表中没有 SR/MA/NMA 类型研究

## R3. upgrade_factors_appropriate【Major，权重2】
（仅当证据列表含 COHORT/CASE_CONTROL 时判断，否则填 NA）
升级因素（large_effect/dose_response/confounding_bias_mitigates）的标注是否与摘要信息相符？
- YES：升级因素的 YES/NO 标注与摘要信息相符
- PARTIAL：整体合理，个别因素有轻微偏差
- NO：明显错误（如无明确剂量效应数据但标注 dose_response=YES）
- NA：证据列表中没有 COHORT/CASE_CONTROL 研究

## R4. upgrade_blocked_appropriate【Major，权重2】
（仅当含 COHORT/CASE_CONTROL 且 risk_of_bias=SERIOUS/VERY_SERIOUS 时判断，否则填 NA）
存在严重偏倚风险时，升级因素是否被正确阻断（upgrade_blocked_by_bias=True）？
- YES：risk_of_bias=SERIOUS/VERY_SERIOUS 时，upgrade_blocked_by_bias 正确标注为 True，且最终等级未因升级因素提升
- NO：存在严重偏倚但升级因素仍被计入
- NA：无 COHORT/CASE_CONTROL 研究，或 risk_of_bias 均为 NOT_SERIOUS

## R5. conflicts_identified【Major，权重2】
证据间存在实质性冲突时，冲突是否被正确识别并描述？
- YES：所有主要冲突均被识别，conflict_description 描述准确；或证据间无冲突（正确标记为无冲突）
- PARTIAL：识别了主要冲突，但有遗漏或描述不够深入
- NO：存在明显冲突但完全未识别

## R6. numerical_data_extracted【Minor，权重1】
摘要中存在效应量/CI/P值时，是否均被提取？
- YES：data_available 的判断准确，能识别摘要中存在的数值指标
- PARTIAL：判断基本合理，有轻微偏差
- NO：摘要有明确效应量但标记为未提取

# Output Format
仅输出以下 JSON，不要包含任何其他文本：

{
  "gate_results": {
    "study_type_correct": "YES | NO",
    "computed_grade_reasonable": "YES | NO"
  },
  "rubric_results": {
    "downgrade_factors_appropriate": "YES | PARTIAL | NO",
    "included_study_type_correct": "YES | PARTIAL | NO | NA",
    "upgrade_factors_appropriate": "YES | PARTIAL | NO | NA",
    "upgrade_blocked_appropriate": "YES | NO | NA",
    "conflicts_identified": "YES | PARTIAL | NO",
    "numerical_data_extracted": "YES | PARTIAL | NO"
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | gate_fail"
}
```

- [ ] **Step 2: 验证格式**

```bash
python3 -c "
from pathlib import Path
txt = Path('src/config/prompts/judge/appraise_judge.txt').read_text()
assert '{evidence_list}' in txt
assert '{stage_output}' in txt
assert 'gate_results' in txt
assert 'rubric_results' in txt
assert 'upgrade_blocked_appropriate' in txt
print('appraise_judge.txt OK')
"
```

---

## Task 4: 重写 `apply_judge.txt`

**Files:**
- Modify: `src/config/prompts/judge/apply_judge.txt`

- [ ] **Step 1: 写入新 prompt**

完整替换 `apply_judge.txt` 内容为：

```
# Role
你是一个严格的EBM审计员。对 Apply Agent 生成的临床推荐进行客观分类判断，只输出结构化 JSON，不要打分。

# Input
路由类型：{route_type}
结构化查询：{query_description}
证据评价结果（来自Appraise阶段）：{appraisal_results}
Apply Agent 输出（临床推荐）：{stage_output}

# 一票否决项（Gate）

## G1. recommendation_grounded_in_evidence
推荐意见是否基于本次检索的证据，方向与证据一致？
- YES：推荐完全来源于提供的证据，方向一致
- NO：推荐与证据无关或方向相反

## G2. route_dimension_consistent
Apply 的维度一致性检查是否使用了与 route_type 匹配的框架？
各 route_type 对应的正确框架：
- ebm_pico：Population / Intervention / Comparator / Outcome
- ebm_pird：Population / Index Test / Reference Standard / Target Condition
- ebm_peo：Population / Exposure / Outcome（无 Comparator）
- ebm_prognosis：Population / Prognostic Factor / Outcome / Time Horizon
- YES：维度框架与 route_type 匹配
- NO：使用了错误框架（如 PIRD 问题用 PICO 框架，Index Test 被映射为 Intervention）

## G3. strength_not_grossly_inflated
推荐强度是否未严重超出证据上限？
- YES：推荐强度在证据支持范围内
- NO：Very Low 或 Low 证据给出 Strong 推荐，或有充分高质量证据却输出 No Recommendation

# Rubric 评分项

## R1. effect_size_correctly_reported【Critical，权重3】
效应量、置信区间、GRADE 等级是否被正确转述，无数据失真？
- YES：数值被正确转述，无失真
- PARTIAL：数值基本正确，有轻微表述偏差但不影响结论方向
- NO：效应量或 GRADE 等级被错误转述，导致结论方向改变

## R2. strength_matches_evidence【Critical，权重3】
推荐强度是否与证据等级严格匹配？
注意：inconsistency=SERIOUS 时 Moderate→Weak 的降强推荐属正确行为，不应标注为不匹配。
EBM原则：Strong需要High/Moderate直接证据；Weak适用于Low质量或结果不一致；Conditional适用于仅有间接证据；Consensus-based适用于仅有专家共识/指南。
- YES：推荐强度与证据等级严格匹配（含上述特殊情况）
- PARTIAL：有轻微偏差（如 Moderate 证据给 Strong，但结果高度一致且无 inconsistency 问题），临床上可接受
- NO：推荐强度与证据等级明显不符（不触发 gate 的中等程度不匹配）

## R3. population_applicability_addressed【Major，权重2】
是否明确说明了证据人群与当前患者的匹配程度，包括可外推性或外推限制？
- YES：明确说明了人群匹配程度和外推性
- PARTIAL：有提及人群差异但说明不充分
- NO：完全未讨论人群适配性

## R4. uncertainty_source_explained【Major，权重2】
不确定性的来源是否被明确说明（如样本量不足、间接证据、研究设计局限）？
- YES：不确定性来源被明确说明
- PARTIAL：提及了不确定性但未说明来源
- NO：未提及不确定性，或仅说"证据有限"而无来源说明

## R5. citation_traceable【Major，权重2】
推荐依据是否有文献溯源（PMID 或标题可追溯）？
- YES：推荐依据有文献溯源
- PARTIAL：部分推荐有溯源，部分缺失
- NO：无任何文献溯源

## R6. recommendation_specific【Minor，权重1】
推荐内容是否足够具体，临床医生可据此执行（含适应症、关键参数等）？
- YES：推荐包含关键细节，临床医生可直接执行
- PARTIAL：推荐方向明确但缺少关键细节
- NO：推荐过于模糊，无法指导临床决策

## R7. patient_preference_considered【Minor，权重1】
患者偏好或价值观是否被纳入推荐表述（或明确说明不适用）？
- YES：患者偏好被纳入，或明确说明不适用
- PARTIAL：有提及但表述笼统
- NO：完全未提及患者偏好

# Output Format
仅输出以下 JSON，不要包含任何其他文本：

{
  "gate_results": {
    "recommendation_grounded_in_evidence": "YES | NO",
    "route_dimension_consistent": "YES | NO",
    "strength_not_grossly_inflated": "YES | NO"
  },
  "rubric_results": {
    "effect_size_correctly_reported": "YES | PARTIAL | NO",
    "strength_matches_evidence": "YES | PARTIAL | NO",
    "population_applicability_addressed": "YES | PARTIAL | NO",
    "uncertainty_source_explained": "YES | PARTIAL | NO",
    "citation_traceable": "YES | PARTIAL | NO",
    "recommendation_specific": "YES | PARTIAL | NO",
    "patient_preference_considered": "YES | PARTIAL | NO"
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | gate_fail"
}
```

- [ ] **Step 2: 验证格式**

```bash
python3 -c "
from pathlib import Path
txt = Path('src/config/prompts/judge/apply_judge.txt').read_text()
assert '{route_type}' in txt
assert '{query_description}' in txt
assert '{appraisal_results}' in txt
assert '{stage_output}' in txt
assert 'gate_results' in txt
assert 'rubric_results' in txt
assert 'route_dimension_consistent' in txt
print('apply_judge.txt OK')
"
```

---

## Task 5: 重写 `judge_llm.py` — 核心评分架构

**Files:**
- Modify: `src/judge/judge_llm.py`

- [ ] **Step 1: 替换 STAGE_WEIGHTS 为 rubric 权重表**

在 `judge_llm.py` 顶部，将 `STAGE_WEIGHTS` 替换为：

```python
# Rubric weight definitions per stage
# Each rubric: (weight, allows_partial)
# Gate items are not listed here — they are checked separately in _check_gates()
RUBRIC_WEIGHTS = {
    "Ask": {
        "core_dimensions_present":      (3, True),   # Critical
        "secondary_dimensions_present": (2, True),   # Major
        "statement_unambiguous":        (1, True),   # Minor
    },
    "Acquire": {
        "keywords_cover_pico_dimensions": (3, True),
        "primary_focus_match":            (3, True),
        "outcome_match":                  (3, True),
        "keywords_have_synonyms":         (2, True),
        "keywords_count_sufficient":      (2, True),
        "study_design_matches_route":     (2, True),
        "population_match":               (2, True),
        "top_selection_appropriate":      (1, True),
        "selection_count_appropriate":    (1, True),
        "key_sentences_present":          (1, True),
    },
    "Appraise": {
        "downgrade_factors_appropriate":  (3, True),
        "included_study_type_correct":    (3, True),
        "upgrade_factors_appropriate":    (2, True),
        "upgrade_blocked_appropriate":    (2, False),  # only YES/NO/NA
        "conflicts_identified":           (2, True),
        "numerical_data_extracted":       (1, True),
    },
    "Apply": {
        "effect_size_correctly_reported":    (3, True),
        "strength_matches_evidence":         (3, True),
        "population_applicability_addressed":(2, True),
        "uncertainty_source_explained":      (2, True),
        "citation_traceable":                (2, True),
        "recommendation_specific":           (1, True),
        "patient_preference_considered":     (1, True),
    },
}

PASS_THRESHOLD = 0.7
```

- [ ] **Step 2: 新增 `_check_gates` 函数**

在 `RUBRIC_WEIGHTS` 定义后添加：

```python
def _check_gates(stage: str, audit: dict) -> list:
    """
    Check gate items for a stage. Returns list of failed gate names.
    Any gate failure means overall fail regardless of rubric scores.
    """
    gate_results = audit.get("gate_results", {})
    failed = []

    if stage == "Ask":
        if gate_results.get("intent_not_distorted") == "NO":
            failed.append("intent_not_distorted")
        if gate_results.get("route_correct") == "NO":
            failed.append("route_correct")
        if gate_results.get("nonresearch_classification_correct") == "NO":
            failed.append("nonresearch_classification_correct")

    elif stage == "Acquire":
        if gate_results.get("search_terms_valid") == "NO":
            failed.append("search_terms_valid")

    elif stage == "Appraise":
        if gate_results.get("study_type_correct") == "NO":
            failed.append("study_type_correct")
        if gate_results.get("computed_grade_reasonable") == "NO":
            failed.append("computed_grade_reasonable")

    elif stage == "Apply":
        if gate_results.get("recommendation_grounded_in_evidence") == "NO":
            failed.append("recommendation_grounded_in_evidence")
        if gate_results.get("route_dimension_consistent") == "NO":
            failed.append("route_dimension_consistent")
        if gate_results.get("strength_not_grossly_inflated") == "NO":
            failed.append("strength_not_grossly_inflated")

    return failed
```

- [ ] **Step 3: 新增 `_score_rubrics` 函数**

```python
def _score_rubrics(stage: str, audit: dict) -> tuple:
    """
    Score rubric items using weighted rubric system.
    Returns (dimension_scores, raw_issues, total_score).
    NA items are excluded from denominator.
    YES = full weight, PARTIAL = weight * 0.5, NO = 0.
    """
    rubric_weights = RUBRIC_WEIGHTS.get(stage, {})
    rubric_results = audit.get("rubric_results", {})
    issues = []
    total_score = 0.0
    total_max = 0.0
    dimension_scores = {}

    for rubric_name, (weight, allows_partial) in rubric_weights.items():
        val = rubric_results.get(rubric_name, "NA")
        if val == "NA":
            dimension_scores[rubric_name] = None  # excluded
            continue

        if val == "YES":
            score = float(weight)
        elif val == "PARTIAL" and allows_partial:
            score = weight * 0.5
        else:  # NO or PARTIAL on non-partial rubric
            score = 0.0

        total_score += score
        total_max += weight
        dimension_scores[rubric_name] = score / weight  # normalize to 0-1 for display

        if val == "NO":
            severity = "critical" if weight == 3 else "major" if weight == 2 else "minor"
            issues.append({
                "severity": severity,
                "dimension": rubric_name,
                "description": f"{rubric_name} 未通过（NO）",
            })
        elif val == "PARTIAL":
            severity = "major" if weight >= 2 else "minor"
            issues.append({
                "severity": severity,
                "dimension": rubric_name,
                "description": f"{rubric_name} 部分通过（PARTIAL）",
            })

    overall = total_score / total_max if total_max > 0 else 1.0
    return dimension_scores, issues, overall
```

- [ ] **Step 4: 重写 `_score_ask`**

```python
def _score_ask(audit: dict) -> tuple:
    gate_failures = _check_gates("Ask", audit)
    if gate_failures:
        issues = [{"severity": "critical", "dimension": g,
                   "description": f"Gate 失败: {g}"} for g in gate_failures]
        return {"core_dimensions_present": 0.0}, issues, False, f"Gate失败: {', '.join(gate_failures)}"

    # direct_answer: gate passed means classification correct → terminate signal
    gate_results = audit.get("gate_results", {})
    if gate_results.get("nonresearch_classification_correct") == "YES":
        return {"nonresearch": 1.0}, [], False, "direct_answer路由正确，触发terminate"

    dim_scores, issues, overall = _score_rubrics("Ask", audit)
    pass_threshold = overall >= PASS_THRESHOLD
    failures = audit.get("failures", [])
    return dim_scores, issues, False, "; ".join(failures) if failures else f"综合评分: {overall:.2f}"
```

- [ ] **Step 5: 重写 `_score_acquire`**

```python
def _score_acquire(audit: dict) -> tuple:
    search_exhausted = bool(audit.get("search_exhausted", False))
    if search_exhausted:
        return {"search_exhausted": 1.0}, [], True, "检索穷尽，标记evidence_gap"

    gate_failures = _check_gates("Acquire", audit)
    if gate_failures:
        issues = [{"severity": "critical", "dimension": g,
                   "description": f"Gate 失败: {g}"} for g in gate_failures]
        return {"search_terms_valid": 0.0}, issues, False, f"Gate失败: {', '.join(gate_failures)}"

    dim_scores, issues, overall = _score_rubrics("Acquire", audit)
    failures = audit.get("failures", [])
    return dim_scores, issues, False, "; ".join(failures) if failures else f"综合评分: {overall:.2f}"
```

- [ ] **Step 6: 重写 `_score_appraise`**

```python
def _score_appraise(audit: dict) -> tuple:
    gate_failures = _check_gates("Appraise", audit)
    if gate_failures:
        issues = [{"severity": "critical", "dimension": g,
                   "description": f"Gate 失败: {g}"} for g in gate_failures]
        return {"study_type_correct": 0.0}, issues, False, f"Gate失败: {', '.join(gate_failures)}"

    dim_scores, issues, overall = _score_rubrics("Appraise", audit)
    failures = audit.get("failures", [])
    return dim_scores, issues, False, "; ".join(failures) if failures else f"综合评分: {overall:.2f}"
```

- [ ] **Step 7: 重写 `_score_apply`**

```python
def _score_apply(audit: dict) -> tuple:
    gate_failures = _check_gates("Apply", audit)
    if gate_failures:
        issues = [{"severity": "critical", "dimension": g,
                   "description": f"Gate 失败: {g}"} for g in gate_failures]
        return {"recommendation_grounded_in_evidence": 0.0}, issues, False, f"Gate失败: {', '.join(gate_failures)}"

    dim_scores, issues, overall = _score_rubrics("Apply", audit)
    failures = audit.get("failures", [])
    return dim_scores, issues, False, "; ".join(failures) if failures else f"综合评分: {overall:.2f}"
```

- [ ] **Step 8: 更新 `_calculate_overall_score` 以兼容新 rubric 体系**

新的 `_score_*` 函数直接返回 overall score，`_calculate_overall_score` 只在 Assess 阶段（未改动）使用。在 `evaluate_stage` 中，对 Ask/Acquire/Appraise/Apply 阶段，overall_score 从 `_score_rubrics` 直接取得，不再走 `STAGE_WEIGHTS` 加权。

在 `evaluate_stage` 中修改评分计算段：

```python
dimension_scores, raw_issues, search_exhausted, reasoning_hint = scorer(audit)

# For rubric-based stages, compute overall from rubric scores directly
if stage in ("Ask", "Acquire", "Appraise", "Apply"):
    gate_failures = _check_gates(stage, audit)
    if gate_failures:
        overall_score = 0.0
    else:
        _, _, overall_score = _score_rubrics(stage, audit)
        # Clamp NA-only edge case
        overall_score = max(0.0, min(1.0, overall_score))
else:
    overall_score = self._calculate_overall_score(stage, dimension_scores)
```

- [ ] **Step 9: 更新 `_prepare_context` 中 Acquire 和 Apply 的字段注入**

Acquire 阶段：将 `pico_query` 替换为 `ebm_query` + `route_type`：

```python
elif stage == "Acquire":
    ebm_query = state.get("ebm_query")
    pico = state.get("pico_query")
    if ebm_query:
        context["route_type"] = state.get("route_type", "ebm_pico")
        context["ebm_query"] = json.dumps({
            "patient": ebm_query.patient,
            "primary_focus": ebm_query.primary_focus,
            "comparator": getattr(ebm_query, "comparator", None),
            "outcome": ebm_query.outcome,
            "keywords": ebm_query.keywords,
        }, ensure_ascii=False, indent=2)
    elif pico:
        context["route_type"] = "ebm_pico"
        context["ebm_query"] = json.dumps({
            "patient": pico.patient,
            "primary_focus": pico.intervention,
            "comparator": pico.comparison,
            "outcome": pico.outcome,
            "keywords": pico.keywords,
        }, ensure_ascii=False, indent=2)
    else:
        context["route_type"] = "ebm_pico"
        context["ebm_query"] = "N/A"
```

Apply 阶段：将 `pico_query` 替换为 `route_type` + `query_description`：

```python
elif stage == "Apply":
    context["route_type"] = state.get("route_type", "ebm_pico")
    ebm_query = state.get("ebm_query")
    pico = state.get("pico_query")
    if ebm_query:
        context["query_description"] = json.dumps({
            "patient": ebm_query.patient,
            "primary_focus": ebm_query.primary_focus,
            "outcome": ebm_query.outcome,
        }, ensure_ascii=False, indent=2)
    elif pico:
        context["query_description"] = json.dumps({
            "patient": pico.patient,
            "intervention": pico.intervention,
            "comparison": pico.comparison,
            "outcome": pico.outcome,
        }, ensure_ascii=False, indent=2)
    else:
        context["query_description"] = "N/A"
    # appraisal_results 注入保持不变
    appraisal = state.get("appraisal_results")
    if appraisal:
        context["appraisal_results"] = json.dumps({
            "evidence_count": len(appraisal.evidence),
            "has_conflict": appraisal.has_conflict,
            "summary": appraisal.summary,
        }, ensure_ascii=False, indent=2)
    else:
        context["appraisal_results"] = "N/A"
```

Ask 阶段：新增 `route_type` 注入：

```python
if stage == "Ask":
    context["original_question"] = state["original_question"]
    context["route_type"] = state.get("route_type", "unknown")
```

- [ ] **Step 10: 运行 lint 检查**

```bash
python3 -m ruff check src/judge/judge_llm.py
```

Expected: no errors (or only pre-existing warnings unrelated to this change).

---

## Task 6: 新增 Appraise Layer 1 Python 校验

**Files:**
- Modify: `src/judge/judge_llm.py`

- [ ] **Step 1: 新增 `_appraise_layer1_check` 函数**

在 `judge_llm.py` 中添加：

```python
def _appraise_layer1_check(output: dict) -> dict:
    """
    Layer 1 Python hardcoded validation for Appraise stage.
    Returns dict with keys: passed (bool), failures (list[str]).
    If passed=True, skip LLM Judge entirely.
    Raises SystemError if grade_output_in_legal_range fails.
    """
    LEGAL_GRADES = {"High", "Moderate", "Low", "Very Low"}
    failures = []

    appraisal = output.get("appraisal_results")
    if appraisal is None:
        failures.append("appraisal_results missing")
        return {"passed": False, "failures": failures}

    from dataclasses import asdict, is_dataclass
    appraisal_d = asdict(appraisal) if is_dataclass(appraisal) else appraisal
    evidence_list = appraisal_d.get("evidence", [])

    LEGAL_STUDY_TYPES = {
        "RCT", "COHORT", "CASE_CONTROL", "CASE_REPORT",
        "SYSTEMATIC_REVIEW", "META_ANALYSIS", "NMA",
        "GUIDELINE", "CROSS_SECTIONAL", "NARRATIVE_REVIEW", "EXPERT_OPINION",
    }

    for ev in evidence_list:
        study_type = ev.get("study_type")
        if not study_type or study_type not in LEGAL_STUDY_TYPES:
            failures.append(f"study_type missing or illegal: pmid={ev.get('pmid','?')} study_type={study_type}")

        rob = ev.get("risk_of_bias")
        if rob is None:
            failures.append(f"risk_of_bias missing: pmid={ev.get('pmid','?')}")

        grade = ev.get("grade_level")
        if grade and grade not in LEGAL_GRADES:
            raise SystemError(
                f"grade_output_in_legal_range FAILED: pmid={ev.get('pmid','?')} grade={grade}. "
                "Illegal grade value — workflow terminated."
            )

    return {"passed": len(failures) == 0, "failures": failures}
```

- [ ] **Step 2: 在 `evaluate_stage` 中为 Appraise 阶段插入 Layer 1 前置检查**

在 `evaluate_stage` 方法中，在 `prompt_template = self._load_prompt(stage)` 之前插入：

```python
# Appraise Layer 1: Python hardcoded check before calling LLM Judge
if stage == "Appraise":
    layer1 = _appraise_layer1_check(output)
    if layer1["passed"]:
        # All structural checks pass — skip LLM Judge, return pass directly
        from src.state.schema import Issue as IssueSchema
        evaluation = Evaluation(
            overall_score=1.0,
            dimension_scores={"layer1_structural": 1.0},
            pass_threshold=True,
            issues=[],
            summary="Layer 1 结构校验通过，跳过 LLM Judge",
            search_exhausted=False,
        )
        return ObserveSchema(stage=stage, output=output, evaluation=evaluation)
    else:
        print(f"[Appraise Layer1] 校验失败，触发 LLM Judge: {layer1['failures']}")
```

- [ ] **Step 3: 运行 lint 检查**

```bash
python3 -m ruff check src/judge/judge_llm.py
```

---

## Task 7: 编写单元测试

**Files:**
- Create: `tests/test_judge_rubrics.py`

- [ ] **Step 1: 创建测试文件**

```python
"""Unit tests for Gate + Weighted Rubrics judge scoring."""
import pytest
from src.judge.judge_llm import (
    _check_gates,
    _score_rubrics,
    _score_ask,
    _score_acquire,
    _score_appraise,
    _score_apply,
    _appraise_layer1_check,
    RUBRIC_WEIGHTS,
    PASS_THRESHOLD,
)


# ── _check_gates ─────────────────────────────────────────────────────────────

def test_check_gates_ask_all_pass():
    audit = {"gate_results": {
        "intent_not_distorted": "YES",
        "route_correct": "YES",
        "nonresearch_classification_correct": "NA",
    }}
    assert _check_gates("Ask", audit) == []


def test_check_gates_ask_intent_fail():
    audit = {"gate_results": {"intent_not_distorted": "NO", "route_correct": "YES"}}
    assert "intent_not_distorted" in _check_gates("Ask", audit)


def test_check_gates_ask_route_fail():
    audit = {"gate_results": {"intent_not_distorted": "YES", "route_correct": "NO"}}
    assert "route_correct" in _check_gates("Ask", audit)


def test_check_gates_acquire_pass():
    audit = {"gate_results": {"search_terms_valid": "YES"}}
    assert _check_gates("Acquire", audit) == []


def test_check_gates_acquire_fail():
    audit = {"gate_results": {"search_terms_valid": "NO"}}
    assert "search_terms_valid" in _check_gates("Acquire", audit)


def test_check_gates_appraise_study_type_fail():
    audit = {"gate_results": {"study_type_correct": "NO", "computed_grade_reasonable": "YES"}}
    assert "study_type_correct" in _check_gates("Appraise", audit)


def test_check_gates_apply_all_fail():
    audit = {"gate_results": {
        "recommendation_grounded_in_evidence": "NO",
        "route_dimension_consistent": "NO",
        "strength_not_grossly_inflated": "YES",
    }}
    failures = _check_gates("Apply", audit)
    assert "recommendation_grounded_in_evidence" in failures
    assert "route_dimension_consistent" in failures
    assert "strength_not_grossly_inflated" not in failures


# ── _score_rubrics ────────────────────────────────────────────────────────────

def test_score_rubrics_ask_all_yes():
    audit = {
        "gate_results": {"intent_not_distorted": "YES", "route_correct": "YES"},
        "rubric_results": {
            "core_dimensions_present": "YES",
            "secondary_dimensions_present": "YES",
            "statement_unambiguous": "YES",
        }
    }
    dim_scores, issues, overall = _score_rubrics("Ask", audit)
    assert overall == pytest.approx(1.0)
    assert issues == []


def test_score_rubrics_ask_partial_critical():
    # core_dimensions_present=PARTIAL → 1.5/3, others YES
    audit = {
        "gate_results": {"intent_not_distorted": "YES", "route_correct": "YES"},
        "rubric_results": {
            "core_dimensions_present": "PARTIAL",
            "secondary_dimensions_present": "YES",
            "statement_unambiguous": "YES",
        }
    }
    dim_scores, issues, overall = _score_rubrics("Ask", audit)
    # total_score = 1.5 + 2 + 1 = 4.5, total_max = 3+2+1 = 6
    assert overall == pytest.approx(4.5 / 6)
    assert any(i["severity"] == "major" for i in issues)


def test_score_rubrics_ask_no_critical():
    audit = {
        "gate_results": {"intent_not_distorted": "YES", "route_correct": "YES"},
        "rubric_results": {
            "core_dimensions_present": "NO",
            "secondary_dimensions_present": "YES",
            "statement_unambiguous": "YES",
        }
    }
    dim_scores, issues, overall = _score_rubrics("Ask", audit)
    # total_score = 0 + 2 + 1 = 3, total_max = 6
    assert overall == pytest.approx(3.0 / 6)
    assert any(i["severity"] == "critical" for i in issues)


def test_score_rubrics_na_excluded_from_denominator():
    # secondary_dimensions_present=NA → excluded
    audit = {
        "gate_results": {"intent_not_distorted": "YES", "route_correct": "YES"},
        "rubric_results": {
            "core_dimensions_present": "YES",
            "secondary_dimensions_present": "NA",
            "statement_unambiguous": "YES",
        }
    }
    dim_scores, issues, overall = _score_rubrics("Ask", audit)
    # total_score = 3 + 1 = 4, total_max = 3+1 = 4
    assert overall == pytest.approx(1.0)


def test_score_rubrics_pass_threshold():
    # Acquire: all YES → overall=1.0 → pass
    rubric_results = {k: "YES" for k in RUBRIC_WEIGHTS["Acquire"]}
    audit = {
        "gate_results": {"search_terms_valid": "YES"},
        "rubric_results": rubric_results,
    }
    _, _, overall = _score_rubrics("Acquire", audit)
    assert overall >= PASS_THRESHOLD


# ── _score_ask gate path ──────────────────────────────────────────────────────

def test_score_ask_gate_fail_returns_zero():
    audit = {"gate_results": {"intent_not_distorted": "NO", "route_correct": "YES"}}
    dim_scores, issues, search_exhausted, hint = _score_ask(audit)
    assert any(i["severity"] == "critical" for i in issues)
    assert "intent_not_distorted" in hint


def test_score_ask_direct_answer_correct():
    audit = {"gate_results": {
        "intent_not_distorted": "YES",
        "route_correct": "NA",
        "nonresearch_classification_correct": "YES",
    }, "rubric_results": {}}
    dim_scores, issues, search_exhausted, hint = _score_ask(audit)
    assert "terminate" in hint or "direct_answer" in hint


# ── _score_acquire search_exhausted ──────────────────────────────────────────

def test_score_acquire_search_exhausted():
    audit = {"search_exhausted": True, "gate_results": {}, "rubric_results": {}}
    dim_scores, issues, search_exhausted, hint = _score_acquire(audit)
    assert search_exhausted is True


# ── _appraise_layer1_check ────────────────────────────────────────────────────

def test_appraise_layer1_pass():
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class FakeEvidence:
        pmid: str
        study_type: str
        risk_of_bias: str
        grade_level: Optional[str] = "Moderate"

    @dataclass
    class FakeAppraisal:
        evidence: list
        has_conflict: bool = False
        conflict_description: Optional[str] = None
        summary: str = ""

    output = {"appraisal_results": FakeAppraisal(evidence=[
        FakeEvidence(pmid="123", study_type="RCT", risk_of_bias="NOT_SERIOUS"),
    ])}
    result = _appraise_layer1_check(output)
    assert result["passed"] is True


def test_appraise_layer1_missing_study_type():
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class FakeEvidence:
        pmid: str
        study_type: Optional[str]
        risk_of_bias: str
        grade_level: Optional[str] = None

    @dataclass
    class FakeAppraisal:
        evidence: list
        has_conflict: bool = False
        conflict_description: Optional[str] = None
        summary: str = ""

    output = {"appraisal_results": FakeAppraisal(evidence=[
        FakeEvidence(pmid="456", study_type=None, risk_of_bias="NOT_SERIOUS"),
    ])}
    result = _appraise_layer1_check(output)
    assert result["passed"] is False
    assert any("study_type" in f for f in result["failures"])


def test_appraise_layer1_illegal_grade_raises():
    from dataclasses import dataclass
    from typing import Optional

    @dataclass
    class FakeEvidence:
        pmid: str
        study_type: str
        risk_of_bias: str
        grade_level: Optional[str]

    @dataclass
    class FakeAppraisal:
        evidence: list
        has_conflict: bool = False
        conflict_description: Optional[str] = None
        summary: str = ""

    output = {"appraisal_results": FakeAppraisal(evidence=[
        FakeEvidence(pmid="789", study_type="RCT", risk_of_bias="NOT_SERIOUS", grade_level="ILLEGAL"),
    ])}
    with pytest.raises(SystemError, match="grade_output_in_legal_range"):
        _appraise_layer1_check(output)
```

- [ ] **Step 2: 运行测试**

```bash
python3 -m pytest tests/test_judge_rubrics.py -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 3: 如有失败，修复后重跑**

```bash
python3 -m pytest tests/test_judge_rubrics.py -v --tb=short
```

---

## Task 8: 端到端冒烟验证

**Files:**
- No file changes — validation only

- [ ] **Step 1: 验证所有 prompt 文件格式占位符**

```bash
python3 -c "
from pathlib import Path
stages = {
    'ask': ['{original_question}', '{route_type}', '{stage_output}'],
    'acquire': ['{route_type}', '{ebm_query}', '{stage_output}'],
    'appraise': ['{evidence_list}', '{stage_output}'],
    'apply': ['{route_type}', '{query_description}', '{appraisal_results}', '{stage_output}'],
}
for stage, placeholders in stages.items():
    txt = Path(f'src/config/prompts/judge/{stage}_judge.txt').read_text()
    for p in placeholders:
        assert p in txt, f'Missing {p} in {stage}_judge.txt'
    assert 'gate_results' in txt
    assert 'rubric_results' in txt
    print(f'{stage}_judge.txt: OK')
print('All prompt files validated.')
"
```

- [ ] **Step 2: 验证 judge_llm.py 可导入**

```bash
python3 -c "
from src.judge.judge_llm import (
    _check_gates, _score_rubrics, _score_ask, _score_acquire,
    _score_appraise, _score_apply, _appraise_layer1_check,
    RUBRIC_WEIGHTS, PASS_THRESHOLD
)
print('judge_llm.py imports OK')
print('Stages with rubrics:', list(RUBRIC_WEIGHTS.keys()))
"
```

- [ ] **Step 3: 运行完整测试套件**

```bash
python3 -m pytest tests/ --tb=short -q || [ $? -eq 5 ]
```

Expected: all tests pass (exit 0 or 5 if no other tests collected).

- [ ] **Step 4: 运行 lint**

```bash
python3 -m ruff check src/judge/judge_llm.py src/config/prompts/
```

Expected: no new errors.

---

## 补充说明：`STAGE_SCORERS` 更新

Task 5 Step 7 完成后，需同步更新 `judge_llm.py` 中的 `STAGE_SCORERS` dispatch table，将新的 `_score_*` 函数签名对齐。

现有 `STAGE_SCORERS`（`judge_llm.py:826`）：

```python
STAGE_SCORERS = {
    "Ask": _score_ask,
    "Acquire": _score_acquire,
    "Appraise": _score_appraise,
    "Apply": _score_apply,
    "Assess": _score_assess,
}
```

新的 `_score_ask/_score_acquire/_score_appraise/_score_apply` 签名与原来相同（均接受 `audit: dict`，返回 `(dim_scores, issues, search_exhausted, reasoning_hint)`），因此 `STAGE_SCORERS` 本身**无需修改**，dispatch 逻辑不变。

唯一需要注意的是 Task 5 Step 8 中 `evaluate_stage` 里 overall_score 的计算方式：对 Ask/Acquire/Appraise/Apply 阶段，在调用 `scorer(audit)` 之后，额外调用 `_score_rubrics(stage, audit)` 取得 overall_score，而不再走 `_calculate_overall_score(stage, dimension_scores)`。

---
