from typing import List, Dict, Any, Optional
from pathlib import Path
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, Recommendation, EBMQuery, PICOQuery


def _format_ebm_query(ebm_query: EBMQuery) -> str:
    """Format an EBMQuery into a concise human-readable description."""
    def _s(v: Any) -> str:
        return str(v) if v is not None else "N/A"

    qt = ebm_query.query_type
    if qt == "pico":
        return (f"Patient: {_s(ebm_query.patient)} | "
                f"Intervention: {_s(ebm_query.primary_focus)} | "
                f"Comparator: {_s(ebm_query.comparator)} | "
                f"Outcome: {_s(ebm_query.outcome)}")
    elif qt == "pird":
        return (f"Patient: {_s(ebm_query.patient)} | "
                f"Index Test: {_s(ebm_query.primary_focus)} | "
                f"Reference Standard: {_s(ebm_query.reference_standard)} | "
                f"Target Condition: {_s(ebm_query.outcome)}")
    elif qt == "peo":
        return (f"Patient: {_s(ebm_query.patient)} | "
                f"Exposure: {_s(ebm_query.primary_focus)} | "
                f"Outcome: {_s(ebm_query.outcome)}")
    else:  # prognosis
        return (f"Patient: {_s(ebm_query.patient)} | "
                f"Prognostic Factor: {_s(ebm_query.primary_focus)} | "
                f"Outcome: {_s(ebm_query.outcome)} | "
                f"Time Horizon: {_s(ebm_query.time_horizon)}")


def _format_pico_query(pico_query: PICOQuery) -> str:
    """Format a PICOQuery into a concise human-readable description."""
    return (
        f"P: {pico_query.patient}; "
        f"I: {pico_query.intervention}; "
        f"C: {pico_query.comparison}; "
        f"O: {pico_query.outcome}"
    )


def _summarize_downgrade_factors(grade_rationales: List[Dict]) -> Dict[str, Any]:
    """
    Summarise key downgrade factors across all appraised studies.

    Returns a dict with:
      - key_downgrade_factors: human-readable string listing the most common issues
      - has_serious_inconsistency: bool — True when any study has inconsistency
        rated SERIOUS or VERY_SERIOUS
    """
    factor_counts: Dict[str, int] = {}
    has_serious_inconsistency = False

    for r in grade_rationales:
        for factor in ("risk_of_bias", "inconsistency", "indirectness", "imprecision"):
            val = r.get(factor, "NOT_SERIOUS")
            if val in ("SERIOUS", "VERY_SERIOUS"):
                factor_counts[factor] = factor_counts.get(factor, 0) + 1
        if r.get("inconsistency") in ("SERIOUS", "VERY_SERIOUS"):
            has_serious_inconsistency = True
        if r.get("publication_bias") == "SUSPECTED":
            factor_counts["publication_bias"] = factor_counts.get("publication_bias", 0) + 1

    if not factor_counts:
        key_downgrade_factors = "无主要降级因素"
    else:
        _label_map = {
            "risk_of_bias": "偏倚风险",
            "inconsistency": "不一致性",
            "indirectness": "间接性",
            "imprecision": "不精确性",
            "publication_bias": "发表偏倚",
        }
        parts = [
            f"{_label_map.get(k, k)}({v}篇)" for k, v in sorted(factor_counts.items())
        ]
        key_downgrade_factors = "、".join(parts)

    return {
        "key_downgrade_factors": key_downgrade_factors,
        "has_serious_inconsistency": has_serious_inconsistency,
    }


