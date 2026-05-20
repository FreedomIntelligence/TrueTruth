import json
from typing import Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import asdict, is_dataclass
from src.state.schema import Observe, Evaluation, WorkflowState
from src.agents.base import robust_parse_json

# Rubric weight definitions per stage.
# Each rubric: (weight, allows_partial)
# Gate items are checked separately in _check_gates() — not listed here.
RUBRIC_WEIGHTS = {
    "Ask": {
        "core_dimensions_present":      (3, True),   # Critical
        "secondary_dimensions_present": (2, True),   # Major
        "statement_unambiguous":        (1, True),   # Minor
    },
    "Acquire": {
        "keywords_cover_pico_dimensions": (3, True),
        "primary_focus_match":            (3, True),
        "p_match":                        (3, True),
        "o_match":                        (3, True),
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
        "effect_size_correctly_reported":     (3, True),
        "strength_matches_evidence":          (3, True),
        "population_applicability_addressed": (2, True),
        "uncertainty_source_explained":       (2, True),
        "citation_traceable":                 (2, True),
        "recommendation_specific":            (1, True),
        "patient_preference_considered":      (1, True),
    },
}

# Legacy weights kept for Assess stage (unchanged)
_ASSESS_WEIGHTS = {
    "answer_completeness": 0.35,
    "reasoning_chain": 0.35,
    "logical_consistency": 0.30,
}

PASS_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# Gate + Rubric helpers (shared across stages)
# ---------------------------------------------------------------------------


def _check_gates(stage: str, audit: Dict) -> List[str]:
    """
    Check gate items for a stage. Returns list of failed gate names.
    Any gate failure means overall fail regardless of rubric scores.
    """
    gate_results = audit.get("gate_results", {})
    failed: List[str] = []

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


def _score_rubrics(stage: str, audit: Dict) -> Tuple[Dict[str, Any], List[Dict], float]:
    """
    Score rubric items using the weighted rubric system.
    Returns (dimension_scores, raw_issues, overall_score).
    NA items are excluded from the denominator.
    YES = full weight, PARTIAL = weight * 0.5, NO = 0.
    """
    rubric_weights = RUBRIC_WEIGHTS.get(stage, {})
    rubric_results = audit.get("rubric_results", {})
    issues: List[Dict] = []
    total_score = 0.0
    total_max = 0.0
    dimension_scores: Dict[str, Any] = {}

    for rubric_name, (weight, allows_partial) in rubric_weights.items():
        val = rubric_results.get(rubric_name, "NA")
        if val == "NA":
            dimension_scores[rubric_name] = None  # excluded from denominator
            continue

        if val == "YES":
            score = float(weight)
        elif val == "PARTIAL" and allows_partial:
            score = weight * 0.5
        else:  # NO or PARTIAL on a non-partial rubric
            score = 0.0

        total_score += score
        total_max += weight
        dimension_scores[rubric_name] = score / weight  # normalise to 0-1 for display

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


def _appraise_layer1_check(output: Dict) -> Dict:
    """
    Layer 1 Python hardcoded validation for Appraise stage.
    Returns dict with keys: passed (bool), failures (list[str]).
    If passed=True, skip LLM Judge entirely.
    Raises SystemError if grade_output_in_legal_range fails.
    """
    LEGAL_GRADES = {"High", "Moderate", "Low", "Very Low"}
    LEGAL_STUDY_TYPES = {
        "RCT", "COHORT", "CASE_CONTROL", "CASE_REPORT",
        "SYSTEMATIC_REVIEW", "META_ANALYSIS", "NMA",
        "GUIDELINE", "CROSS_SECTIONAL", "NARRATIVE_REVIEW", "EXPERT_OPINION",
    }
    failures: List[str] = []

    appraisal = output.get("appraisal_results")
    if appraisal is None:
        failures.append("appraisal_results missing")
        return {"passed": False, "failures": failures}

    appraisal_d = asdict(appraisal) if is_dataclass(appraisal) else appraisal
    evidence_list = appraisal_d.get("evidence", []) if isinstance(appraisal_d, dict) else []

    for ev in evidence_list:
        study_type = ev.get("study_type")
        if not study_type or study_type not in LEGAL_STUDY_TYPES:
            failures.append(
                f"study_type missing or illegal: pmid={ev.get('pmid', '?')} study_type={study_type}"
            )

        rob = ev.get("risk_of_bias")
        if rob is None:
            failures.append(f"risk_of_bias missing: pmid={ev.get('pmid', '?')}")

        grade = ev.get("grade_level")
        if grade and grade not in LEGAL_GRADES:
            raise SystemError(
                f"grade_output_in_legal_range FAILED: pmid={ev.get('pmid', '?')} grade={grade}. "
                "Illegal grade value — workflow terminated."
            )

    return {"passed": len(failures) == 0, "failures": failures}


