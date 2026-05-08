# Ask Judge 重设计规范

**日期**: 2026-04-20
**范围**: `ask_judge.txt`（重写）+ `judge_llm.py`（`_score_ask` 重写 + `_precheck_ask` 新增）+ `coordinator.py`（小改）+ `apply_agent.py`（小改）
**不在本次范围内**: 其他阶段 Judge 的 route_type 适配

---

## 背景与问题

原 Ask Judge 存在以下问题：

1. **`route_type` 完全未被审计**：Ask 新架构的核心输出之一，分类错误无法捕获
2. **非 PICO 路由用错误框架审计**：PIRD/PEO/Prognosis 被套用 PICO 四要素，产生误判
3. **`keywords_english_medical`/`has_synonyms_or_mesh` 由 LLM 判断**：可规则化的格式检查浪费 LLM 调用
4. **`routing_decision` 原设计由 LLM 输出**：违背"LLM 分类→Python 计算"架构原则
5. **`_score_diagnostic_reasoning` 无权重定义**
6. **Pass/Fail 阈值与 `dimension_scores` 转化关系未明确**
7. **`reasoning` 字段信息密度不足**，无法支撑决策模型
8. **`format_match` 与路由验证职责重叠**（冗余，删除）
9. **`route_appropriateness` PARTIAL 处理逻辑缺失**（简化为 YES/NO）

---

## 架构决策

| 决策 | 选择 | 理由 |
|---|---|---|
| Prompt 共用 vs 独立 | 单 prompt + Python 动态注入对应路由段落 | LLM 不处理条件判断，prompt 精简 |
| 两阶段 vs 一阶段 Judge | 合并为一次调用 | 路由和结构化是同一 Ask 调用的输出，分两次引入的状态传递复杂度不值得 |
| `routing_decision` | Python 推导，不由 LLM 输出 | 与整个 Judge 架构（LLM 分类→Python 计算）保持一致 |
| `route_appropriateness` | 简化为 YES/NO | PARTIAL 无明确后续动作；歧义由 `ambiguity_flag` 单独承担 |
| `diagnostic_reasoning` Judge | 所有子PICO完成后一次批量调用 | 避免 N+1 次调用；与其他路由调用次数对齐 |
| `keywords_english_medical`/`has_synonyms_or_mesh` | 移至 Python 预检 | 正则/数组操作，无需 LLM 语义理解 |
| `format_match` | 删除 | 与路由验证职责重叠 |

---

## Python 预检（调用 Judge LLM 前）

```python
def _precheck_ask(pico_dict: dict) -> dict:
    """在调用 Judge LLM 前，用 Python 规则完成可确定性检查。"""
    import re
    chinese = re.compile(r'[\u4e00-\u9fff]')
    keywords = pico_dict.get("keywords", [])

    keywords_english = not any(chinese.search(kw) for kw in keywords)
    has_synonyms = len(set(keywords)) >= 2
    keyword_count_ok = len(keywords) > 1  # False → boolean_logic_valid 直接 NO

    return {
        "keywords_english_medical": "YES" if keywords_english else "NO",
        "has_synonyms_or_mesh":     "YES" if has_synonyms else "NO",
        "keyword_count_ok":         keyword_count_ok,
    }
```

预检结果直接写入 `_score_ask`，不传给 LLM Judge。

---

## Judge Prompt 结构

### 固定段（所有路由共用）

```
# Role
你是一个严格的EBM审计员，对 Ask Agent 的输出进行客观分类判断，只输出结构化 JSON，不要打分。

# Input
原始问题：{original_question}
路由类型：{route_type}
Ask Agent 输出：{stage_output}

# 固定审计项

## 路由审计
route_appropriateness: YES | NO
- YES：route_type 与问题类型匹配
- NO：明显不符（如诊断准确性问题路由为 ebm_pico）

ambiguity_flag: YES | NO
- YES：问题本身存在路由歧义（如同时涉及诊断和治疗），当前路由是合理选择之一
- NO：路由方向明确

## 安全审计（Critical，一票否决）
intent_distorted: YES | NO
- YES：结构化结果扭曲了原问题核心意图（方向性错误：问儿童→写成人；问治疗→写诊断）
- NO：意图基本一致
注意：intent_distorted 关注方向性错误，不关注描述清晰度；
      pico_statement_unambiguous 关注描述清晰度（两者独立，可同时触发）

## 关键词语义审计（仅语义合理性；英文/数量已由 Python 预检）
boolean_logic_valid: YES | NO
- YES：关键词覆盖了问题的核心维度（至少覆盖 P + I/Exposure/IndexTest 两个维度），无明显冗余
- NO：关键词全部指向同一概念，或包含大量明显无关词，或数量严重不足
```

### 动态注入段（Python 按 route_type 选择注入）

