# 4/20-4/22 全量重设计实现计划

> **For agentic workers:** Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Ask 路由重设计、Acquire PMC+RAG、Appraise GRADE 修正、Apply 对齐、Judge Gate+Rubrics 架构重写。

**原则：** 每个 Task 先写失败测试（如适用），再改代码，再验证，不需要commit。

---

## 文件改动清单

| 文件 | 操作 |
|---|---|
| src/state/schema.py | 新增 EBMQuery；WorkflowState 路由字段；Evidence.has_full_text |
| src/config/prompts/ask/ | 新建目录 + 8 个 prompt 文件 |
| src/agents/ask_agent.py | 重写：路由→分支→统一输出 |
| src/coordinator/coordinator.py | direct_answer 提前终止 |
| src/tools/pubmed_api.py | 新增 fetch_pmc_full_text |
| src/agents/acquire_agent.py | EBMQuery 适配；PMC 全文；BM25+Embedding RAG |
| src/agents/appraise_agent.py | _compute_grade 重写；SR 动态初始分；升级阻断 |
| src/config/prompts/appraise_agent.txt | 新增 included_study_type、confounding_bias_mitigates |
| src/agents/apply_agent.py | route_type 注入；结构化 GRADE；inconsistency 强制规则 |
| src/config/prompts/apply_agent.txt | 路由维度检查；结构化 GRADE 输入变量 |
| src/config/prompts/judge/ask_judge.txt | 重写：Gate+Rubrics |
| src/config/prompts/judge/acquire_judge.txt | 重写：Gate+Rubrics |
| src/config/prompts/judge/appraise_judge.txt | 重写：Gate+Rubrics |
| src/config/prompts/judge/apply_judge.txt | 重写：Gate+Rubrics |
| src/config/prompts/judge/assess_judge.txt | 新增路由字段输入；route_confidence_noted |
| src/judge/judge_llm.py | Gate 检查；Rubric 评分；RUBRIC_WEIGHTS |
| tests/test_judge_rubrics.py | 新建：Gate+Rubrics 单元测试 |
| tests/test_integration_routing.py | 新建：路由集成测试 |

---

## Task 1: schema.py — EBMQuery + routing fields + Evidence.has_full_text

**Files:** `src/state/schema.py`

- [ ] 在 PICOQuery 之后插入 EBMQuery dataclass（字段：query_type, patient, primary_focus, outcome, keywords, comparator=None, reference_standard=None, time_horizon=None）
- [ ] Evidence 新增 `has_full_text: bool = False`
- [ ] WorkflowState 新增：route_type, route_confidence, direct_answer_output, ebm_query, sub_pico_queries, sub_question_index, sub_question_total
- [ ] 验证：`python3 -c "from src.state.schema import EBMQuery, WorkflowState, Evidence; print('OK')"`
- [ ] `git commit -m "feat(schema): EBMQuery, routing fields, Evidence.has_full_text"`

---

## Task 2: Ask prompt files — create src/config/prompts/ask/ with 8 files

**Files:** `src/config/prompts/ask/`（新建目录）

| 文件 | 输入变量 | 输出 JSON 关键字段 |
|---|---|---|
| router.txt | {question} | route_type, reasoning |
| direct_answer.txt | {question} | answer, source, disclaimer |
| diag_step1.txt | {question} | clinical_features[], differential_diagnoses[]（最多3个） |
| diag_step2.txt | {clinical_features}, {single_diagnosis} | EBMQuery 字段 |
| ebm_pico.txt | {question}, {backtrack_context} | EBMQuery（query_type=pico） |
| ebm_pird.txt | {question}, {backtrack_context} | EBMQuery（query_type=pird） |
| ebm_peo.txt | {question}, {backtrack_context} | EBMQuery（query_type=peo） |
| ebm_prognosis.txt | {question}, {backtrack_context} | EBMQuery（query_type=prognosis） |

router.txt 的 direct_answer 触发条件须同时满足：(1) 要求立即操作性指导；(2) 延迟会危及生命；(3) 答案来自公认标准流程（BLS/ACLS）。

- [ ] 创建目录并写入 8 个文件，每个文件含 Role + 输入变量 + 输出 JSON 格式，不含示例数据
- [ ] 验证所有文件存在且非空
- [ ] `git commit -m "feat(ask-prompts): 8 routing prompt files"`

---