# ---------------------------------------------------------------------------
# Per-stage Python scoring functions
# Each function takes the LLM audit dict and returns:
#   (dimension_scores, raw_issues, search_exhausted, reasoning_hint)
# ---------------------------------------------------------------------------


def _precheck_ask(pico_dict: dict) -> dict:
    """Pre-check Ask output for basic keyword quality before LLM judge call."""
    import re
    chinese = re.compile(r'[一-鿿]')
    keywords = pico_dict.get("keywords", [])
    keywords_english = not any(chinese.search(kw) for kw in keywords)
    has_synonyms = len(set(keywords)) >= 2
    keyword_count_ok = len(keywords) > 1
    return {
        "keywords_english_medical": "YES" if keywords_english else "NO",
        "has_synonyms_or_mesh":     "YES" if has_synonyms else "NO",
        "keyword_count_ok":         keyword_count_ok,
    }


def _derive_routing_decision(audit: dict, pass_threshold: bool,
                              retry_count: int, max_retry: int = 2) -> str:
    """Derive routing decision from Ask judge audit without LLM output."""
    gate_results = audit.get("gate_results", {})
    intent_ok = gate_results.get("intent_not_distorted") != "NO"
    route_ok = gate_results.get("route_correct") != "NO"
    if not intent_ok:
        return "retry_structure" if retry_count < max_retry else "fallback"
    if not route_ok:
        return "retry_route" if retry_count < max_retry else "fallback"
    if pass_threshold:
        return "proceed"
    return "retry_structure" if retry_count < max_retry else "fallback"


def _score_ask(audit: Dict) -> Tuple[Dict[str, Any], List[Dict], bool, str]:
    """Gate + Rubric scoring for Ask stage."""
    gate_failures = _check_gates("Ask", audit)
    if gate_failures:
        issues = [
            {"severity": "critical", "dimension": g, "description": f"Gate 失败: {g}"}
            for g in gate_failures
        ]
        return {"core_dimensions_present": 0.0}, issues, False, f"Gate失败: {', '.join(gate_failures)}"

    # direct_answer: gate passed means classification correct → terminate signal
    gate_results = audit.get("gate_results", {})
    if gate_results.get("nonresearch_classification_correct") == "YES":
        return {"nonresearch": 1.0}, [], False, "direct_answer路由正确，触发terminate"

    dim_scores, issues, overall = _score_rubrics("Ask", audit)
    failures = audit.get("failures", [])
    hint = "; ".join(failures) if failures else f"综合评分: {overall:.2f}"
    return dim_scores, issues, False, hint


