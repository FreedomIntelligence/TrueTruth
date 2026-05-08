"""
AskAgent — clinical question triage and EBM query structuring.

Routing flow:
  1. Router prompt  → route_type: "direct_answer" | "full_pipeline" | "sub_questions"
  2a. direct_answer → DirectAnswer prompt → populate direct_answer_output, set should_terminate
  2b. sub_questions → decompose into sub-question list, recurse on first sub-question
  2c. full_pipeline  → framework-specific prompt (PICO / PIRD / PEO / Prognosis)
                       Diagnosis questions run diag_step1 → diag_step2 before PIRD
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent, robust_parse_json
from src.state.schema import EBMQuery, PICOQuery, WorkflowState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt directory
# ---------------------------------------------------------------------------
_PROMPT_DIR = Path(__file__).parent.parent / "config" / "prompts" / "ask"

# Map framework name → prompt file stem
_FRAMEWORK_PROMPT: Dict[str, str] = {
    "pico": "ebm_pico",
    "pird": "ebm_pird",
    "peo": "ebm_peo",
    "prognosis": "ebm_prognosis",
    "diagnostic_reasoning": "ebm_pird",  # fallback to PIRD for diagnostic_reasoning
}

# Valid question types
_VALID_QUESTION_TYPES = {"Therapy", "Diagnosis", "Prognosis", "Harm", "Prevention", "Background", "Mixed"}

# Valid route types
_VALID_ROUTE_TYPES = {"direct_answer", "full_pipeline", "sub_questions"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load_prompt(stem: str) -> str:
    """Load a prompt template from the ask/ directory."""
    path = _PROMPT_DIR / f"{stem}.txt"
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _safe_str(value: Any, default: str = "") -> str:
    """Return str(value) or default if value is None/falsy."""
    if value is None:
        return default
    return str(value)


def _ebm_query_from_dict(d: dict) -> EBMQuery:
    """Build an EBMQuery dataclass from a parsed LLM JSON dict."""
    return EBMQuery(
        query_type=_safe_str(d.get("query_type"), "pico"),
        patient=_safe_str(d.get("patient")),
        primary_focus=_safe_str(d.get("primary_focus")),
        outcome=_safe_str(d.get("outcome")),
        keywords=d.get("keywords") or [],
        comparator=d.get("comparator"),
        reference_standard=d.get("reference_standard"),
        time_horizon=d.get("time_horizon"),
    )


def _pico_from_ebm(ebm: EBMQuery) -> PICOQuery:
    """Derive a legacy PICOQuery from an EBMQuery for backward compatibility."""
    return PICOQuery(
        patient=ebm.patient,
        intervention=ebm.primary_focus,
        comparison=_safe_str(ebm.comparator),
        outcome=ebm.outcome,
        keywords=ebm.keywords,
    )


# ---------------------------------------------------------------------------
# AskAgent
# ---------------------------------------------------------------------------

class AskAgent(BaseAgent):
    """
    Agent for triaging clinical questions and structuring them into EBM queries.

    Routing logic:
      - direct_answer  → answer immediately, set should_terminate = True
      - sub_questions  → decompose, store list, process first sub-question
      - full_pipeline  → select framework prompt, build EBMQuery
        - Diagnosis questions run a two-step diagnostic analysis first
    """

    def __init__(self, llm, tools: Optional[List[Any]] = None):
        super().__init__(llm=llm, tools=tools or [], agent_type="Ask")
        # Pre-load all prompt templates at init time to catch missing files early
        self._prompts: Dict[str, str] = {
            stem: _load_prompt(stem)
            for stem in [
                "router",
                "direct_answer",
                "diag_step1",
                "diag_step2",
                "ebm_pico",
                "ebm_pird",
                "ebm_peo",
                "ebm_prognosis",
            ]
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Execute the Ask agent.

        Returns a dict of state updates.  The coordinator merges this into
        WorkflowState.
        """
        question = state["original_question"]
        backtrack_context = self._build_backtrack_context(state)

        # ── Step 1: Route ──────────────────────────────────────────────
        route_result = self._run_router(question, backtrack_context)
        route_type = route_result.get("route_type", "full_pipeline")
        if route_type not in _VALID_ROUTE_TYPES:
            logger.warning("Unknown route_type '%s', defaulting to full_pipeline", route_type)
            route_type = "full_pipeline"

        route_confidence = float(route_result.get("route_confidence", 0.0))
        question_type = route_result.get("question_type") or "Therapy"
        if question_type not in _VALID_QUESTION_TYPES:
            question_type = "Therapy"
        ebm_framework = route_result.get("ebm_framework") or "pico"

        logger.info(
            "AskAgent routing: route=%s (conf=%.2f) type=%s framework=%s",
            route_type, route_confidence, question_type, ebm_framework,
        )

        # ── Step 2a: Direct answer ─────────────────────────────────────
        if route_type == "direct_answer":
            return self._handle_direct_answer(
                question=question,
                question_type=question_type,
                routing_rationale=route_result.get("routing_rationale", ""),
                route_confidence=route_confidence,
            )

        # ── Step 2b: Sub-questions ─────────────────────────────────────
        if route_type == "sub_questions":
            sub_question_texts: List[str] = route_result.get("sub_question_texts") or []
            if not sub_question_texts:
                # Router said sub_questions but gave no list — fall through to full_pipeline
                logger.warning("sub_questions route but no sub_question_texts; falling back to full_pipeline")
                route_type = "full_pipeline"
            else:
                return self._handle_sub_questions(
                    sub_question_texts=sub_question_texts,
                    question_type=question_type,
                    ebm_framework=ebm_framework,
                    route_confidence=route_confidence,
                    backtrack_context=backtrack_context,
                )

        # ── Step 2c: Full pipeline ─────────────────────────────────────
        return self._handle_full_pipeline(
            question=question,
            question_type=question_type,
            ebm_framework=ebm_framework,
            route_confidence=route_confidence,
            backtrack_context=backtrack_context,
        )

    # ------------------------------------------------------------------
    # Router
    # ------------------------------------------------------------------

    def _run_router(self, question: str, backtrack_context: str) -> dict:
        """Call the router prompt and return parsed JSON."""
        prompt = self._prompts["router"].format(
            question=question,
            backtrack_context=backtrack_context,
        )
        response = self.llm.invoke(prompt)
        try:
            return robust_parse_json(response.content)
        except ValueError as exc:
            logger.error("Router JSON parse failed: %s", exc)
            return {"route_type": "full_pipeline", "question_type": "Therapy", "ebm_framework": "pico"}

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    def _handle_direct_answer(
        self,
        question: str,
        question_type: str,
        routing_rationale: str,
        route_confidence: float,
    ) -> Dict[str, Any]:
        """Run the direct_answer prompt and return state updates."""
        prompt = self._prompts["direct_answer"].format(
            question=question,
            question_type=question_type,
            routing_rationale=routing_rationale,
        )
        response = self.llm.invoke(prompt)
        try:
            answer_dict = robust_parse_json(response.content)
        except ValueError as exc:
            logger.error("DirectAnswer JSON parse failed: %s", exc)
            answer_dict = {"answer": response.content, "requires_pipeline": False}

        # If the LLM decided mid-answer that a pipeline is needed, honour it
        if answer_dict.get("requires_pipeline"):
            logger.info("DirectAnswer prompt escalated to full_pipeline")
            return self._handle_full_pipeline(
                question=question,
                question_type=question_type,
                ebm_framework="pico",
                route_confidence=route_confidence,
                backtrack_context="",
            )

        return {
            "route_type": "direct_answer",
            "route_confidence": route_confidence,
            "question_type": question_type,
            "direct_answer_output": answer_dict,
            "should_terminate": True,
            # Keep pico_query / ebm_query as None — not needed for direct answers
        }

    def _handle_sub_questions(
        self,
        sub_question_texts: List[str],
        question_type: str,
        ebm_framework: str,
        route_confidence: float,
        backtrack_context: str,
    ) -> Dict[str, Any]:
        """
        Decompose into sub-questions.

        Each sub-question is structured independently using the appropriate
        framework prompt.  The results are stored in sub_pico_queries.
        The first sub-question is also promoted to ebm_query / pico_query
        so the rest of the pipeline can proceed immediately.
        """
        sub_queries: List[EBMQuery] = []
        for sub_q in sub_question_texts:
            try:
                ebm = self._structure_question(
                    question=sub_q,
                    question_type=question_type,
                    ebm_framework=ebm_framework,
                    backtrack_context=backtrack_context,
                )
                sub_queries.append(ebm)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to structure sub-question '%s': %s", sub_q[:60], exc)

        if not sub_queries:
            # All sub-questions failed — fall back to full pipeline on original question
            logger.warning("All sub-question structuring failed; falling back to full_pipeline")
            return self._handle_full_pipeline(
                question=sub_question_texts[0] if sub_question_texts else "",
                question_type=question_type,
                ebm_framework=ebm_framework,
                route_confidence=route_confidence,
                backtrack_context=backtrack_context,
            )

        first = sub_queries[0]
        return {
            "route_type": "sub_questions",
            "route_confidence": route_confidence,
            "question_type": question_type,
            "ebm_query": first,
            "pico_query": _pico_from_ebm(first),
            "sub_pico_queries": sub_queries,
            "sub_question_index": 0,
            "sub_question_total": len(sub_queries),
            "should_terminate": False,
        }

    def _handle_full_pipeline(
        self,
        question: str,
        question_type: str,
        ebm_framework: str,
        route_confidence: float,
        backtrack_context: str,
    ) -> Dict[str, Any]:
        """Structure the question into an EBMQuery and return state updates."""
        ebm = self._structure_question(
            question=question,
            question_type=question_type,
            ebm_framework=ebm_framework,
            backtrack_context=backtrack_context,
        )
        return {
            "route_type": "full_pipeline",
            "route_confidence": route_confidence,
            "question_type": question_type,
            "ebm_query": ebm,
            "pico_query": _pico_from_ebm(ebm),
            "should_terminate": False,
        }

    # ------------------------------------------------------------------
    # Question structuring
    # ------------------------------------------------------------------

    def _structure_question(
        self,
        question: str,
        question_type: str,
        ebm_framework: str,
        backtrack_context: str,
    ) -> EBMQuery:
        """
        Run the appropriate framework prompt(s) and return an EBMQuery.

        Diagnosis questions run diag_step1 → diag_step2 before the PIRD prompt.
        """
        # Diagnostic two-step pre-processing
        diag_step1_output: Optional[dict] = None
        if question_type == "Diagnosis" or ebm_framework in ("pird", "diagnostic_reasoning"):
            diag_step1_output = self._run_diag_step1(question, backtrack_context)

        # Select framework prompt
        framework_key = ebm_framework if ebm_framework in _FRAMEWORK_PROMPT else "pico"
        prompt_stem = _FRAMEWORK_PROMPT[framework_key]

        prompt_template = self._prompts[prompt_stem]

        # Build format kwargs — each template uses a subset of these
        fmt_kwargs: Dict[str, str] = {
            "question": question,
            "question_type": question_type,
            "backtrack_context": backtrack_context,
            "diag_step1_output": str(diag_step1_output) if diag_step1_output else "",
        }

        # Safely format — ignore keys the template doesn't use
        try:
            prompt = prompt_template.format(**fmt_kwargs)
        except KeyError:
            # Template has extra placeholders we didn't supply — fill with empty string
            import string
            formatter = string.Formatter()
            keys_needed = {fn for _, fn, _, _ in formatter.parse(prompt_template) if fn}
            safe_kwargs = {k: fmt_kwargs.get(k, "") for k in keys_needed}
            prompt = prompt_template.format(**safe_kwargs)

        response = self.llm.invoke(prompt)
        try:
            ebm_dict = robust_parse_json(response.content)
        except ValueError as exc:
            logger.error("Framework prompt JSON parse failed (%s): %s", prompt_stem, exc)
            raise

        return _ebm_query_from_dict(ebm_dict)

    def _run_diag_step1(self, question: str, backtrack_context: str) -> dict:
        """Run the diagnostic step-1 analysis prompt."""
        prompt = self._prompts["diag_step1"].format(
            question=question,
            backtrack_context=backtrack_context,
        )
        response = self.llm.invoke(prompt)
        try:
            return robust_parse_json(response.content)
        except ValueError as exc:
            logger.warning("diag_step1 JSON parse failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _build_backtrack_context(state: WorkflowState) -> str:
        """Build a backtrack context string from state."""
        reason = state.get("backtrack_reason")
        if not reason:
            return ""
        return (
            f"Previous attempt failed with the following reason:\n{reason}\n"
            "Please refine the question structuring to address this issue."
        )
