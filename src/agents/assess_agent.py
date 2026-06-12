from typing import List, Dict, Any
from pathlib import Path
import re
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, Assessment

_OVERSTATEMENT_RE = re.compile(
    r"首选|优于|明显优于|应当首选|更优|显著优于|推荐.{0,6}而非|应优先选择"
)
_NO_DIFF_RE = re.compile(r"无显著差异|无明确优劣|不良反应谱方面无明确")
_NO_DATA_RE = re.compile(r"无直接|未测量|未报告|无头对头|无.*?直接比较数据")

# --- 7-Dimension Scoring Configuration (评价标准.md) ---
# Each dimension maps to its maximum point value; total = 100.

DIMENSION_MAX_POINTS = {
    "medical_accuracy": 20,
    "evidence_quality": 20,
    "relevance": 10,
    "safety_risk_control": 20,
    "individualization": 10,
    "clarity_actionability": 10,
    "uncertainty_boundary": 10,
}

SAFETY_A_CAP = 0.40  # Category A: cap at 40/100 (normalized)
SAFETY_B_CAP = 0.60  # Category B: cap at 60/100 (normalized)

CRITICAL_BOTTOM_THRESHOLDS = {
    "medical_accuracy": 4,
    "safety_risk_control": 4,
    "evidence_quality": 4,
}


