import json
from typing import Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import asdict, is_dataclass
from src.state.schema import Observe, Evaluation, Issue, WorkflowState
from src.agents.base import robust_parse_json

# Dimension weights per stage (used by Python to compute weighted overall_score)
STAGE_WEIGHTS = {
    "Ask": {
        "pico_completeness": 0.35,
        "searchability": 0.35,
        "clarity": 0.30,
    },
    "Acquire": {
        "evidence_potency": 0.40,
        "evidence_hierarchy": 0.30,
        "pico_relevance": 0.30,
    },
    "Appraise": {
        "grade_reasonableness": 0.40,
        "conflict_identification": 0.30,
        "numerical_confidence": 0.30,
    },
    "Apply": {
        "evidence_alignment": 0.40,
        "strength_appropriateness": 0.35,
        "actionability": 0.25,
    },
    "Assess": {
        "answer_completeness": 0.35,
        "reasoning_chain": 0.35,
        "logical_consistency": 0.30,
    },
}

PASS_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# Per-stage Python scoring functions
# Each function takes the LLM audit dict and returns:
#   (dimension_scores, raw_issues, search_exhausted, reasoning_hint)
# ---------------------------------------------------------------------------

def _score_ask(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Ask audit classifications to dimension scores and issues."""
    issues: List[Dict] = []

    # --- Safety circuit breaker ---
    if audit.get("safety_audit", {}).get("intent_distorted") == "YES":
        return (
            {"pico_completeness": 0.0, "searchability": 0.0, "clarity": 0.0},
            [{
                "severity": "critical",
                "dimension": "pico_completeness",
                "description": (
                    "严重错误：PICO结构化结果扭曲了用户的原始意图。"
                    "请重新分析原问题，确保人群和干预措施与用户描述完全一致。"
                ),
            }],
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
            issues.append({
                "severity": "major",
                "dimension": "pico_completeness",
                "description": (
                    f"PICO中的 {pico_labels[element]} 要素描述模糊，"
                    "请在下次输出中提供更具体的描述（如具体疾病名称、干预剂量等）。"
                ),
            })
        elif val == "NO":
            severity = "critical" if element in ("P", "I", "O") else "major"
            issues.append({
                "severity": severity,
                "dimension": "pico_completeness",
                "description": (
                    f"PICO中缺失 {pico_labels[element]} 要素，"
                    "请在下次输出中补充完整。"
                ),
            })
    pico_completeness = sum(pico_scores) / 4

    # --- Searchability ---
    search_audit = audit.get("search_audit", {})
    binary_map = {"YES": 1.0, "NO": 0.0}
    kw_score = binary_map.get(search_audit.get("keywords_english_medical", "YES"), 1.0)
    exp_score = binary_map.get(search_audit.get("has_synonyms_or_mesh", "YES"), 1.0)
    logic_score = binary_map.get(search_audit.get("boolean_logic_valid", "YES"), 1.0)
    searchability = (kw_score + exp_score + logic_score) / 3

    if search_audit.get("keywords_english_medical") == "NO":
        issues.append({
            "severity": "major",
            "dimension": "searchability",
            "description": (
                "关键词必须转化为标准的英文医学术语（MeSH），"
                "请勿使用中文或口语化词汇。"
            ),
        })
    if search_audit.get("has_synonyms_or_mesh") == "NO":
        issues.append({
            "severity": "minor",
            "dimension": "searchability",
            "description": (
                "缺少同义词扩展，请为核心概念补充MeSH词或常见别名"
                "（如 'heart failure' OR 'cardiac failure'）。"
            ),
        })
    if search_audit.get("boolean_logic_valid") == "NO":
        issues.append({
            "severity": "major",
            "dimension": "searchability",
            "description": "布尔逻辑（AND/OR）使用错误，请检查检索策略的逻辑结构。",
        })

    # --- Clarity ---
    clarity_audit = audit.get("clarity_audit", {})
    clarity_map = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0.1}
    clarity_val = clarity_audit.get("pico_statement_unambiguous", "YES")
    clarity = clarity_map.get(clarity_val, 1.0)
    if clarity_val == "PARTIAL":
        issues.append({
            "severity": "minor",
            "dimension": "clarity",
            "description": "PICO表述存在轻微歧义，请澄清不明确的术语或条件。",
        })
    elif clarity_val == "NO":
        issues.append({
            "severity": "major",
            "dimension": "clarity",
            "description": "PICO表述存在严重歧义，请重新提炼问题，确保表述无歧义。",
        })

    dimension_scores = {
        "pico_completeness": pico_completeness,
        "searchability": searchability,
        "clarity": clarity,
    }
    return dimension_scores, issues, False, audit.get("reasoning", "")


def _score_acquire(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Acquire audit classifications to dimension scores and issues."""
    issues: List[Dict] = []
    search_audit = audit.get("search_audit", {})
    evidence_audit = audit.get("evidence_audit", {})
    search_exhausted = bool(audit.get("search_exhausted", False))

    # --- Invalid search terms: circuit breaker ---
    if search_audit.get("search_terms_valid") == "NO":
        issues.append({
            "severity": "critical",
            "dimension": "evidence_potency",
            "description": (
                "检索词构建有误，检索方向完全错误。"
                "请根据PICO重新设计检索策略，使用正确的英文医学术语（MeSH词）。"
            ),
        })
        return (
            {"evidence_potency": 0.0, "evidence_hierarchy": 0.0, "pico_relevance": 0.0},
            issues,
            False,
            "检索词严重错误，无法获取有效证据。",
        )

    # --- Evidence hierarchy ---
    type_scores = {
        "SR_META": 1.0,
        "RCT": 0.80,
        "COHORT": 0.55,
        "CASE_CONTROL": 0.35,
        "CASE_REPORT": 0.15,
        "NONE": 0.0,
    }
    best_type = evidence_audit.get("best_study_type", "NONE")
    evidence_hierarchy = type_scores.get(best_type, 0.0)

    # --- Evidence potency = hierarchy × ability to answer PICO ---
    answers_map = {"YES": 1.0, "PARTIAL": 0.6, "NO": 0.2}
    answers_val = evidence_audit.get("best_evidence_answers_pico", "NO")
    evidence_potency = evidence_hierarchy * answers_map.get(answers_val, 0.2)

    # --- PICO relevance = average of P / I / O match ---
    pico_match_map = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0.0}
    p_score = pico_match_map.get(evidence_audit.get("pico_p_match", "NO"), 0.0)
    i_score = pico_match_map.get(evidence_audit.get("pico_i_match", "NO"), 0.0)
    o_score = pico_match_map.get(evidence_audit.get("pico_o_match", "NO"), 0.0)
    pico_relevance = (p_score + i_score + o_score) / 3

    # --- Issue generation ---
    if best_type == "NONE" and not search_exhausted:
        # Reaching here means search_terms_valid=YES (circuit breaker already returned for NO).
        # NONE results with valid terms = API/network error or genuinely empty literature.
        # Use "major" (not "critical") and advise retrying with same terms.
        issues.append({
            "severity": "major",
            "dimension": "evidence_potency",
            "description": (
                "检索返回零结果，但检索词已确认有效（可能是API网络错误或临时故障）。"
                "请保持原检索词直接重试，不要改变搜索策略。"
            ),
        })
    elif best_type == "CASE_REPORT":
        issues.append({
            "severity": "major",
            "dimension": "evidence_hierarchy",
            "description": (
                f"找到的最高质量证据仅为病例报告（{best_type}）。"
                "建议尝试更宽泛或不同的检索词以寻找更高层级的证据（RCT或SR）。"
            ),
        })

    if answers_val == "NO" and not search_exhausted:
        issues.append({
            "severity": "major",
            "dimension": "evidence_potency",
            "description": (
                "现有最佳证据无法直接回答PICO临床问题，"
                "请调整检索策略以找到更直接相关的证据。"
            ),
        })

    pico_match_labels = {
        "pico_p_match": "Patient人群",
        "pico_i_match": "Intervention干预",
        "pico_o_match": "Outcome结局",
    }
    for key, label in pico_match_labels.items():
        val = evidence_audit.get(key, "YES")
        if val == "NO":
            issues.append({
                "severity": "major",
                "dimension": "pico_relevance",
                "description": (
                    f"证据与PICO的 {label} 严重不匹配，"
                    "请调整检索词以找到更匹配的证据。"
                ),
            })
        elif val == "PARTIAL":
            issues.append({
                "severity": "minor",
                "dimension": "pico_relevance",
                "description": (
                    f"证据与PICO的 {label} 存在间接性，"
                    "请在后续评价阶段注意外推限制。"
                ),
            })

    # --- Listwise selection quality ---
    # Mapped onto existing dimensions: selection order → evidence_potency adjustment;
    # selection count → evidence_hierarchy adjustment.
    listwise_audit = audit.get("listwise_audit", {})
    top_sel_val = listwise_audit.get("top_selection_appropriate", "YES")
    count_val = listwise_audit.get("selection_count_appropriate", "YES")

    listwise_map = {"YES": 0.0, "PARTIAL": -0.05, "NO": -0.15}
    evidence_potency = max(0.0, evidence_potency + listwise_map.get(top_sel_val, 0.0))
    evidence_hierarchy = max(0.0, evidence_hierarchy + listwise_map.get(count_val, 0.0))

    if top_sel_val == "NO":
        issues.append({
            "severity": "major",
            "dimension": "evidence_potency",
            "description": (
                "Listwise排序结果不合理：排名靠前的文献并非最优证据，"
                "或纳入了明显不相关的文献。请重新审视选择策略。"
            ),
        })
    elif top_sel_val == "PARTIAL":
        issues.append({
            "severity": "minor",
            "dimension": "evidence_potency",
            "description": "Listwise排名顺序有轻微偏差，个别文献的排名位置有待优化。",
        })

    if count_val == "NO":
        issues.append({
            "severity": "major",
            "dimension": "evidence_hierarchy",
            "description": (
                "选择数量明显不合理（有效候选很多却仅选极少篇，或质量差仍凑满10篇），"
                "请重新调整Listwise筛选标准。"
            ),
        })

    dimension_scores = {
        "evidence_potency": evidence_potency,
        "evidence_hierarchy": evidence_hierarchy,
        "pico_relevance": pico_relevance,
    }
    return dimension_scores, issues, search_exhausted, audit.get("reasoning", "")