def _score_ask_legacy(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Legacy Ask scoring — kept for backward compat with old prompt format."""
    issues: List[Dict] = []

    # --- Safety circuit breaker ---
    if audit.get("safety_audit", {}).get("intent_distorted") == "YES":
        return (
            {"pico_completeness": 0.0, "searchability": 0.0, "clarity": 0.0},
            [
                {
                    "severity": "critical",
                    "dimension": "pico_completeness",
                    "description": (
                        "严重错误：PICO结构化结果扭曲了用户的原始意图。"
                        "请重新分析原问题，确保人群和干预措施与用户描述完全一致。"
                    ),
                }
            ],
            False,
            "PICO意图被严重扭曲，任务直接失败。",
        )

    # --- PICO completeness (maps to 0-1 per element, then average) ---
    pico_map = {"YES": 1.0, "PARTIAL": 0.4, "NO": 0.0, "NA": 1.0}
    pico_labels = {
        "P": "Patient（患者人群）",
        "I": "Intervention（干预措施）",
        "C": "Comparison（对照组）",
        "O": "Outcome（临床结局）",
    }
    pico_audit = audit.get("pico_audit", {})
    pico_scores = []
    for element in ["P", "I", "C", "O"]:
        val = pico_audit.get(element, "NO")
        pico_scores.append(pico_map.get(val, 0.0))
        if val == "PARTIAL":
            issues.append(
                {
                    "severity": "major",
                    "dimension": "pico_completeness",
                    "description": (
                        f"PICO中的 {pico_labels[element]} 要素描述模糊，"
                        "请在下次输出中提供更具体的描述（如具体疾病名称、干预剂量等）。"
                    ),
                }
            )
        elif val == "NO":
            severity = "critical" if element in ("P", "I", "O") else "major"
            issues.append(
                {
                    "severity": severity,
                    "dimension": "pico_completeness",
                    "description": (
                        f"PICO中缺失 {pico_labels[element]} 要素，"
                        "请在下次输出中补充完整。"
                    ),
                }
            )
    pico_completeness = sum(pico_scores) / 4

    # --- Searchability ---
    search_audit = audit.get("search_audit", {})
    binary_map = {"YES": 1.0, "NO": 0.0}
    kw_score = binary_map.get(search_audit.get("keywords_english_medical", "YES"), 1.0)
    exp_score = binary_map.get(search_audit.get("has_synonyms_or_mesh", "YES"), 1.0)
    logic_score = binary_map.get(search_audit.get("boolean_logic_valid", "YES"), 1.0)
    searchability = (kw_score + exp_score + logic_score) / 3

    if search_audit.get("keywords_english_medical") == "NO":
        issues.append(
            {
                "severity": "major",
                "dimension": "searchability",
                "description": (
                    "关键词必须转化为标准的英文医学术语（MeSH），"
                    "请勿使用中文或口语化词汇。"
                ),
            }
        )
    if search_audit.get("has_synonyms_or_mesh") == "NO":
        issues.append(
            {
                "severity": "minor",
                "dimension": "searchability",
                "description": (
                    "缺少同义词扩展，请为核心概念补充MeSH词或常见别名"
                    "（如 'heart failure' OR 'cardiac failure'）。"
                ),
            }
        )
    if search_audit.get("boolean_logic_valid") == "NO":
        issues.append(
            {
                "severity": "major",
                "dimension": "searchability",
                "description": "布尔逻辑（AND/OR）使用错误，请检查检索策略的逻辑结构。",
            }
        )

    # --- Clarity ---
    clarity_audit = audit.get("clarity_audit", {})
    clarity_map = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0.1}
    clarity_val = clarity_audit.get("pico_statement_unambiguous", "YES")
    clarity = clarity_map.get(clarity_val, 1.0)
    if clarity_val == "PARTIAL":
        issues.append(
            {
                "severity": "minor",
                "dimension": "clarity",
                "description": "PICO表述存在轻微歧义，请澄清不明确的术语或条件。",
            }
        )
    elif clarity_val == "NO":
        issues.append(
            {
                "severity": "major",
                "dimension": "clarity",
                "description": "PICO表述存在严重歧义，请重新提炼问题，确保表述无歧义。",
            }
        )

    dimension_scores = {
        "pico_completeness": pico_completeness,
        "searchability": searchability,
        "clarity": clarity,
    }
    return dimension_scores, issues, False, audit.get("reasoning", "")


def _score_acquire(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Acquire audit classifications to dimension scores and issues.

    Reads the Gate+Rubrics format produced by acquire_judge.txt:
      gate_results.search_terms_valid
      rubric_results.{keywords_cover_pico_dimensions, primary_focus_match, ...}
      overall_quality: pass | fail | gate_fail
      failures: [...]
    """
    issues: List[Dict] = []
    gate_results = audit.get("gate_results", {})
    search_exhausted = bool(audit.get("search_exhausted", False))

    # Gate: invalid search terms
    if gate_results.get("search_terms_valid") == "NO":
        issues.append({
            "severity": "critical",
            "dimension": "search_terms_valid",
            "description": "检索词构建有误，检索方向完全错误。请根据PICO重新设计检索策略。",
        })
        return {"overall": 0.0}, issues, False, "检索词严重错误，无法获取有效证据。"

    # Rubric scoring via shared helper
    dim_scores, rubric_issues, overall_score = _score_rubrics("Acquire", audit)
    issues.extend(rubric_issues)

    # Translate failures[] from LLM into additional context
    for failure_msg in audit.get("failures", []):
        if failure_msg and not any(failure_msg in i.get("description", "") for i in issues):
            issues.append({
                "severity": "minor",
                "dimension": "acquire_detail",
                "description": failure_msg,
            })

    return dim_scores, issues, search_exhausted, audit.get("reasoning", "")


def _score_appraise(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Appraise audit classifications to dimension scores and issues.

    Reads gate_results/rubric_results from appraise_judge.txt output.
    Gates: study_type_correct, computed_grade_reasonable
    Rubrics: downgrade_factors_appropriate, included_study_type_correct,
             upgrade_factors_appropriate, upgrade_blocked_appropriate,
             conflicts_identified, numerical_data_extracted
    """
    issues: List[Dict] = []
    gate_results = audit.get("gate_results", {})
    search_exhausted = bool(audit.get("search_exhausted", False))

    # G1 → G2 dependency: if study_type is wrong, G2 is automatically UNCERTAIN
    # (wrong study_type already captured by G1; don't double-penalise with G2)
    g1 = gate_results.get("study_type_correct", "YES")
    g2 = gate_results.get("computed_grade_reasonable", "YES")
    if g1 == "NO":
        g2 = "UNCERTAIN"

    if g2 == "NO":
        # Hard gate: calculation is clearly wrong
        issues.append({
            "severity": "critical",
            "dimension": "computed_grade_reasonable",
            "description": "Gate 失败: computed_grade_reasonable — GRADE等级计算明显不合理",
        })
        return {"overall": 0.0}, issues, False, "Gate失败: computed_grade_reasonable"

    if g2 == "UNCERTAIN":
        # Soft warning: study design ambiguous, can't verify — demote to MAJOR
        issues.append({
            "severity": "major",
            "dimension": "computed_grade_reasonable",
            "description": "computed_grade_reasonable 无法确认（研究设计有歧义或摘要信息不足）",
        })

    # Rubric scoring
    dim_scores, rubric_issues, overall_score = _score_rubrics("Appraise", audit)
    issues.extend(rubric_issues)

    # study_type_correct as a major issue (not gate-level)
    if gate_results.get("study_type_correct") == "NO":
        issues.append({
            "severity": "major",
            "dimension": "study_type_correct",
            "description": "存在研究类型识别错误，请检查 study_type 标注",
        })

    for failure_msg in audit.get("failures", []):
        if failure_msg and not any(failure_msg in i.get("description", "") for i in issues):
            issues.append({
                "severity": "minor",
                "dimension": "appraise_detail",
                "description": failure_msg,
            })

    return dim_scores, issues, search_exhausted, audit.get("reasoning", "")


def _score_apply(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Apply audit classifications to dimension scores and issues.

    Reads gate_results/rubric_results from apply_judge.txt output.
    Gates: recommendation_grounded_in_evidence, route_dimension_consistent,
           strength_not_grossly_inflated
    Rubrics: effect_size_correctly_reported, strength_matches_evidence,
             population_applicability_addressed, uncertainty_source_explained,
             citation_traceable, recommendation_specific, patient_preference_considered
    """
    issues: List[Dict] = []
    gate_results = audit.get("gate_results", {})
    search_exhausted = bool(audit.get("search_exhausted", False))

    # Gates
    gate_failures = []
    for gate_key in ("recommendation_grounded_in_evidence", "route_dimension_consistent",
                     "strength_not_grossly_inflated"):
        if gate_results.get(gate_key) == "NO":
            gate_failures.append(gate_key)

    if gate_failures:
        for g in gate_failures:
            issues.append({
                "severity": "critical",
                "dimension": g,
                "description": f"Gate 失败: {g}",
            })
        return {"overall": 0.0}, issues, False, f"Gate失败: {', '.join(gate_failures)}"

    # Rubric scoring
    dim_scores, rubric_issues, overall_score = _score_rubrics("Apply", audit)
    issues.extend(rubric_issues)

    for failure_msg in audit.get("failures", []):
        if failure_msg and not any(failure_msg in i.get("description", "") for i in issues):
            issues.append({
                "severity": "minor",
                "dimension": "apply_detail",
                "description": failure_msg,
            })

    return dim_scores, issues, search_exhausted, audit.get("reasoning", "")


def _score_assess(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Assess audit classifications to dimension scores and issues."""
    issues: List[Dict] = []
    completeness_audit = audit.get("completeness_audit", {})
    chain_audit = audit.get("chain_audit", {})
    consistency_audit = audit.get("consistency_audit", {})

    # --- answer_completeness ---
    answered_map = {"YES": 1.0, "PARTIAL": 0.55, "NO": 0.1}
    limitations_map = {"YES": 1.0, "NO": 0.5, "NA": 1.0}
    answered_val = completeness_audit.get("original_question_answered", "YES")
    limitations_val = completeness_audit.get("evidence_limitations_stated", "NA")
    answer_completeness = 0.7 * answered_map.get(
        answered_val, 1.0
    ) + 0.3 * limitations_map.get(limitations_val, 1.0)

    if answered_val == "NO":
        issues.append(
            {
                "severity": "critical",
                "dimension": "answer_completeness",
                "description": (
                    "完全未回答原始临床问题，"
                    "请检查整个推理链是否与原始问题对齐，必要时回退Ask阶段。"
                ),
            }
        )
    elif answered_val == "PARTIAL":
        issues.append(
            {
                "severity": "major",
                "dimension": "answer_completeness",
                "description": ("原始问题未被完整回答，请检查遗漏的方面并补充说明。"),
            }
        )
    if limitations_val == "NO":
        issues.append(
            {
                "severity": "minor",
                "dimension": "answer_completeness",
                "description": (
                    "未说明证据局限性，请在最终输出中明确标注证据的适用范围和不确定性。"
                ),
            }
        )

    # --- reasoning_chain ---
    link_map = {"CLEAR": 1.0, "WEAK": 0.5, "BROKEN": 0.0}
    ask_acquire_val = chain_audit.get("ask_to_acquire_link", "CLEAR")
    acquire_appraise_val = chain_audit.get("acquire_to_appraise_link", "CLEAR")
    appraise_apply_val = chain_audit.get("appraise_to_apply_link", "CLEAR")
    reasoning_chain = (
        link_map.get(ask_acquire_val, 1.0)
        + link_map.get(acquire_appraise_val, 1.0)
        + link_map.get(appraise_apply_val, 1.0)
    ) / 3

    chain_issues = [
        (
            ask_acquire_val,
            "Ask→Acquire",
            "检索策略与PICO脱节，建议回退Ask阶段重新构建检索策略。",
        ),
        (
            acquire_appraise_val,
            "Acquire→Appraise",
            "证据评价与检索结果不一致，建议回退Appraise阶段。",
        ),
        (
            appraise_apply_val,
            "Appraise→Apply",
            "推荐强度与证据评价不一致，建议回退Apply阶段。",
        ),
    ]
    for val, link_name, broken_desc in chain_issues:
        if val == "BROKEN":
            issues.append(
                {
                    "severity": "major",
                    "dimension": "reasoning_chain",
                    "description": f"推理链断裂（{link_name}）：{broken_desc}",
                }
            )
        elif val == "WEAK":
            issues.append(
                {
                    "severity": "minor",
                    "dimension": "reasoning_chain",
                    "description": f"推理链薄弱（{link_name}）：连接关系不够清晰，请加强各阶段的逻辑衔接。",
                }
            )

    # --- logical_consistency ---
    consistency_map = {"YES": 1.0, "MINOR_ISSUE": 0.65, "MAJOR_CONTRADICTION": 0.1}
    grade_strength_val = consistency_audit.get("grade_to_strength_consistent", "YES")
    no_contradictions_val = consistency_audit.get("no_internal_contradictions", "YES")
    logical_consistency = 0.5 * consistency_map.get(
        grade_strength_val, 1.0
    ) + 0.5 * consistency_map.get(no_contradictions_val, 1.0)

    if grade_strength_val == "MAJOR_CONTRADICTION":
        issues.append(
            {
                "severity": "critical",
                "dimension": "logical_consistency",
                "description": (
                    "证据质量与推荐强度存在根本性矛盾（如Very Low证据→Strong推荐），"
                    "建议回退Apply阶段修正推荐强度。"
                ),
            }
        )
    elif grade_strength_val == "MINOR_ISSUE":
        issues.append(
            {
                "severity": "minor",
                "dimension": "logical_consistency",
                "description": "证据质量与推荐强度存在轻微不协调，请检查Apply阶段的强度设定。",
            }
        )

    if no_contradictions_val == "MAJOR_CONTRADICTION":
        issues.append(
            {
                "severity": "major",
                "dimension": "logical_consistency",
                "description": (
                    "推理链内部存在重大矛盾（如不同阶段的人群/干预/结论方向不一致），"
                    "请检查各阶段输出是否相互支撑。"
                ),
            }
        )
    elif no_contradictions_val == "MINOR_ISSUE":
        issues.append(
            {
                "severity": "minor",
                "dimension": "logical_consistency",
                "description": "推理链内部存在轻微不一致，可接受但建议进一步完善。",
            }
        )

    dimension_scores = {
        "answer_completeness": answer_completeness,
        "reasoning_chain": reasoning_chain,
        "logical_consistency": logical_consistency,
    }
    failures = audit.get("failures", [])
    hint = "; ".join(failures) if failures else f"综合评分: {(answer_completeness + reasoning_chain + logical_consistency) / 3:.2f}"
    return dimension_scores, issues, False, hint


# Dispatch table: stage name -> scorer function
STAGE_SCORERS = {
    "Ask": _score_ask,
    "Acquire": _score_acquire,
    "Appraise": _score_appraise,
    "Apply": _score_apply,
    "Assess": _score_assess,
}


class JudgeLLM:
    """
    Judge LLM that evaluates stage outputs and generates structured Observe.

    Architecture:
      1. LLM receives a classification-only audit prompt and outputs categorical
         labels (YES/NO/PARTIAL, etc.) — no numerical scores.
      2. A per-stage Python scorer converts those labels into dimension scores,
         generates issues with appropriate severity, and computes overall_score.
      3. Returns the same Observe/Evaluation structure as before.
    """

    def __init__(self, llm):
        self.llm = llm
        self.prompt_dir = Path(__file__).parent.parent / "config" / "prompts" / "judge"
        # Preload all stage prompts at init to avoid repeated disk I/O during workflow.
        # SchedulingLLM already does this; JudgeLLM now follows the same pattern.
        self._prompt_cache: Dict[str, str] = {}
        for stage in ["Ask", "Acquire", "Appraise", "Apply", "Assess"]:
            path = self.prompt_dir / f"{stage.lower()}_judge.txt"
            if path.exists():
                self._prompt_cache[stage] = path.read_text(encoding="utf-8")

    def _load_prompt(self, stage: str) -> str:
        """Load judge prompt for a specific stage (from cache if available)."""
        if stage in self._prompt_cache:
            return self._prompt_cache[stage]
        # Fallback to disk for any stage not preloaded
        prompt_path = self.prompt_dir / f"{stage.lower()}_judge.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _format_stage_output(self, output: Dict[str, Any]) -> str:
        """Serialize stage output to JSON string for prompt injection."""
        serializable_output = {}
        for key, value in output.items():
            if is_dataclass(value):
                serializable_output[key] = asdict(value)
            elif isinstance(value, list) and value and is_dataclass(value[0]):
                serializable_output[key] = [asdict(item) for item in value]
            else:
                serializable_output[key] = value
        return json.dumps(
            serializable_output, ensure_ascii=False, indent=2, default=str
        )

    def _calculate_overall_score(
        self, stage: str, dimension_scores: Dict[str, float]
    ) -> float:
        """Calculate weighted overall score from dimension scores."""
        # direct_answer Ask path uses a single "nonresearch" dimension that isn't
        # in RUBRIC_WEIGHTS — return it directly so it isn't dropped to 0.
        if stage == "Ask" and "nonresearch" in dimension_scores:
            return dimension_scores["nonresearch"]

        weights = {dim: w for dim, (w, _) in RUBRIC_WEIGHTS.get(stage, {}).items()}
        if not weights:
            valid = [v for v in dimension_scores.values() if v is not None]
            return sum(valid) / len(valid) if valid else 0.0
        total = 0.0
        weight_sum = 0.0
        for dim, weight in weights.items():
            val = dimension_scores.get(dim)
            if val is None:
                continue  # NA — excluded from denominator
            total += val * weight
            weight_sum += weight
        return total / weight_sum if weight_sum > 0 else 0.0

    def _has_critical_issue(self, issues: List) -> bool:
        """Return True if any issue has critical severity."""
        return any(
            (issue.severity if hasattr(issue, "severity") else issue.get("severity"))
            == "critical"
            for issue in issues
        )

    def evaluate_stage(
        self, stage: str, output: Dict[str, Any], state: WorkflowState
    ) -> Observe:
        """
        Evaluate a stage's output and return a structured Observe.

        Steps:
          1. Build prompt with stage-specific context.
          2. Call LLM → receives classification audit JSON (no scores).
          3. Run Python scorer → converts classifications to dimension_scores + issues.
          4. Compute weighted overall_score and pass_threshold in Python.
          5. Return Observe.
        """
        from src.state.schema import Issue as IssueSchema, Observe as ObserveSchema

        prompt_template = self._load_prompt(stage)
        context = self._prepare_context(stage, output, state)
        prompt = prompt_template.format(**context)

        response = self.llm.invoke(prompt)

        try:
            audit = self._parse_json_response(response.content)
        except Exception as e:
            print(f"Error parsing judge response: {e}")
            print(f"Response: {response.content}")
            raise

        # Select stage scorer
        scorer = STAGE_SCORERS.get(stage)
        if scorer is None:
            raise ValueError(f"No scorer defined for stage: {stage}")

        dimension_scores, raw_issues, search_exhausted, reasoning_hint = scorer(audit)
        overall_score = self._calculate_overall_score(stage, dimension_scores)

        issues = [
            IssueSchema(
                severity=issue["severity"],
                dimension=issue["dimension"],
                description=issue["description"],
            )
            for issue in raw_issues
        ]

        pass_threshold = (
            overall_score >= PASS_THRESHOLD and not self._has_critical_issue(issues)
        )

        summary = reasoning_hint if reasoning_hint else f"综合评分: {overall_score:.2f}"

        # For Ask stage: derive routing decision and write to state as side effect
        if stage == "Ask":
            retry_count = state.get("agent_call_counts", {}).get("Ask", 1) - 1
            routing_decision = _derive_routing_decision(audit, pass_threshold, retry_count)
            state["_ask_routing_decision"] = routing_decision  # type: ignore[typeddict-unknown-key]
            if routing_decision == "fallback":
                state["route_confidence"] = 0.0  # type: ignore[typeddict-item]

        evaluation = Evaluation(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            pass_threshold=pass_threshold,
            issues=issues,
            summary=summary,
            search_exhausted=search_exhausted,
        )

        return ObserveSchema(
            stage=stage,
            output=output,
            evaluation=evaluation,
        )

    def _prepare_context(
        self, stage: str, output: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        """Prepare context variables for judge prompt based on stage."""
        context = {
            "stage_output": self._format_stage_output(output),
            "route_type": state.get("route_type") or "full_pipeline",
        }

        if stage == "Ask":
            context["original_question"] = state["original_question"]
            context["route_type"] = state.get("route_type") or "full_pipeline"

        elif stage == "Acquire":
            ebm_q = state.get("ebm_query")
            pico = state.get("pico_query")
            if ebm_q:
                context["ebm_query"] = json.dumps(
                    {
                        "query_type": ebm_q.query_type,
                        "patient": ebm_q.patient,
                        "primary_focus": ebm_q.primary_focus,
                        "outcome": ebm_q.outcome,
                        "keywords": ebm_q.keywords,
                        "comparator": ebm_q.comparator,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            elif pico:
                context["ebm_query"] = json.dumps(
                    {
                        "query_type": "pico",
                        "patient": pico.patient,
                        "primary_focus": pico.intervention,
                        "outcome": pico.outcome,
                        "keywords": pico.keywords,
                        "comparator": pico.comparison,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                context["ebm_query"] = "N/A"

            # Condense evidence list to avoid context overflow
            raw_output = output
            evidence_list = raw_output.get("evidence_list", [])
            condensed_evidence = []
            for i, e in enumerate(evidence_list):
                condensed_evidence.append(
                    {
                        "id": i + 1,
                        "title": e.title if hasattr(e, "title") else str(e),
                        "source": getattr(e, "source", ""),
                        "pmid": getattr(e, "pmid", ""),
                        "study_type": getattr(e, "study_type", "Unknown"),
                        "relevance_score": getattr(e, "relevance_score", 0.0),
                        # has_full_text and key_sentences let the Judge verify
                        # key_sentences_present without guessing from other fields.
                        "has_full_text": getattr(e, "has_full_text", False),
                        "has_key_sentences": bool(getattr(e, "key_sentences", None)),
                        "abstract_preview": (getattr(e, "abstract", "") or "")[:200],
                    }
                )
            # Truncate search_query: full Boolean PubMed queries are 500-1000+ chars,
            # but the Judge only needs to confirm the query is medically sensible (YES/NO).
            # 300 chars captures the core search intent without bloating the prompt.
            raw_search_query = raw_output.get("search_query", "") or ""
            context["stage_output"] = json.dumps(
                {
                    "search_query": raw_search_query[:300]
                    + ("..." if len(raw_search_query) > 300 else ""),
                    "total_results": raw_output.get("total_results", 0),
                    "selected_count": raw_output.get("selected_count", 0),
                    "study_type_distribution": raw_output.get(
                        "study_type_distribution", {}
                    ),
                    "evidence_list": condensed_evidence,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        elif stage == "Appraise":
            evidence_list = state.get("evidence_list", [])
            context["evidence_list"] = json.dumps(
                [
                    {
                        "title": e.title,
                        "source": e.source,
                        "pmid": e.pmid,
                        "relevance_score": e.relevance_score,
                        # pub_types is the authoritative study design field used by AppraiseAgent.
                        # Including it here lets the Judge verify study_type using the same
                        # source of truth, eliminating abstract-text vs metadata divergence.
                        "pub_types": getattr(e, "pub_types", None) or [],
                        "abstract": (getattr(e, "abstract", "") or "")[:300],
                    }
                    for e in evidence_list
                ],
                ensure_ascii=False,
                indent=2,
            )

            # Override stage_output: strip full abstracts from Evidence objects.
            # The Judge audits GRADE classification labels (study_type, risk_of_bias, etc.),
            # not the raw text — abstracts are shown via evidence_list above (truncated to 300 chars).
            # Removing full abstracts here cuts ~4000 redundant chars (~1000 tokens) from the Judge prompt.
            appraisal = output.get("appraisal_results")
            if appraisal and is_dataclass(appraisal):
                appraisal_d = asdict(appraisal)
                for ev in appraisal_d.get("evidence", []):
                    ev.pop("abstract", None)
                    ev.pop("full_text", None)
                    ev.pop("key_sentences", None)
            else:
                appraisal_d = appraisal
            context["stage_output"] = json.dumps(
                {
                    "appraisal_results": appraisal_d,
                    "grade_rationales": output.get("grade_rationales", []),
                    "numerical_confidence": output.get("numerical_confidence"),
                    "numerical_data": output.get("numerical_data"),
                    "bias_inconsistency": output.get("bias_inconsistency"),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        elif stage == "Apply":
            ebm_q = state.get("ebm_query")
            pico = state.get("pico_query")
            if ebm_q:
                context["query_description"] = (
                    f"{ebm_q.query_type}: {ebm_q.patient} / {ebm_q.primary_focus} / "
                    f"{ebm_q.comparator or 'N/A'} / {ebm_q.outcome}"
                )
            elif pico:
                context["query_description"] = (
                    f"pico: {pico.patient} / {pico.intervention} / "
                    f"{pico.comparison} / {pico.outcome}"
                )
            else:
                context["query_description"] = "N/A"

            appraisal = state.get("appraisal_results")
            if appraisal:
                # Include per-evidence grade breakdown so the Judge can verify
                # strength_matches_evidence using the same adopted-evidence view
                # that Apply Agent used (evidence_quality field), not just the
                # aggregate summary which hides which studies were excluded.
                grade_rationales = state.get("grade_rationales") or []
                grade_breakdown = [
                    {"title": r.get("title", ""), "computed_grade": r.get("computed_grade", "")}
                    for r in grade_rationales
                ]
                context["appraisal_results"] = json.dumps(
                    {
                        "evidence_count": len(appraisal.evidence),
                        "has_conflict": appraisal.has_conflict,
                        "summary": appraisal.summary,
                        "grade_breakdown": grade_breakdown,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                context["appraisal_results"] = "N/A"

        elif stage == "Assess":
            context["original_question"] = state["original_question"]
            context["route_confidence"] = state.get("route_confidence") or "N/A"

            ebm_q = state.get("ebm_query")
            pico = state.get("pico_query")
            if ebm_q:
                context["ebm_query_description"] = (
                    f"{ebm_q.query_type}: {ebm_q.patient} / {ebm_q.primary_focus} / "
                    f"{ebm_q.comparator or 'N/A'} / {ebm_q.outcome}"
                )
                context["pico_query"] = context["ebm_query_description"]
            elif pico:
                context["pico_query"] = (
                    f"{pico.patient} / {pico.intervention} / {pico.comparison} / {pico.outcome}"
                )
                context["ebm_query_description"] = context["pico_query"]
            else:
                context["pico_query"] = "N/A"
                context["ebm_query_description"] = "N/A"

            evidence_list = state.get("evidence_list", [])
            context["evidence_count"] = len(evidence_list)

            appraisal = state.get("appraisal_results")
            if appraisal:
                grade_dist: Dict[str, int] = {}
                for e in appraisal.evidence:
                    if e.grade_level:
                        grade_dist[e.grade_level] = grade_dist.get(e.grade_level, 0) + 1
                context["grade_distribution"] = json.dumps(
                    grade_dist, ensure_ascii=False
                )
            else:
                context["grade_distribution"] = "{}"

            rec = state.get("recommendation")
            if rec:
                context["recommendation"] = f"{rec.text} (强度: {rec.strength})"
            else:
                context["recommendation"] = "N/A"

        return context

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with heuristic error recovery.

        If standard parsing fails, falls back to stripping the 'reasoning'
        field (which may contain unescaped double-quote characters from Chinese
        text) and retrying.  The 'reasoning' field is only used for display;
        all scoring is driven by the structured audit fields, so dropping it
        is safe.
        """
        try:
            return robust_parse_json(response)
        except ValueError:
            # Extract raw JSON block
            if "```json" in response:
                s = response.find("```json") + 7
                e = response.find("```", s)
                raw = response[s:e].strip() if e > s else response
            else:
                s = response.find("{")
                e = response.rfind("}") + 1
                raw = response[s:e] if s >= 0 and e > s else response

            # Strip the 'reasoning' field, which is the last field and may
            # contain unescaped " characters that break JSON parsing.
            if '"reasoning"' in raw:
                pos = raw.rfind('"reasoning"')
                truncated = raw[:pos].rstrip().rstrip(",") + "\n}"
                try:
                    import json as _json

                    result = _json.loads(truncated)
                    result.setdefault(
                        "reasoning", "[解析回退：推理字段含非转义引号，已忽略]"
                    )
                    print(
                        "[WARN] Judge JSON parse fallback: stripped 'reasoning' field due to unescaped quotes."
                    )
                    return result
                except Exception:
                    pass
            raise
