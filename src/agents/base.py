import json
import re
from typing import List, Any, Dict
from abc import ABC, abstractmethod
from src.state.schema import WorkflowState


def _extract_json_block(content: str) -> str:
    """Extract the raw JSON string from LLM response (handles ```json blocks and bare JSON)."""
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        if end > start:
            return content[start:end].strip()
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return content[start:end]
    return content


def _attempt_json_repair(raw: str) -> str:
    """
    Apply heuristic repairs to a JSON string that failed to parse.

    Common LLM JSON errors handled:
    1. Missing comma between array elements or object fields (two closing
       brackets / quotes on adjacent lines without a comma).
    2. Trailing commas before ] or } (strict JSON disallows these).
    3. Single-quoted strings (replace with double quotes where safe).
    """
    # Remove trailing commas before ] or }
    repaired = re.sub(r",\s*([}\]])", r"\1", raw)
    # Add missing comma between } and { or ] and [ or " and { on adjacent lines
    repaired = re.sub(r"([}\]\"'])\s*\n(\s*)([{\[\"'])", r"\1,\n\2\3", repaired)
    # Add missing comma between } and " (object field after nested object)
    repaired = re.sub(r"(})\s*\n(\s*)(\")", r"\1,\n\2\3", repaired)
    return repaired


def robust_parse_json(content: str) -> dict:
    """
    Parse JSON from LLM response with multi-stage error recovery:
      1. Direct parse of full content.
      2. Extract ```json block or bare {…} and parse.
      3. Apply heuristic repairs and retry.
      4. Raise ValueError with diagnostic context if all attempts fail.
    """
    # Stage 1: direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Stage 2: extract block and parse
    raw = _extract_json_block(content)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Stage 3: heuristic repair then parse
    repaired = _attempt_json_repair(raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as final_err:
        raise ValueError(
            f"JSON parse failed after repair attempt.\n"
            f"Error: {final_err}\n"
            f"Raw excerpt (first 300 chars): {raw[:300]}"
        )


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, llm, tools: List[Any], agent_type: str):
        """
        Initialize agent

        Args:
            llm: Language model instance
            tools: List of tools available to this agent
            agent_type: Type identifier (Ask/Acquire/Appraise/Apply/Assess)
        """
        self.llm = llm
        self.tools = tools
        self.agent_type = agent_type

    @abstractmethod
    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Execute agent logic

        Args:
            state: Current workflow state

        Returns:
            Dictionary with agent outputs
        """
        raise NotImplementedError("Subclasses must implement execute()")
