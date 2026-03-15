from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, Assessment

class AssessAgent(BaseAgent):
    """Agent for assessing recommendation quality"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Assess")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "assess_agent.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
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
            backtrack_context=backtrack_context
        )

        response = self.llm.invoke(prompt)
        assess_dict = self._parse_json(response.content)

        # Compute quality_score deterministically from classification labels.
        completeness_map = {"YES": 1.0, "PARTIAL": 0.55, "NO": 0.1}
        strength_map = {"YES": 1.0, "MINOR_ISSUE": 0.65, "MAJOR_CONTRADICTION": 0.1}
        chain_map = {"COMPLETE": 1.0, "WEAK": 0.6, "BROKEN": 0.1}
        caveats_map = {"YES": 1.0, "PARTIAL": 0.7, "NO": 0.3, "NA": 1.0}

        quality_score = round(
            0.50 * completeness_map.get(assess_dict.get("completeness", "PARTIAL"), 0.55)
            + 0.25 * strength_map.get(assess_dict.get("strength_consistent", "YES"), 1.0)
            + 0.15 * chain_map.get(assess_dict.get("reasoning_chain", "COMPLETE"), 1.0)
            + 0.10 * caveats_map.get(assess_dict.get("caveats_adequate", "NA"), 1.0),
            2,
        )

        assessment = Assessment(
            quality_score=quality_score,
            gaps=assess_dict.get("gaps", []),
            needs_backtrack=assess_dict.get("needs_backtrack", False),
            backtrack_reason=assess_dict.get("backtrack_reason")
        )

        return {"assessment": assessment}