**ebm_pico：**
```
## 结构审计 (PICO)
P: YES|PARTIAL|NO  患者/人群是否明确（年龄、疾病状态等）
I: YES|PARTIAL|NO  干预措施是否明确
C: YES|NA|NO       对照组（原问题不涉及对照→NA）
O: YES|PARTIAL|NO  临床结局是否明确
pico_statement_unambiguous: YES|PARTIAL|NO
  YES=表述明确无歧义；PARTIAL=轻微歧义不影响检索方向；NO=严重歧义难以检索
```

**ebm_pird：**
```
## 结构审计 (PIRD)
P:  YES|PARTIAL|NO  患者人群是否明确
I:  YES|PARTIAL|NO  Index Test（待评估的诊断测试）是否明确
R:  YES|PARTIAL|NA  Reference Standard（金标准）是否明确（原问题未提及→NA）
D:  YES|PARTIAL|NO  Target Condition（诊断结局）是否明确
pico_statement_unambiguous: YES|PARTIAL|NO
```

**ebm_peo：**
```
## 结构审计 (PEO)
P: YES|PARTIAL|NO  患者人群是否明确
E: YES|PARTIAL|NO  Exposure（暴露因素）是否明确
O: YES|PARTIAL|NO  Outcome（结局）是否明确
（PEO 无 Comparator，不审计 C 字段）
pico_statement_unambiguous: YES|PARTIAL|NO
```

**ebm_prognosis：**
```
## 结构审计 (Prognosis)
P:    YES|PARTIAL|NO   患者人群是否明确
PF:   YES|PARTIAL|NO   Prognostic Factor（预后因素）是否明确
O:    YES|PARTIAL|NO   结局是否明确
TH:   YES|PARTIAL|NA   Time Horizon（随访时间窗）是否明确（原问题未提及→NA）
pico_statement_unambiguous: YES|PARTIAL|NO
```

**direct_answer：**
```
## 结构审计 (direct_answer)
all_three_conditions_met: YES | NO
三个条件（须全部满足才应路由到 direct_answer）：
  1. 问题要求立即操作性指导（动词：如何处理/立即给/紧急处置）
  2. 延迟回答会直接危及患者生命安全
  3. 答案来自已有公认标准流程（BLS/ACLS/指南操作章节）
YES=三条均满足；NO=任一条不满足（应重新路由到 EBM 流程）

standard_protocol_cited: YES | NO  是否引用了公认标准操作规范
```

**diagnostic_reasoning（Step1+所有Step2完成后批量）：**
```
## 结构审计 (Diagnostic Reasoning)

### 鉴别诊断质量（Step1）
clinical_feature_completeness: YES|PARTIAL|NO  关键症状/体征/检查是否遗漏
differential_reasonableness:   YES|PARTIAL|NO  鉴别诊断是否与临床特征匹配
critical_diagnosis_prioritized: YES|NO         危重/需立即排除的诊断是否排在前列

### 子PICO对应关系（Step2，批量）
sub_pico_audit: 数组，每个元素：
  - diagnosis: 对应的鉴别诊断名称
  - correspondence: YES|PARTIAL|NO
  - issue: 若非YES，说明具体问题；否则填null
```

### 输出格式（所有路由共用框架）

```json
{
  "route_audit": {
    "route_appropriateness": "YES | NO",
    "ambiguity_flag": "YES | NO"
  },
  "safety_audit": {
    "intent_distorted": "YES | NO"
  },
  "search_audit": {
    "boolean_logic_valid": "YES | NO"
  },
  "structure_audit": {
    /* 动态字段，按 route_type 变化，见上方各段 */
  },
  "failures": ["具体失败项及原因（无失败则为空列表）"],
  "overall_quality": "pass | fail | degraded"
}
```

`routing_decision` 不在 LLM 输出中，由 Python 推导。

---

## Python 评分：`_score_ask`

### 维度权重

```python
STAGE_WEIGHTS = {
    "Ask": {
        "pico_completeness": 0.45,
        "searchability":     0.30,
        "clarity":           0.25,
    },
    # 其他阶段不变
}

PASS_THRESHOLD = 0.70  # 沿用现有阈值
```

### 评分逻辑

