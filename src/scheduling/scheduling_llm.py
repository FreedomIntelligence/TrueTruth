import json
import re
from typing import Dict, Any, List
from pathlib import Path
from dataclasses import asdict, is_dataclass
from src.state.schema import SchedulingDecision, Observe, WorkflowState


class SchedulingLLM:
    """Scheduling LLM that makes decisions based on observe"""

    def __init__(self, llm):
        """
        Initialize Scheduling LLM

        Args:
            llm: Language model instance
        """
        self.llm = llm
        self.prompt_path = (
            Path(__file__).parent.parent / "config" / "prompts" / "scheduling_llm.txt"
        )
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load scheduling prompt template"""
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def make_decision(
        self, observe: Observe, state: WorkflowState, soft_gate_signals: List[str]
    ) -> SchedulingDecision:
        """
        Make scheduling decision based on observe

        Args:
            observe: Current stage observation
            state: Current workflow state
            soft_gate_signals: List of soft gate signals

        Returns:
            SchedulingDecision object
        """
        # Prepare context
        context = self._prepare_context(observe, state, soft_gate_signals)

        # Format prompt
        prompt = self.prompt_template.format(**context)

        # Call LLM
        response = self.llm.invoke(prompt)

        # Parse response
        try:
            decision_dict = self._parse_json_response(response.content)
        except Exception as e:
            print(f"Error parsing scheduling decision: {e}")
            print(f"Response: {response.content}")
            raise

        # Convert to SchedulingDecision
        decision = SchedulingDecision(
            reasoning=decision_dict["reasoning"],
            action=decision_dict["action"],
            parameters=decision_dict.get("parameters"),
        )

        return decision

    def _prepare_context(
        self, observe: Observe, state: WorkflowState, soft_gate_signals: List[str]
    ) -> Dict[str, Any]:
        """Prepare context for scheduling prompt"""

        # Format dimension scores
        dimension_scores_str = "\n".join(
            [
                f"  - {dim}: {score:.2f}"
                for dim, score in observe.evaluation.dimension_scores.items()
            ]
        )

        # Format issues
        if observe.evaluation.issues:
            issues_str = "\n".join(
                [
                    f"  - [{issue.severity.upper()}] {issue.dimension}: {issue.description}"
                    for issue in observe.evaluation.issues
                ]
            )
        else:
            issues_str = "  无问题"

        # Format execution history summary
        history_summary = self._format_execution_history(state)

        # Format stage output — truncated to avoid inflating the prompt with large evidence bodies.
        # The scheduling decision relies on scores/issues (already present above), not raw evidence text.
        serializable_output = {}
        for key, value in observe.output.items():
            if is_dataclass(value):
                serializable_output[key] = asdict(value)
            elif isinstance(value, list) and value and is_dataclass(value[0]):
                serializable_output[key] = [asdict(item) for item in value]
            else:
                serializable_output[key] = value

        # For Appraise stage: strip abstracts from evidence objects before truncation.
        # Abstracts (~1000 chars each × 10 papers) dominate the 3000-char budget and
        # crowd out the decision-relevant fields (study_type, grade_level, etc.).
        # judge_llm.py already does the same stripping for its own prompt.
        if observe.stage == "Appraise":
            appraisal = serializable_output.get("appraisal_results")
            if isinstance(appraisal, dict):
                for ev in appraisal.get("evidence", []):
                    if isinstance(ev, dict):
                        ev.pop("abstract", None)

        raw_output_str = json.dumps(
            serializable_output, ensure_ascii=False, indent=2, default=str
        )
        # Cap at 3000 chars — enough for the scheduler to understand what was produced
        # without sending thousands of tokens of evidence abstracts
        stage_output_str = raw_output_str[:3000] + (
            "..." if len(raw_output_str) > 3000 else ""
        )

        context = {
            "original_question": state["original_question"],
            "current_stage": observe.stage,
            "current_iteration": state["iteration_count"],
            "remaining_budget": state.get(
                "remaining_budget", 20 - state["iteration_count"]
            ),
            "stage_output": stage_output_str,
            "overall_score": observe.evaluation.overall_score,
            "pass_threshold": "是" if observe.evaluation.pass_threshold else "否",
            "dimension_scores": dimension_scores_str,
            "issues": issues_str,
            "summary": observe.evaluation.summary,
            "soft_gate_signals": ", ".join(soft_gate_signals)
            if soft_gate_signals
            else "无",
            "execution_history_summary": history_summary,
        }

        return context

    def _format_execution_history(self, state: WorkflowState) -> str:
        """Format execution history for display"""
        history = state.get("execution_history", [])

        if not history:
            return "无执行历史"

        # Get last 5 executions
        recent = history[-5:]

        lines = []
        for node in recent:
            status = "✓" if node.status == "completed" else "✗"
            lines.append(f"  {status} {node.agent_type} (迭代 {node.id})")

            if node.observe:
                lines.append(
                    f"    评分: {node.observe.evaluation.overall_score:.2f}, 通过: {node.observe.evaluation.pass_threshold}"
                )

            if node.scheduling_decision:
                lines.append(f"    决策: {node.scheduling_decision.action}")

        # Add backtrack history
        backtrack_history = state.get("backtrack_history", [])
        if backtrack_history:
            lines.append("\n  回退历史:")
            for bt in backtrack_history[-3:]:
                lines.append(
                    f"    - 从 {bt['from_stage']} 回退到 {bt['to_stage']}: {bt['reason']}"
                )

        return "\n".join(lines)

    def _repair_json(self, s: str) -> str:
        """Fix common LLM JSON formatting mistakes before parsing.

        Handles the pattern where a string value is followed by whitespace +
        newline + another key without a separating comma, e.g.:
            "reasoning": "..."\\n  "action": "proceed"
        """
        # Add missing comma between a closing string-value quote and the next key
        return re.sub(r'"(\s*\n\s+)"', r'",\1"', s)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response.

        Tries full JSON parsing first, then a missing-comma repair, then a
        regex-based field extraction for the common case where the LLM embeds
        unescaped ASCII double-quote characters inside the ``reasoning`` string.
        """

        def _try_parse(s: str):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
            try:
                return json.loads(self._repair_json(s))
            except json.JSONDecodeError:
                return None

        # Try direct parse
        result = _try_parse(response)
        if result is not None:
            return result

        # Try extracting from markdown code block
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            result = _try_parse(response[start:end].strip())
            if result is not None:
                return result

        # Try raw JSON object extraction
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            result = _try_parse(response[start:end])
            if result is not None:
                return result

        # Fallback: extract critical fields via regex.
        # Handles LLM output where "reasoning" contains unescaped " characters
        # (e.g. Chinese text with embedded ASCII quotes) that break JSON parsing.
        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', response)
        if action_match:
            action = action_match.group(1)
            params: Dict[str, Any] = {}
            params_match = re.search(
                r'"parameters"\s*:\s*(\{.*?\})', response, re.DOTALL
            )
            if params_match:
                try:
                    params = json.loads(params_match.group(1))
                except json.JSONDecodeError:
                    pass
            return {
                "reasoning": "[JSON解析回退：响应含非转义引号，已直接提取action字段]",
                "action": action,
                "parameters": params,
            }

        raise ValueError(f"Could not parse JSON from response: {response[:200]}")