## Task 3: ask_agent.py — rewrite with routing logic

**Files:** `src/agents/ask_agent.py`

```
__init__: 从 src/config/prompts/ask/ 加载 8 个 prompt 到 self._prompts dict
execute(state):
  route = _call("router", question)
  if route == "direct_answer": return {direct_answer_output, _ask_direct_answer: True}
  if route == "diagnostic_reasoning":
      step1 = _call("diag_step1"); sub_queries = [_call("diag_step2", ...) for diag in differentials]
      return {sub_pico_queries, ebm_query: sub_queries[0]}
  ebm_dict = _call(route_type, question, backtrack_context)
  return {ebm_query: EBMQuery(**ebm_dict), pico_query: PICOQuery(...), route_type}
```

- [ ] 重写 ask_agent.py
- [ ] 验证：`python3 -c "from src.agents.ask_agent import AskAgent; print('OK')"`
- [ ] `git commit -m "feat(ask-agent): routing with direct_answer/diag/ebm_* branches"`

---

## Task 4: coordinator.py — direct_answer early termination

**Files:** `src/coordinator/coordinator.py`

```python
if agent_name == "Ask" and result.get("_ask_direct_answer"):
    state.update(result); state["should_terminate"] = True; return state
```

- [ ] 在 execute_agent 的 result = agent.execute(state) 之后插入上述代码
- [ ] 验证：`python3 -c "from src.coordinator.coordinator import Coordinator; print('OK')"`
- [ ] `git commit -m "feat(coordinator): early termination for direct_answer route"`

---

## Task 5: pubmed_api.py — add fetch_pmc_full_text via PMC OA BioC JSON API

**Files:** `src/tools/pubmed_api.py`

```
URL: https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid}/unicode
timeout=10，任何异常返回 None
解析 documents[0].passages[*].text，拼接返回
```

- [ ] 在文件末尾追加 fetch_pmc_full_text 函数
- [ ] 验证：`python3 -c "from src.tools.pubmed_api import fetch_pmc_full_text; print('OK')"`
- [ ] `git commit -m "feat(pubmed-api): add fetch_pmc_full_text via PMC OA BioC JSON"`

---

## Task 6: acquire_agent.py — EBMQuery support + PMC full text + BM25/Embedding RAG

**Files:** `src/agents/acquire_agent.py`

- [ ] 新增 _FILTER_BY_ROUTE_TYPE（ebm_pico→HSSS, ebm_pird→DTA, ebm_peo/prognosis→OBSERVATIONAL）
- [ ] 新增线程安全 _get_embedding_model()（懒加载 all-MiniLM-L6-v2）
- [ ] 新增 _fetch_full_texts(candidates)：ThreadPoolExecutor(max_workers=8)，写入 evidence.full_text 和 evidence.has_full_text
- [ ] 新增 _rag_extract(evidence, query_terms)：BM25 top-8 → Embedding rerank top-3，返回 (key_sentences, score)
- [ ] 更新 execute：读 ebm_query（优先）或 pico_query（兼容）；fetch full texts；RAG extract；full_text 文章排前
- [ ] 验证：`python3 -c "from src.agents.acquire_agent import AcquireAgent; print('OK')"`
- [ ] `git commit -m "feat(acquire): EBMQuery routing, PMC full-text, BM25+Embedding RAG"`

---

## Task 7: appraise_agent.py — fix _compute_grade: SR dynamic initial score, upgrade blocked by SERIOUS bias, cap observational at Moderate

**Files:** `src/agents/appraise_agent.py`, `tests/test_appraise_grade.py`

测试用例（5个）：SR+RCT→High；SR+OBSERVATIONAL→Low；COHORT+SERIOUS+全升级→Very Low（阻断）；COHORT+NOT_SERIOUS+全升级→Moderate（cap）；CROSS_SECTIONAL+全升级→Low（不在升级类型中）

```
_SR_INITIAL_POINTS = {"RCT": 4, "OBSERVATIONAL": 2, "MIXED": 3, "UNKNOWN": 3}
_SR_TYPES = {"SYSTEMATIC_REVIEW", "META_ANALYSIS", "NMA"}
_UPGRADE_STUDY_TYPES = {"COHORT", "CASE_CONTROL"}
```