```python
def _score_ask(audit: dict, precheck: dict, route_type: str
               ) -> Tuple[dict, list, bool, str]:
    issues = []

    # 0. Python 预检失败项注入 issues
    if precheck["keywords_english_medical"] == "NO":
        issues.append({"severity": "major", "dimension": "searchability",
                       "description": "keywords 包含中文，必须全部使用英文医学术语（MeSH）"})
    if precheck["has_synonyms_or_mesh"] == "NO":
        issues.append({"severity": "minor", "dimension": "searchability",
                       "description": "缺少同义词扩展，请为核心概念补充 MeSH 词或常见别名"})
    if not precheck["keyword_count_ok"]:
        issues.append({"severity": "major", "dimension": "searchability",
                       "description": "关键词数量不足（≤1），无法构成有效检索策略"})

    # 1. 安全项：intent_distorted（一票否决）
    if audit.get("safety_audit", {}).get("intent_distorted") == "YES":
        return (
            {"pico_completeness": 0.0, "searchability": 0.0, "clarity": 0.0},
            [{"severity": "critical", "dimension": "pico_completeness",
              "description": "PICO结构化结果严重扭曲了用户原始意图"}],
            False, "意图严重扭曲，任务失败"
        )

    # 2. 路由失败（route_appropriateness=NO，一票否决）
    if audit.get("route_audit", {}).get("route_appropriateness") == "NO":
        return (
            {"pico_completeness": 0.0, "searchability": 0.0, "clarity": 0.0},
            [{"severity": "critical", "dimension": "pico_completeness",
              "description": "路由分类错误，需重新路由"}],
            False, "路由错误，需重试"
        )

    # 3. 结构化得分（按 route_type 分支）
    structure = audit.get("structure_audit", {})

    if route_type in ("ebm_pico", "ebm_pird", "ebm_peo", "ebm_prognosis"):
        pico_completeness = _score_structure_fields(structure, route_type, issues)
    elif route_type == "direct_answer":
        pico_completeness = 1.0 if structure.get("all_three_conditions_met") == "YES" else 0.0
        if structure.get("all_three_conditions_met") == "NO":
            issues.append({"severity": "critical", "dimension": "pico_completeness",
                           "description": "direct_answer 三个触发条件未全部满足，应重新路由到 EBM 流程"})
    elif route_type == "diagnostic_reasoning":
        pico_completeness = _score_diagnostic_reasoning(structure, issues)
    else:
        pico_completeness = 0.5

    # 4. searchability（Python 预检 + LLM boolean_logic）
    kw_score  = 1.0 if precheck["keywords_english_medical"] == "YES" else 0.0
    syn_score = 1.0 if precheck["has_synonyms_or_mesh"] == "YES" else 0.0
    bl_score  = 1.0 if audit.get("search_audit", {}).get("boolean_logic_valid") == "YES" else 0.0
    searchability = (kw_score + syn_score + bl_score) / 3

    # 5. clarity
    clarity_map = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0.1}
    clarity = clarity_map.get(structure.get("pico_statement_unambiguous", "YES"), 1.0)
    if structure.get("pico_statement_unambiguous") == "NO":
        issues.append({"severity": "major", "dimension": "clarity",
                       "description": "PICO表述存在严重歧义，请重新提炼问题"})
    elif structure.get("pico_statement_unambiguous") == "PARTIAL":
        issues.append({"severity": "minor", "dimension": "clarity",
                       "description": "PICO表述存在轻微歧义，请澄清不明确的术语"})

    dimension_scores = {
        "pico_completeness": pico_completeness,
        "searchability":     searchability,
        "clarity":           clarity,
    }
    return dimension_scores, issues, False, "; ".join(audit.get("failures", []))
```

### EBM 格式结构字段权重（`_score_structure_fields`）

| 字段 | PICO | PIRD | PEO | Prognosis | YES | PARTIAL | NO | NA |
|---|---|---|---|---|---|---|---|---|
| P（人群） | 3 | 3 | 3 | 3 | 1.0 | 0.4 | 0.0 | 1.0 |
| I/IndexTest/Exposure/PF | 3 | 3 | 3 | 3 | 1.0 | 0.4 | 0.0 | — |
| C/R | 1 | 2 | — | — | 1.0 | 0.4 | 0.0 | 1.0 |
| O/D | 2 | 2 | 2 | 2 | 1.0 | 0.4 | 0.0 | — |
| TH（time_horizon） | — | — | — | 1 | 1.0 | 0.4 | 0.0 | 1.0 |

分数 = Σ(字段权重 × 字段得分) / Σ字段权重

### `_score_diagnostic_reasoning` 权重