def _score_appraise(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """
    Convert Appraise audit classifications to dimension scores and issues.

    The judge now evaluates the Appraise Agent's structured output which
    contains explicit GRADE factor classifications (study_type, risk_of_bias,
    etc.) and Python-computed grades.  The audit fields reflect this:
      - grade_audit.study_type_correct: was study type identified correctly?
      - grade_audit.downgrade_factors_appropriate: were factor labels reasonable?
      - grade_audit.computed_grade_reasonable: does the final grade make sense?
    """
    issues: List[Dict] = []
    grade_audit = audit.get("grade_audit", {})
    conflict_audit = audit.get("conflict_audit", {})
    data_audit = audit.get("data_audit", {})

    # --- grade_reasonableness ---
    # 30% study_type correctness + 30% downgrade factor quality + 40% computed grade
    type_map = {"YES": 1.0, "PARTIAL": 0.70, "NO": 0.0}
    factor_map = {"YES": 1.0, "PARTIAL": 0.60, "NO": 0.15}
    grade_map = {"YES": 1.0, "PARTIAL": 0.65, "NO": 0.10}

    type_val = grade_audit.get("study_type_correct", "YES")
    factor_val = grade_audit.get("downgrade_factors_appropriate", "YES")
    grade_val = grade_audit.get("computed_grade_reasonable", "YES")

    grade_reasonableness = (
        0.30 * type_map.get(type_val, 1.0)
        + 0.30 * factor_map.get(factor_val, 1.0)
        + 0.40 * grade_map.get(grade_val, 1.0)
    )

    if type_val == "NO":
        issues.append({
            "severity": "critical",
            "dimension": "grade_reasonableness",
            "description": (
                "研究类型（study_type）分类存在明显错误，导致GRADE初始等级错误。"
                "请重新识别每篇研究的设计类型：RCT / COHORT / CASE_CONTROL / CASE_REPORT。"
            ),
        })
    elif type_val == "PARTIAL":
        issues.append({
            "severity": "major",
            "dimension": "grade_reasonableness",
            "description": "部分研究的类型识别有误，请复查并修正错误的study_type标签。",
        })

    if factor_val == "NO":
        issues.append({
            "severity": "major",
            "dimension": "grade_reasonableness",
            "description": (
                "GRADE降级因素评估存在明显错误（如将未盲法RCT标记为NOT_SERIOUS偏倚风险）。"
                "请重新评估各降级因素（risk_of_bias、inconsistency、indirectness、imprecision）。"
            ),
        })
    elif factor_val == "PARTIAL":
        issues.append({
            "severity": "minor",
            "dimension": "grade_reasonableness",
            "description": "个别降级因素的严重程度评估过于宽松或严苛，请复查相关分类依据。",
        })

    if grade_val == "NO":
        issues.append({
            "severity": "critical",
            "dimension": "grade_reasonableness",
            "description": (
                "系统计算出的最终GRADE等级（computed_grade）明显不合理，"
                "根本原因通常是study_type或降级因素分类错误。请修正上游分类标签。"
            ),
        })
    elif grade_val == "PARTIAL":
        issues.append({
            "severity": "minor",
            "dimension": "grade_reasonableness",
            "description": "个别研究的计算等级与预期有轻微偏差，可接受但建议核查分类标签。",
        })

    # --- conflict_identification ---
    conflicts_exist = conflict_audit.get("conflicts_exist", "NO")
    conflicts_id_val = conflict_audit.get("conflicts_identified", "NA")

    if conflicts_exist == "NO":
        conflict_identification = 1.0  # Correctly assessed no conflict
    else:
        conflict_id_map = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0.0, "NA": 1.0}
        conflict_identification = conflict_id_map.get(conflicts_id_val, 0.0)
        if conflicts_id_val == "NO":
            issues.append({
                "severity": "major",
                "dimension": "conflict_identification",
                "description": (
                    "证据间存在实质性冲突但未被识别，"
                    "请重新比较各研究的结论方向并分析冲突原因。"
                ),
            })
        elif conflicts_id_val == "PARTIAL":
            issues.append({
                "severity": "minor",
                "dimension": "conflict_identification",
                "description": "证据冲突识别不完整，conflict_description需补充遗漏的冲突说明。",
            })

    # --- numerical_confidence ---
    # data_score: did the agent correctly assess what data is available?
    data_map = {"YES": 1.0, "PARTIAL": 0.65, "NO": 0.1, "NA": 0.85}
    data_val = data_audit.get("numerical_data_extracted", "PARTIAL")
    data_score = data_map.get(data_val, 0.65)

    # confidence_accuracy: was the confidence_level label itself appropriate?
    # HIGH = accurate label (no over/under-confidence), VERY_LOW = serious mismatch
    confidence_accuracy_map = {"HIGH": 1.0, "MODERATE": 0.75, "LOW": 0.35, "VERY_LOW": 0.10}
    conf_acc_val = data_audit.get("confidence_level_appropriate", "MODERATE")
    confidence_accuracy = confidence_accuracy_map.get(conf_acc_val, 0.75)

    numerical_confidence = 0.5 * data_score + 0.5 * confidence_accuracy

    if data_val == "NO":
        issues.append({
            "severity": "major",
            "dimension": "numerical_confidence",
            "description": (
                "摘要中存在数值数据但未被提取或评估，"
                "请补充提取关键数值指标（效应量、置信区间、P值等）。"
            ),
        })
    if conf_acc_val == "LOW":
        issues.append({
            "severity": "major",
            "dimension": "numerical_confidence",
            "description": (
                "置信度标签评估过高（实际数值不可靠），"
                "请下调confidence_level并在推荐中标注数值的不确定性。"
            ),
        })
    elif conf_acc_val == "VERY_LOW":
        issues.append({
            "severity": "major",
            "dimension": "numerical_confidence",
            "description": (
                "置信度标签与实际数据质量严重不符，"
                "请重新评估数值可靠性，必要时请求人工审核。"
            ),
        })

    dimension_scores = {
        "grade_reasonableness": grade_reasonableness,
        "conflict_identification": conflict_identification,
        "numerical_confidence": numerical_confidence,
    }
    return dimension_scores, issues, False, audit.get("reasoning", "")