class AssessAgent(BaseAgent):
    """Agent for assessing recommendation quality using 7-dimension rubric."""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Assess")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = (
            Path(__file__).parent.parent / "config" / "prompts" / "assess_agent.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        return robust_parse_json(content)

    def _compute_quality_score(self, assess_dict: dict) -> float:
        """Compute quality score from 7-dimension rubric, normalized to 0.0-1.0."""
        dim_scores = assess_dict.get("dim_scores", {})
        total = 0.0
        for dim, max_pts in DIMENSION_MAX_POINTS.items():
            raw = dim_scores.get(dim, max_pts * 0.5)
            if isinstance(raw, str):
                try:
                    raw = float(raw)
                except ValueError:
                    raw = max_pts * 0.5
            raw = max(0, min(raw, max_pts))
            total += raw

        safety_cat = assess_dict.get("safety_category", "NONE")
        if safety_cat == "A":
            total = min(total, 40)
        elif safety_cat == "B":
            total = min(total, 60)

        return round(total / 100.0, 2)

    def _check_critical_backtrack(self, assess_dict: dict) -> bool:
        """Check if any critical dimension is in the bottom tier or safety Category A."""
        dim_scores = assess_dict.get("dim_scores", {})
        for dim, threshold in CRITICAL_BOTTOM_THRESHOLDS.items():
            val = dim_scores.get(dim)
            if val is not None:
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    continue
                if val <= threshold:
                    return True
        if assess_dict.get("safety_category") == "A":
            return True
        return False

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Assess agent to evaluate recommendation quality."""
        recommendation = state.get("recommendation")
        if not recommendation:
            raise ValueError("No recommendation found in state")

        question = state["original_question"]

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = f"Previous attempt failed: {state['backtrack_reason']}\nPlease address these issues in your assessment."

        prompt = self.prompt_template.format(
            question=question,
            recommendation_text=recommendation.text,
            strength=recommendation.strength,
            evidence_quality=recommendation.evidence_quality,
            rationale=recommendation.rationale,
            backtrack_context=backtrack_context,
        )

        response = self.llm.invoke(prompt)
        assess_dict = self._parse_json(response.content)

        # --- Compute quality score from 7 dimensions ---
        quality_score = self._compute_quality_score(assess_dict)

        # Gaps-based cap
        if assess_dict.get("gaps") and quality_score > 0.95:
            quality_score = 0.95

        # Extract dimension scores and justifications
        dim_scores_raw = assess_dict.get("dim_scores", {})
        dimension_scores = {}
        for dim in DIMENSION_MAX_POINTS:
            val = dim_scores_raw.get(dim)
            if val is not None:
                dimension_scores[dim] = str(val)

        dimension_justifications = assess_dict.get("dimension_justifications", {})

        # Determine backtrack need
        needs_backtrack = assess_dict.get("needs_backtrack", False)
        if not needs_backtrack and self._check_critical_backtrack(assess_dict):
            needs_backtrack = True

        # Auto-generate backtrack reason from critical dimensions
        backtrack_reason = assess_dict.get("backtrack_reason")
        if needs_backtrack and not backtrack_reason:
            critical_fails = []
            for dim, threshold in CRITICAL_BOTTOM_THRESHOLDS.items():
                val = dim_scores_raw.get(dim)
                if val is not None:
                    try:
                        if float(val) <= threshold:
                            justification = dimension_justifications.get(dim, dim)
                            critical_fails.append(f"{dim}={val}: {justification}")
                    except (ValueError, TypeError):
                        pass
            safety_cat = assess_dict.get("safety_category", "NONE")
            if safety_cat == "A":
                violations = assess_dict.get("safety_violations", [])
                critical_fails.append(
                    f"安全A类违规: {'; '.join(violations) if violations else '存在直接不合格项'}"
                )
            backtrack_reason = f"关键维度未达标：{'；'.join(critical_fails)}" if critical_fails else "评分未通过充分性判断"

        # Map safety category B to backtrack when combined with low score
        safety_cat = assess_dict.get("safety_category", "NONE")
        if safety_cat == "B" and quality_score <= SAFETY_B_CAP and not needs_backtrack:
            needs_backtrack = True
            violations = assess_dict.get("safety_violations", [])
            backtrack_reason = (
                f"安全性缺陷（B类）：{'; '.join(violations) if violations else '存在严重扣分项'}。"
                "推荐存在重大安全隐患，建议回退修正。"
            )

        assessment = Assessment(
            quality_score=quality_score,
            gaps=assess_dict.get("gaps", []),
            needs_backtrack=needs_backtrack,
            backtrack_reason=backtrack_reason,
            dimension_scores=dimension_scores,
            dimension_justifications=dimension_justifications,
        )

        # ═══════════════════════════════════════════════════════════════════
        # HARD GATES (preserved — safety mechanisms)
        # ═══════════════════════════════════════════════════════════════════

        result: Dict[str, Any] = {"assessment": assessment}

        # --- Gate 1: Strong recommendation with low quality score → downgrade ---
        if recommendation.strength == "Strong" and quality_score < 0.70:
            downgraded = recommendation.model_copy(update={
                "strength": "Conditional",
                "caveats": list(recommendation.caveats) + [
                    f"Strength 已由 Strong 自动下调为 Conditional：Assess quality_score={quality_score*100:.0f}/100 < 70，"
                    "审计发现多个维度存在不足，不满足 Strong 推荐的硬门槛。"
                ],
            }) if hasattr(recommendation, "model_copy") else recommendation
            if not hasattr(recommendation, "model_copy"):
                downgraded.strength = "Conditional"
                downgraded.caveats = list(recommendation.caveats) + [
                    f"Strength 已由 Strong 自动下调为 Conditional：Assess quality_score={quality_score*100:.0f}/100 < 70。"
                ]
            print(
                f"[GRADE-CLAMP] Strong → Conditional: quality_score={quality_score*100:.0f}/100 < 70."
            )
            result["recommendation"] = downgraded

        # --- Gate 2: Overly conservative detection ---
        elif (recommendation.strength in ("Insufficient Evidence", "No Recommendation")
              and float(dim_scores_raw.get("evidence_quality", 0)) >= 14):
            flagged = recommendation.model_copy(update={
                "caveats": list(recommendation.caveats) + [
                    "【Assess 审计】：当前输出为'证据不足'，但 Assess 审计判断证据质量评分尚可（≥14/20），"
                    "按循证原则本应给出 Conditional 推荐。"
                    "建议人工复核是否存在 Apply 阶段过于保守的问题。"
                ],
            }) if hasattr(recommendation, "model_copy") else recommendation
            print(
                f"[GRADE-FLAG] Insufficient Evidence flagged: evidence_quality dim={dim_scores_raw.get('evidence_quality')}>=14."
            )
            result["recommendation"] = flagged

        # --- Gate 3: Overstatement hard stop ---
        rec_to_check = result.get("recommendation", recommendation)
        has_core_direct = getattr(rec_to_check, "has_core_direct", False)
        overstatement_match = _OVERSTATEMENT_RE.search(rec_to_check.text)

        if overstatement_match and not has_core_direct:
            matched_term = overstatement_match.group()
            assessment.needs_backtrack = True
            assessment.backtrack_reason = (
                f"Assess 硬门槛：推荐文本包含优越性用语「{matched_term}」，"
                "但所有证据均为间接证据（无 core_direct），"
                "请使用均衡表述（如「均可作为一线选择」）重新生成推荐。"
            )
            assessment.gaps.append(
                f"检测到过强措辞「{matched_term}」且无直接头对头证据支撑"
            )
            print(
                f"[OVERSTATEMENT-GATE] Detected '{matched_term}' without core_direct evidence. "
                "Triggering backtrack to Apply."
            )
            result["assessment"] = assessment

        # --- Gate 4: Conclusion-caveat contradiction penalty ---
        rec_text = rec_to_check.text
        caveat_text = " ".join(rec_to_check.caveats) if rec_to_check.caveats else ""
        if _NO_DIFF_RE.search(rec_text) and _NO_DATA_RE.search(caveat_text):
            quality_score = min(quality_score, 0.85)
            assessment.quality_score = quality_score
            assessment.gaps.append(
                "推荐文本声称'无显著差异'但 caveats 承认无直接比较数据，存在逻辑矛盾"
            )
            print(
                "[CONSISTENCY-CHECK] Conclusion claims 'no difference' but caveats "
                "acknowledge no direct data — capping score at 85/100"
            )
            result["assessment"] = assessment

        # --- Gate 5: Strong without core_direct → force downgrade ---
        rec_final = result.get("recommendation", recommendation)
        if rec_final.strength == "Strong" and not getattr(rec_final, "has_core_direct", False):
            if hasattr(rec_final, "model_copy"):
                downgraded = rec_final.model_copy(update={
                    "strength": "Conditional",
                    "caveats": list(rec_final.caveats) + [
                        "Strength 由 Strong 自动下调为 Conditional：无 core_direct 证据（PICO 完全匹配的头对头比较），"
                        "不满足 Strong 推荐的必要条件。"
                    ],
                })
            else:
                downgraded = rec_final
                downgraded.strength = "Conditional"
                downgraded.caveats = list(rec_final.caveats) + [
                    "Strength 由 Strong 自动下调为 Conditional：无 core_direct 证据。"
                ]
            print(
                "[GRADE-CLAMP] Strong → Conditional: no core_direct evidence present."
            )
            result["recommendation"] = downgraded

        return result