```python
def _score_diagnostic_reasoning(structure: dict, issues: list) -> float:
    label_map = {"YES": 1.0, "PARTIAL": 0.4, "NO": 0.0}

    # Step1：鉴别诊断质量（60%）
    # critical_diagnosis_prioritized 权重最高（患者安全）
    cf = label_map.get(structure.get("clinical_feature_completeness", "YES"), 1.0)
    dr = label_map.get(structure.get("differential_reasonableness", "YES"), 1.0)
    cp = 1.0 if structure.get("critical_diagnosis_prioritized") != "NO" else 0.0
    step1 = cf * 0.30 + dr * 0.30 + cp * 0.40

    if structure.get("clinical_feature_completeness") == "NO":
        issues.append({"severity": "major", "dimension": "pico_completeness",
                       "description": "关键临床特征提取不完整，鉴别诊断可能遗漏重要线索"})
    if structure.get("differential_reasonableness") == "NO":
        issues.append({"severity": "major", "dimension": "pico_completeness",
                       "description": "鉴别诊断与临床特征不匹配，请重新分析"})
    if structure.get("critical_diagnosis_prioritized") == "NO":
        issues.append({"severity": "critical", "dimension": "pico_completeness",
                       "description": "危重/需立即排除的诊断未排在首位，存在患者安全风险"})

    # Step2：子PICO对应关系（40%）
    sub_audits = structure.get("sub_pico_audit", [])
    if not sub_audits:
        step2 = 1.0  # 尚未生成子PICO，不扣分
    else:
        corr_scores = [label_map.get(s.get("correspondence", "YES"), 1.0)
                       for s in sub_audits]
        step2 = sum(corr_scores) / len(corr_scores)
        for s in sub_audits:
            if s.get("correspondence") == "NO":
                issues.append({"severity": "major", "dimension": "pico_completeness",
                               "description": f"子PICO（{s.get('diagnosis','?')}）"
                                              f"与鉴别诊断不对应：{s.get('issue','')}"})
            elif s.get("correspondence") == "PARTIAL":
                issues.append({"severity": "minor", "dimension": "pico_completeness",
                               "description": f"子PICO（{s.get('diagnosis','?')}）"
                                              f"对应关系有偏差：{s.get('issue','')}"})

    return step1 * 0.60 + step2 * 0.40
```

---

## `routing_decision` Python 推导

```python
def _derive_routing_decision(audit: dict, pass_threshold: bool,
                              retry_count: int, max_retry: int = 2) -> str:
    route_ok  = audit.get("route_audit", {}).get("route_appropriateness") == "YES"
    intent_ok = audit.get("safety_audit", {}).get("intent_distorted") == "NO"

    if not intent_ok:
        return "retry_structure" if retry_count < max_retry else "fallback"
    if not route_ok:
        return "retry_route" if retry_count < max_retry else "fallback"
    if pass_threshold:
        return "proceed"
    return "retry_structure" if retry_count < max_retry else "fallback"
```

### Pass/Fail 判定

```python
overall_score  = _calculate_overall_score("Ask", dimension_scores)
has_critical   = any(i["severity"] == "critical" for i in raw_issues)
pass_threshold = (overall_score >= PASS_THRESHOLD) and not has_critical
```

Pass 条件：加权分 ≥ 0.70 **且** 无 critical issue。

### 完整决策流

```
overall_score ≥ 0.70 且无 critical
    → pass_threshold=True → routing_decision="proceed" → 进入 Acquire

overall_score < 0.70 或有 critical（路由错误）
    → routing_decision="retry_route" → 重新路由（最多2次）

overall_score < 0.70 或有 critical（结构化不达标）
    → routing_decision="retry_structure" → 重新结构化（最多2次）

超过 max_retry
    → routing_decision="fallback" → route_confidence="low"，强制 ebm_pico 继续
```

---

## `route_confidence` 下游传递

```python
# judge_llm.py evaluate_stage()（Ask 阶段）
if stage == "Ask":
    retry_count = state.get("agent_call_counts", {}).get("Ask", 1) - 1
    routing_decision = _derive_routing_decision(audit, pass_threshold, retry_count)
    state["_ask_routing_decision"] = routing_decision
    if routing_decision == "fallback":
        state["route_confidence"] = "low"

# apply_agent.py：生成推荐时
if state.get("route_confidence") == "low":
    recommendation.caveats.append(
        "本问题的结构化框架存在路由不确定性（Ask 阶段降级处理），推荐结论需结合临床判断"
    )
```

---

## 文件改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/config/prompts/judge/ask_judge.txt` | 重写 | 单 prompt + 动态注入；路由/安全/搜索/结构四块；删除 `format_match`；`failures`+`overall_quality` 输出；删除 `routing_decision` 输出字段 |
| `src/judge/judge_llm.py` | 修改 | `_precheck_ask` 新增；`_score_ask` 重写（含分支权重）；`_score_structure_fields` 新增；`_score_diagnostic_reasoning` 新增；`_derive_routing_decision` 新增；`evaluate_stage` 中 Ask 阶段写入 `route_confidence` |
| `src/coordinator/coordinator.py` | 小改 | 读取 `_ask_routing_decision` 执行 retry_route / retry_structure / fallback 分支 |
| `src/agents/apply_agent.py` | 小改 | 检测 `route_confidence="low"` 时追加 caveat |

---

## 明确不在本次范围内

- Acquire/Appraise/Apply/Assess Judge 的 route_type 适配
- `ambiguity_flag=YES` 时的 UI 提示（当前仅写入 `route_confidence` 日志）
- `WorkflowState` 中 `route_confidence` 字段的持久化格式（实现阶段决定）
