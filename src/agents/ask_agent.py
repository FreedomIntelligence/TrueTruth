from typing import List, Dict, Any
from pathlib import Path
from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import WorkflowState, PICOQuery


class AskAgent(BaseAgent):
    """Agent for refining clinical questions into PICO format"""

    def __init__(self, llm, tools: List[Any] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Ask")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load prompt template from file"""
        prompt_path = (
            Path(__file__).parent.parent / "config" / "prompts" / "ask_agent.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from LLM response with heuristic error recovery."""
        return robust_parse_json(content)

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute Ask agent to extract PICO from question"""
        question = state["original_question"]

        backtrack_context = ""
        if state.get("backtrack_reason"):
            backtrack_context = f"Previous attempt failed: {state['backtrack_reason']}\nPlease refine the question."

        prompt = self.prompt_template.format(
            question=question, backtrack_context=backtrack_context
        )

        response = self.llm.invoke(prompt)
        pico_dict = self._parse_json(response.content)

        pico_query = PICOQuery(
            patient=pico_dict["patient"],
            intervention=pico_dict["intervention"],
            comparison=pico_dict["comparison"],
            outcome=pico_dict["outcome"],
            keywords=pico_dict["keywords"],
        )

        question_type = pico_dict.get("question_type", "Therapy")
        valid_types = {"Therapy", "Diagnosis", "Prognosis", "Harm", "Prevention"}
        if question_type not in valid_types:
            question_type = "Therapy"

        return {"pico_query": pico_query, "question_type": question_type}