class ApplyAgent(BaseAgent):
    """Agent for generating clinical recommendations"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Apply")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = (
            Path(__file__).parent.parent / "config" / "prompts" / "apply_agent.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response with heuristic error recovery."""
        return robust_parse_json(content)

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Apply agent to generate recommendation"""
        appraisal = state.get("appraisal_results")
        if not appraisal:
            raise ValueError("No appraisal results found in state")

        question = state["original_question"]

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = f"Previous attempt failed: {state['backtrack_reason']}\nPlease address these issues in your recommendation."

        evidence_summary = "\n\n".join(
            [
                f"Evidence {i+1}:\nTitle: {e.title}\nGRADE: {e.grade_level}\n"
                f"Study Type: {e.study_type or 'Unknown'}\n"
                f"Key Findings:\n{e.key_sentences or e.abstract or '（无摘要）'}"
                for i, e in enumerate(appraisal.evidence)
            ]
        )

        # --- Build structured query description ---
        ebm_query = state.get("ebm_query")
        pico_query = state.get("pico_query")
        if ebm_query:
            query_description = _format_ebm_query(ebm_query)
        elif pico_query:
            query_description = _format_pico_query(pico_query)
        else:
            query_description = question

        # --- Summarise downgrade factors from grade_rationales ---
        grade_rationales: List[Dict] = state.get("grade_rationales") or []
        downgrade_summary = _summarize_downgrade_factors(grade_rationales)
        key_downgrade_factors = downgrade_summary["key_downgrade_factors"]
        has_serious_inconsistency = downgrade_summary["has_serious_inconsistency"]

        # --- Route type context ---
        route_type = state.get("route_type") or "full_pipeline"
        route_confidence: Optional[float] = state.get("route_confidence")

        prompt = self.prompt_template.format(
            question=question,
            query_description=query_description,
            route_type=route_type,
            evidence_summary=evidence_summary,
            appraisal_summary=appraisal.summary,
            key_downgrade_factors=key_downgrade_factors,
            has_serious_inconsistency="YES" if has_serious_inconsistency else "NO",
            backtrack_context=backtrack_context,
        )

        response = self.llm.invoke(prompt)
        try:
            rec_dict = self._parse_json(response.content)
        except ValueError:
            # LLM may output reasoning only without JSON (response truncated or forgot JSON).
            # Retry once with a short follow-up prompt asking only for the JSON block.
            print(
                "[WARN] Apply agent: JSON parse failed on first response, retrying for JSON only."
            )
            retry_prompt = (
                "Your previous response did not include a valid JSON block. "
                "Please output ONLY the following JSON (no reasoning, no extra text):\n\n"
                "```json\n"
                "{\n"
                '  "recommendation": "...",\n'
                '  "strength": "Strong or Weak or Conditional or Consensus-based or Insufficient Evidence or No Recommendation",\n'
                '  "rationale": "...",\n'
                '  "caveats": ["..."]\n'
                "}\n"
                "```\n\n"
                f"Base your answer on the previous conversation context. Original question: {question[:300]}"
            )
            retry_response = self.llm.invoke(retry_prompt)
            rec_dict = self._parse_json(retry_response.content)

        # evidence_quality is now determined by the LLM itself (see apply_agent.txt Step 4).
        # The LLM reports the quality of evidence it actually adopted, not all retrieved evidence.
        # Fallback to "Very Low" if the field is missing or unrecognised.
        _valid_qualities = {"High", "Moderate", "Low", "Very Low"}
        evidence_quality = rec_dict.get("evidence_quality", "")
        if evidence_quality not in _valid_qualities:
            evidence_quality = "Very Low"

        # Safety clamp: enforce hard GRADE rules the LLM may still violate.
        llm_strength = rec_dict.get("strength", "Weak")
        if evidence_quality in ("Very Low", "Low") and llm_strength == "Strong":
            strength = "Weak"
        elif has_serious_inconsistency and llm_strength == "Strong":
            # Serious inconsistency across studies also blocks Strong recommendation
            strength = "Weak"
        else:
            strength = llm_strength

        # Build caveats list, appending route_confidence warning when confidence is low
        caveats: List[str] = list(rec_dict.get("caveats", []))
        if route_confidence is not None and route_confidence < 0.7:
            caveats.append(
                f"路由置信度较低（{route_confidence:.0%}），问题分类可能不准确，建议人工核实检索策略是否匹配临床问题类型。"
            )

        recommendation = Recommendation(
            text=rec_dict["recommendation"],
            strength=strength,
            rationale=rec_dict["rationale"],
            caveats=caveats,
            evidence_quality=evidence_quality,
        )

        return {"recommendation": recommendation}