- [ ] 先写测试，确认 FAIL
- [ ] 重写 _compute_grade：SR 查 _SR_INITIAL_POINTS；升级仅对 _UPGRADE_STUDY_TYPES 且 NOT_SERIOUS 时生效；升级后 cap at min(points, 3)
- [ ] 确认测试 PASS
- [ ] `git commit -m "feat(appraise): dynamic SR initial score, upgrade blocked by bias, cap at Moderate"`

---

## Task 8: appraise_agent.txt — add included_study_type, confounding_bias_mitigates fields

**Files:** `src/config/prompts/appraise_agent.txt`

- [ ] 在"研究类型"节末尾新增 included_study_type 说明（仅 SR/MA/NMA 填写；取值 RCT/OBSERVATIONAL/MIXED/UNKNOWN）
- [ ] 在"升级因素"节新增 confounding_bias_mitigates（YES/NO/NA）和 upgrade_blocked_by_bias（true/false）；注明 SERIOUS 偏倚时升级被阻断
- [ ] 在 JSON 输出模板中新增这两个字段
- [ ] 验证：`python3 -c "t=open('src/config/prompts/appraise_agent.txt').read(); assert 'included_study_type' in t; print('OK')"`
- [ ] `git commit -m "feat(prompt/appraise): included_study_type, confounding_bias_mitigates"`

---

## Task 9: apply_agent.py — route_type injection, structured GRADE, inconsistency enforcement

**Files:** `src/agents/apply_agent.py`, `tests/test_apply_agent.py`

测试用例（4个）：_format_ebm_query pico 含 "Intervention:"；pird 含 "Index Test:"；_summarize_downgrade_factors 全 NOT_SERIOUS→固定字符串；有 SERIOUS→含因素名

- [ ] 新增模块级函数：_format_ebm_query, _format_pico_query, _summarize_downgrade_factors
- [ ] 更新 execute：注入 route_type/query_description/key_downgrade_factors/has_serious_inconsistency
- [ ] 强制规则：overall_grade in (Very Low, Low) + LLM 给 Strong → 降为 Weak；has_serious_inconsistency + Strong → 降为 Weak
- [ ] route_confidence == "low" 时在 caveats 追加警告
- [ ] 先写测试确认 FAIL，修改代码确认 PASS
- [ ] `git commit -m "feat(apply): route_type injection, structured GRADE, inconsistency enforcement"`

---

## Task 10: apply_agent.txt — add route_type dimension check, structured GRADE input variables

**Files:** `src/config/prompts/apply_agent.txt`

- [ ] 新增输入变量：{route_type}, {query_description}, {overall_grade}, {downgrade_factors}, {consistency_flag}
- [ ] 在 prompt 开头新增 Step 0：根据 {route_type} 说明当前问题框架（治疗/诊断/病因/预后）
- [ ] 在推荐强度规则中明确写入：SERIOUS inconsistency → 不得给 Strong
- [ ] 验证：`python3 -c "t=open('src/config/prompts/apply_agent.txt').read(); assert '{route_type}' in t; print('OK')"`
- [ ] `git commit -m "feat(prompt/apply): route_type dimension check, structured GRADE input"`

---

## Task 11: ask_judge.txt — rewrite Gate+Rubrics

**Files:** `src/config/prompts/judge/ask_judge.txt`

Gate（任一触发 → 直接 FAIL）：intent_distorted == YES；keywords_english_medical == NO

| 维度 | 权重 |
|---|---|
| pico_completeness（P/I/O 均 YES） | 0.30 |
| keyword_quality（MeSH + 同义词） | 0.25 |
| route_correctness（route_type 与问题匹配） | 0.25 |
| clarity（表述清晰度） | 0.20 |

输出 JSON 新增：gate_passed: bool, rubric_scores: {...}, weighted_score: float

- [ ] 重写文件
- [ ] `git commit -m "feat(judge/ask): Gate+Rubrics architecture"`

---

## Task 12: acquire_judge.txt — rewrite Gate+Rubrics

**Files:** `src/config/prompts/judge/acquire_judge.txt`

Gate：search_terms_valid == NO

| 维度 | 权重 |
|---|---|
| evidence_quality（best_study_type） | 0.35 |
| pico_match | 0.35 |
| selection_quality（listwise 合理性） | 0.30 |

- [ ] 重写文件
- [ ] `git commit -m "feat(judge/acquire): Gate+Rubrics architecture"`

---