def _score_apply(audit: Dict) -> Tuple[Dict[str, float], List[Dict], bool, str]:
    """Convert Apply audit classifications to dimension scores and issues."""
    issues: List[Dict] = []
    grounding_audit = audit.get("grounding_audit", {})
    strength_audit = audit.get("strength_audit", {})
    actionability_audit = audit.get("actionability_audit", {})

    # --- evidence_alignment ---
    grounding_map = {"YES": 1.0, "PARTIAL": 0.55, "NO": 0.1}
    rec_based_val = grounding_audit.get("recommendation_based_on_evidence", "YES")
    uses_external_val = grounding_audit.get("uses_external_knowledge", "NO")

    base_alignment = grounding_map.get(rec_based_val, 1.0)
    external_penalty = 0.25 if uses_external_val == "YES" else 0.0
    evidence_alignment = max(0.0, base_alignment - external_penalty)

    if rec_based_val == "NO":
        issues.append({
            "severity": "critical",
            "dimension": "evidence_alignment",
            "description": (
                "推荐与提供的证据无关或方向相反，"
                "请严格基于本次检索的证据重新生成推荐，不得引入外部知识。"
            ),
        })
    elif rec_based_val == "PARTIAL":
        issues.append({
            "severity": "major",
            "dimension": "evidence_alignment",
            "description": (
                "推荐部分超出证据范围，请移除未有本次检索证据支持的推断内容。"
            ),
        })
    if uses_external_val == "YES":
        issues.append({
            "severity": "major",
            "dimension": "evidence_alignment",
            "description": (
                "检测到使用了外部知识（如'通常认为'、'临床经验'）替代证据，"
                "请仅基于本次提供的证据列表生成推荐。"
            ),
        })

    # --- strength_appropriateness ---
    insuf_val = strength_audit.get("insufficient_evidence_appropriate", "NA")
    if insuf_val == "YES":
        strength_appropriateness = 1.0
    elif insuf_val == "NO":
        strength_appropriateness = 0.15
        issues.append({
            "severity": "critical",
            "dimension": "strength_appropriateness",
            "description": (
                "证据充足但错误输出了'证据不足'声明，"
                "请根据现有证据质量给出对应强度的推荐。"
            ),
        })
    else:  # NA — a normal recommendation was produced
        strength_map = {"YES": 1.0, "MINOR_MISMATCH": 0.65, "MAJOR_MISMATCH": 0.15}
        strength_val = strength_audit.get("strength_matches_evidence_quality", "YES")
        strength_appropriateness = strength_map.get(strength_val, 1.0)
        if strength_val == "MAJOR_MISMATCH":
            issues.append({
                "severity": "critical",
                "dimension": "strength_appropriateness",
                "description": (
                    "推荐强度与证据质量严重不符（如Very Low证据给出Strong推荐），"
                    "请依据GRADE原则重新确定推荐强度：Very Low→Weak或证据不足；"
                    "Low→Weak；Moderate→Conditional/Moderate；High→Strong。"
                ),
            })
        elif strength_val == "MINOR_MISMATCH":
            issues.append({
                "severity": "major",
                "dimension": "strength_appropriateness",
                "description": (
                    "推荐强度与证据质量存在轻微不符，"
                    "请检查证据质量等级与推荐强度是否严格匹配。"
                ),
            })

    # --- actionability ---
    specific_map = {"YES": 1.0, "PARTIAL": 0.6, "NO": 0.1}
    caveats_map = {"YES": 1.0, "PARTIAL": 0.6, "NO": 0.2, "NA": 1.0}
    specific_val = actionability_audit.get("recommendation_specific", "YES")
    caveats_val = actionability_audit.get("caveats_documented", "NA")
    actionability = (
        0.6 * specific_map.get(specific_val, 1.0)
        + 0.4 * caveats_map.get(caveats_val, 1.0)
    )

    if specific_val == "NO":
        issues.append({
            "severity": "major",
            "dimension": "actionability",
            "description": (
                "推荐过于模糊，临床医生无法据此执行，"
                "请提供更具体的推荐内容（如适应症、用药剂量、疗程等关键参数）。"
            ),
        })
    elif specific_val == "PARTIAL":
        issues.append({
            "severity": "minor",
            "dimension": "actionability",
            "description": "推荐可以更加具体，请补充关键临床细节以提高可操作性。",
        })
    if caveats_val == "NO":
        issues.append({
            "severity": "minor",
            "dimension": "actionability",
            "description": (
                "存在重要的适用性限制或PICO不匹配未在caveats中说明，"
                "请补充相关注意事项。"
            ),
        })
    elif caveats_val == "PARTIAL":
        issues.append({
            "severity": "minor",
            "dimension": "actionability",
            "description": "caveats中部分重要限制未说明，请补充完整。",
        })

    dimension_scores = {
        "evidence_alignment": evidence_alignment,
        "strength_appropriateness": strength_appropriateness,
        "actionability": actionability,
    }
    return dimension_scores, issues, False, audit.get("reasoning", "")


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
    answer_completeness = (
        0.7 * answered_map.get(answered_val, 1.0)
        + 0.3 * limitations_map.get(limitations_val, 1.0)
    )

    if answered_val == "NO":
        issues.append({
            "severity": "critical",
            "dimension": "answer_completeness",
            "description": (
                "完全未回答原始临床问题，"
                "请检查整个推理链是否与原始问题对齐，必要时回退Ask阶段。"
            ),
        })
    elif answered_val == "PARTIAL":
        issues.append({
            "severity": "major",
            "dimension": "answer_completeness",
            "description": (
                "原始问题未被完整回答，请检查遗漏的方面并补充说明。"
            ),
        })
    if limitations_val == "NO":
        issues.append({
            "severity": "minor",
            "dimension": "answer_completeness",
            "description": (
                "未说明证据局限性，请在最终输出中明确标注证据的适用范围和不确定性。"
            ),
        })

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
        (ask_acquire_val, "Ask→Acquire", "检索策略与PICO脱节，建议回退Ask阶段重新构建检索策略。"),
        (acquire_appraise_val, "Acquire→Appraise", "证据评价与检索结果不一致，建议回退Appraise阶段。"),
        (appraise_apply_val, "Appraise→Apply", "推荐强度与证据评价不一致，建议回退Apply阶段。"),
    ]
    for val, link_name, broken_desc in chain_issues:
        if val == "BROKEN":
            issues.append({
                "severity": "major",
                "dimension": "reasoning_chain",
                "description": f"推理链断裂（{link_name}）：{broken_desc}",
            })
        elif val == "WEAK":
            issues.append({
                "severity": "minor",
                "dimension": "reasoning_chain",
                "description": f"推理链薄弱（{link_name}）：连接关系不够清晰，请加强各阶段的逻辑衔接。",
            })

    # --- logical_consistency ---
    consistency_map = {"YES": 1.0, "MINOR_ISSUE": 0.65, "MAJOR_CONTRADICTION": 0.1}
    grade_strength_val = consistency_audit.get("grade_to_strength_consistent", "YES")
    no_contradictions_val = consistency_audit.get("no_internal_contradictions", "YES")
    logical_consistency = (
        0.5 * consistency_map.get(grade_strength_val, 1.0)
        + 0.5 * consistency_map.get(no_contradictions_val, 1.0)
    )

    if grade_strength_val == "MAJOR_CONTRADICTION":
        issues.append({
            "severity": "critical",
            "dimension": "logical_consistency",
            "description": (
                "证据质量与推荐强度存在根本性矛盾（如Very Low证据→Strong推荐），"
                "建议回退Apply阶段修正推荐强度。"
            ),
        })
    elif grade_strength_val == "MINOR_ISSUE":
        issues.append({
            "severity": "minor",
            "dimension": "logical_consistency",
            "description": "证据质量与推荐强度存在轻微不协调，请检查Apply阶段的强度设定。",
        })

    if no_contradictions_val == "MAJOR_CONTRADICTION":
        issues.append({
            "severity": "major",
            "dimension": "logical_consistency",
            "description": (
                "推理链内部存在重大矛盾（如不同阶段的人群/干预/结论方向不一致），"
                "请检查各阶段输出是否相互支撑。"
            ),
        })
    elif no_contradictions_val == "MINOR_ISSUE":
        issues.append({
            "severity": "minor",
            "dimension": "logical_consistency",
            "description": "推理链内部存在轻微不一致，可接受但建议进一步完善。",
        })

    dimension_scores = {
        "answer_completeness": answer_completeness,
        "reasoning_chain": reasoning_chain,
        "logical_consistency": logical_consistency,
    }
    return dimension_scores, issues, False, audit.get("reasoning", "")


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
        return json.dumps(serializable_output, ensure_ascii=False, indent=2, default=str)

    def _calculate_overall_score(self, stage: str, dimension_scores: Dict[str, float]) -> float:
        """Calculate weighted overall score from dimension scores."""
        weights = STAGE_WEIGHTS.get(stage, {})
        if not weights:
            return sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 0.0
        total = 0.0
        weight_sum = 0.0
        for dim, weight in weights.items():
            total += dimension_scores.get(dim, 0.0) * weight
            weight_sum += weight
        return total / weight_sum if weight_sum > 0 else 0.0

    def _has_critical_issue(self, issues: List) -> bool:
        """Return True if any issue has critical severity."""
        return any(
            (issue.severity if hasattr(issue, "severity") else issue.get("severity")) == "critical"
            for issue in issues
        )

    def evaluate_stage(self, stage: str, output: Dict[str, Any], state: WorkflowState) -> Observe:
        """
        Evaluate a stage's output and return a structured Observe.

        Steps:
          1. Build prompt with stage-specific context.
          2. Call LLM → receives classification audit JSON (no scores).
          3. Run Python scorer → converts classifications to dimension_scores + issues.
          4. Compute weighted overall_score and pass_threshold in Python.
          5. Return Observe.
        """
        from src.state.schema import Issue as IssueSchema, Evaluation, Observe as ObserveSchema

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

        pass_threshold = overall_score >= PASS_THRESHOLD and not self._has_critical_issue(issues)

        summary = reasoning_hint if reasoning_hint else f"综合评分: {overall_score:.2f}"

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

    def _prepare_context(self, stage: str, output: Dict[str, Any], state: WorkflowState) -> Dict[str, Any]:
        """Prepare context variables for judge prompt based on stage."""
        context = {
            "stage_output": self._format_stage_output(output)
        }

        if stage == "Ask":
            context["original_question"] = state["original_question"]

        elif stage == "Acquire":
            pico = state.get("pico_query")
            if pico:
                context["pico_query"] = json.dumps({
                    "patient": pico.patient,
                    "intervention": pico.intervention,
                    "comparison": pico.comparison,
                    "outcome": pico.outcome,
                    "keywords": pico.keywords,
                }, ensure_ascii=False, indent=2)
            else:
                context["pico_query"] = "N/A"

            # Condense evidence list to avoid context overflow
            raw_output = output
            evidence_list = raw_output.get("evidence_list", [])
            condensed_evidence = []
            for i, e in enumerate(evidence_list):
                condensed_evidence.append({
                    "id": i + 1,
                    "title": e.title if hasattr(e, "title") else str(e),
                    "source": getattr(e, "source", ""),
                    "pmid": getattr(e, "pmid", ""),
                    "study_type": getattr(e, "study_type", "Unknown"),
                    "relevance_score": getattr(e, "relevance_score", 0.0),
                    "abstract_preview": (getattr(e, "abstract", "") or "")[:200],
                })
            # Truncate search_query: full Boolean PubMed queries are 500-1000+ chars,
            # but the Judge only needs to confirm the query is medically sensible (YES/NO).
            # 300 chars captures the core search intent without bloating the prompt.
            raw_search_query = raw_output.get("search_query", "") or ""
            context["stage_output"] = json.dumps({
                "search_query": raw_search_query[:300] + ("..." if len(raw_search_query) > 300 else ""),
                "total_results": raw_output.get("total_results", 0),
                "selected_count": raw_output.get("selected_count", 0),
                "study_type_distribution": raw_output.get("study_type_distribution", {}),
                "evidence_list": condensed_evidence,
            }, ensure_ascii=False, indent=2, default=str)

        elif stage == "Appraise":
            evidence_list = state.get("evidence_list", [])
            context["evidence_list"] = json.dumps([
                {
                    "title": e.title,
                    "source": e.source,
                    "pmid": e.pmid,
                    "relevance_score": e.relevance_score,
                }
                for e in evidence_list
            ], ensure_ascii=False, indent=2)

            # Override stage_output: strip full abstracts from Evidence objects.
            # The Judge audits GRADE classification labels (study_type, risk_of_bias, etc.),
            # not the raw text — abstracts are already shown via evidence_list above.
            # Removing them cuts ~4000 redundant chars (~1000 tokens) from the Judge prompt.
            appraisal = output.get("appraisal_results")
            if appraisal and is_dataclass(appraisal):
                appraisal_d = asdict(appraisal)
                for ev in appraisal_d.get("evidence", []):
                    ev.pop("abstract", None)
            else:
                appraisal_d = appraisal
            context["stage_output"] = json.dumps({
                "appraisal_results": appraisal_d,
                "grade_rationales": output.get("grade_rationales", []),
                "numerical_confidence": output.get("numerical_confidence"),
                "numerical_data": output.get("numerical_data"),
                "bias_inconsistency": output.get("bias_inconsistency"),
            }, ensure_ascii=False, indent=2, default=str)

        elif stage == "Apply":
            pico = state.get("pico_query")
            if pico:
                context["pico_query"] = json.dumps({
                    "patient": pico.patient,
                    "intervention": pico.intervention,
                    "comparison": pico.comparison,
                    "outcome": pico.outcome,
                }, ensure_ascii=False, indent=2)
            else:
                context["pico_query"] = "N/A"

            appraisal = state.get("appraisal_results")
            if appraisal:
                context["appraisal_results"] = json.dumps({
                    "evidence_count": len(appraisal.evidence),
                    "has_conflict": appraisal.has_conflict,
                    "summary": appraisal.summary,
                }, ensure_ascii=False, indent=2)
            else:
                context["appraisal_results"] = "N/A"

        elif stage == "Assess":
            context["original_question"] = state["original_question"]

            pico = state.get("pico_query")
            if pico:
                context["pico_query"] = (
                    f"{pico.patient} / {pico.intervention} / {pico.comparison} / {pico.outcome}"
                )
            else:
                context["pico_query"] = "N/A"

            evidence_list = state.get("evidence_list", [])
            context["evidence_count"] = len(evidence_list)

            appraisal = state.get("appraisal_results")
            if appraisal:
                grade_dist: Dict[str, int] = {}
                for e in appraisal.evidence:
                    if e.grade_level:
                        grade_dist[e.grade_level] = grade_dist.get(e.grade_level, 0) + 1
                context["grade_distribution"] = json.dumps(grade_dist, ensure_ascii=False)
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
                    result.setdefault("reasoning", "[解析回退：推理字段含非转义引号，已忽略]")
                    print("[WARN] Judge JSON parse fallback: stripped 'reasoning' field due to unescaped quotes.")
                    return result
                except Exception:
                    pass
            raise
