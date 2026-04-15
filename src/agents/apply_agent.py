from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, Recommendation


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
                f"Evidence {i+1}:\nTitle: {e.title}\nQuality: {e.grade_level}\nSource: {e.source}"
                for i, e in enumerate(appraisal.evidence)
            ]
        )

        prompt = self.prompt_template.format(
            question=question,
            evidence_summary=evidence_summary,
            appraisal_summary=appraisal.summary,
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

        # Determine overall evidence quality
        grades = [e.grade_level for e in appraisal.evidence if e.grade_level]
        if "High" in grades:
            evidence_quality = "High"
        elif "Moderate" in grades:
            evidence_quality = "Moderate"
        elif "Low" in grades:
            evidence_quality = "Low"
        else:
            evidence_quality = "Very Low"

        # GRADE enforcement: clamp strength to match evidence quality.
        # LLM may override this despite prompt instructions, so we enforce in Python.
        llm_strength = rec_dict.get("strength", "Weak")
        if evidence_quality in ("Very Low", "Low") and llm_strength == "Strong":
            strength = "Weak"
        else:
            strength = llm_strength

        recommendation = Recommendation(
            text=rec_dict["recommendation"],
            strength=strength,
            rationale=rec_dict["rationale"],
            caveats=rec_dict.get("caveats", []),
            evidence_quality=evidence_quality,
        )

        return {"recommendation": recommendation}