## Task 13: appraise_judge.txt — rewrite Gate+Rubrics

**Files:** `src/config/prompts/judge/appraise_judge.txt`

Gate：study_type_correct == NO

| 维度 | 权重 |
|---|---|
| downgrade_factors（分类合理性） | 0.35 |
| computed_grade（合理性） | 0.35 |
| upgrade_factors（含 confounding_bias_mitigates 审计） | 0.30 |

- [ ] 重写文件
- [ ] `git commit -m "feat(judge/appraise): Gate+Rubrics architecture"`

---

## Task 14: apply_judge.txt — rewrite Gate+Rubrics

**Files:** `src/config/prompts/judge/apply_judge.txt`

Gate：recommendation_based_on_evidence == NO

| 维度 | 权重 |
|---|---|
| grounding（推荐-证据匹配） | 0.35 |
| strength_match（推荐强度 vs GRADE） | 0.35 |
| route_dimension（route_dimension_correct） | 0.15 |
| actionability（临床可操作性） | 0.15 |

新增输入变量 {route_type}，用于判断推荐是否符合当前问题框架。

- [ ] 重写文件
- [ ] `git commit -m "feat(judge/apply): Gate+Rubrics, route_dimension audit"`

---

## Task 15: assess_judge.txt — add route_type/route_confidence/ebm_query inputs, route_confidence_noted output field

**Files:** `src/config/prompts/judge/assess_judge.txt`

- [ ] 输入新增：{route_type}, {route_confidence}, {ebm_query_description}
- [ ] ask_to_acquire_link 审计新增：检索词是否覆盖 {route_type} 对应的关键维度
- [ ] 新增审计项 route_confidence_noted（若 route_confidence=low，输出是否包含不确定性说明）
- [ ] 输出 JSON 新增 `route_confidence_noted: "YES | NO | NA"`
- [ ] `git commit -m "feat(judge/assess): route_type/ebm_query inputs, route_confidence_noted"`

---

## Task 16: judge_llm.py — add _check_gates, _score_rubrics, RUBRIC_WEIGHTS; update _score_ask/acquire/appraise/apply

**Files:** `src/judge/judge_llm.py`, `tests/test_judge_rubrics.py`

```python
RUBRIC_WEIGHTS = {
    "ask":      {"pico_completeness": 0.30, "keyword_quality": 0.25, "route_correctness": 0.25, "clarity": 0.20},
    "acquire":  {"evidence_quality": 0.35, "pico_match": 0.35, "selection_quality": 0.30},
    "appraise": {"downgrade_factors": 0.35, "computed_grade": 0.35, "upgrade_factors": 0.30},
    "apply":    {"grounding": 0.35, "strength_match": 0.35, "route_dimension": 0.15, "actionability": 0.15},
}
```

测试用例（5个）：Gate 触发时 _score_ask 返回 0.0；Gate 通过时按权重正确计算；_check_gates("ask", {"intent_distorted": "YES"}) 返回 False；_check_gates("apply", {"recommendation_based_on_evidence": "NO"}) 返回 False；全 YES rubric_scores 返回 1.0

- [ ] 先写测试，确认 FAIL
- [ ] 新增 _check_gates, _score_rubrics；更新 _score_ask/acquire/appraise/apply；更新 _prepare_context 传入路由字段
- [ ] 确认测试 PASS
- [ ] `git commit -m "feat(judge-llm): Gate+Rubrics scoring, RUBRIC_WEIGHTS"`

---

## Task 17: Integration tests — tests/test_integration_routing.py (mock LLM, test direct_answer/ebm_pico/ebm_pird routing)

**Files:** `tests/test_integration_routing.py`（新建）

- [ ] direct_answer 路由 → should_terminate=True，direct_answer_output 非空
- [ ] ebm_pico 路由 → ebm_query.query_type == "pico"，pico_query 兼容字段存在
- [ ] ebm_pird 路由 → ebm_query.query_type == "pird"
- [ ] 旧 pico_query 兼容 → Acquire 正常运行
- [ ] `git commit -m "test(integration): routing flow with mock LLM"`

---

## Task 18: Full regression — run all tests, fix failures

- [ ] `python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30`
- [ ] 确认无 FAILED
- [ ] 如有失败，逐一修复后重新运行
- [ ] `git commit -m "chore: all tests passing after 4/20-4/22 redesign"`
