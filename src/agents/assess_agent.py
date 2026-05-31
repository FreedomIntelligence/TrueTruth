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


class AssessAgent(BaseAgent):
    """Agent for assessing recommendation quality"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Assess")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = (
            Path(__file__).parent.parent / "config" / "prompts" / "assess_agent.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response with heuristic error recovery."""
        return robust_parse_json(content)

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Assess agent to evaluate recommendation quality"""
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

        # Compute quality_score deterministically from classification labels.
        # Weights reflect clinical importance:
        #   strength_consistent elevated to 35% (critical: wrong GRADE label misleads decisions)
        #   completeness reduced to 35% (Apply output quality, important but not dominant)
        #   reasoning_chain 15% (transparency)
        #   caveats 10% (GRADE required, but already enforced by Apply prompt)
        #   sufficiency_judgment 5% (catches reverse errors: InsuffEvid when Conditional warranted)
        completeness_map = {"YES": 1.0, "PARTIAL": 0.55, "NO": 0.1}
        strength_map = {"YES": 1.0, "MINOR_ISSUE": 0.65, "MAJOR_CONTRADICTION": 0.1}
        chain_map = {"COMPLETE": 1.0, "WEAK": 0.6, "BROKEN": 0.1}
        caveats_map = {"YES": 1.0, "PARTIAL": 0.7, "NO": 0.3, "NA": 1.0}
        sufficiency_map = {"CORRECT": 1.0, "NA": 1.0, "OVERLY_CONSERVATIVE": 0.3, "OVERLY_PERMISSIVE": 0.1}

        quality_score = round(
            0.35 * completeness_map.get(assess_dict.get("completeness", "PARTIAL"), 0.55)
            + 0.35 * strength_map.get(assess_dict.get("strength_consistent", "YES"), 1.0)
            + 0.15 * chain_map.get(assess_dict.get("reasoning_chain", "COMPLETE"), 1.0)
            + 0.10 * caveats_map.get(assess_dict.get("caveats_adequate", "NA"), 1.0)
            + 0.05 * sufficiency_map.get(assess_dict.get("sufficiency_judgment", "CORRECT"), 1.0),
            2,
        )

        # Gaps-based cap: if the LLM itself identified gaps, score should not be 1.0
        if assess_dict.get("gaps") and quality_score > 0.95:
            quality_score = 0.95

        assessment = Assessment(
            quality_score=quality_score,
            gaps=assess_dict.get("gaps", []),
            needs_backtrack=assess_dict.get("needs_backtrack", False),
            backtrack_reason=assess_dict.get("backtrack_reason"),
        )

        # Hard GRADE gates (bidirectional):
        #
        # Forward gate: Strong recommendation with low audit score → downgrade to Conditional.
        # Reverse flag: Insufficient Evidence with OVERLY_CONSERVATIVE sufficiency judgment
        #   → add caveat warning (do NOT auto-upgrade; Assess might be wrong, let human decide).
        result: Dict[str, Any] = {"assessment": assessment}
        sufficiency_judgment = assess_dict.get("sufficiency_judgment", "CORRECT")

        if recommendation.strength == "Strong" and quality_score < 0.70:
            downgraded = recommendation.model_copy(update={
                "strength": "Conditional",
                "caveats": list(recommendation.caveats) + [
                    f"Strength 已由 Strong 自动下调为 Conditional：Assess quality_score={quality_score:.2f} < 0.70，"
                    "审计发现完整性/强度一致性/推理链/警示存在不足，不满足 Strong 推荐的硬门槛。"
                ],
            }) if hasattr(recommendation, "model_copy") else recommendation
            if not hasattr(recommendation, "model_copy"):
                downgraded.strength = "Conditional"
                downgraded.caveats = list(recommendation.caveats) + [
                    f"Strength 已由 Strong 自动下调为 Conditional：Assess quality_score={quality_score:.2f} < 0.70。"
                ]
            print(
                f"[GRADE-CLAMP] Strong → Conditional: quality_score={quality_score:.2f} < 0.70."
            )
            result["recommendation"] = downgraded

        elif (recommendation.strength in ("Insufficient Evidence", "No Recommendation")
              and sufficiency_judgment == "OVERLY_CONSERVATIVE"):
            flagged = recommendation.model_copy(update={
                "caveats": list(recommendation.caveats) + [
                    "【Assess 审计】：当前输出为'证据不足'，但 Assess 审计判断证据方向一致，"
                    "按 GRADE 原则（Andrews et al. 2013）本应给出 Conditional 推荐。"
                    "建议人工复核是否存在 Apply 阶段过于保守的问题。"
                ],
            }) if hasattr(recommendation, "model_copy") else recommendation
            print(
                f"[GRADE-FLAG] Insufficient Evidence flagged as OVERLY_CONSERVATIVE by Assess."
            )
            result["recommendation"] = flagged

        # --- Overstatement hard stop ---
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

        # --- Conclusion-caveat contradiction penalty ---
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
                "acknowledge no direct data — capping score at 0.85"
            )
            result["assessment"] = assessment

        # --- Strong without core_direct: force downgrade ---
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
