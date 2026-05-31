"""InstrumentedCoordinator: Coordinator subclass that emits SSE events at key points.

No existing files are modified.  This class:
  - Inherits Coordinator unchanged
  - Overrides execute_agent, handle_scheduling_decision, execute_workflow
  - Pushes SSEEvent objects into an asyncio.Queue consumed by the SSE endpoint
"""

import asyncio
import threading
import time
from datetime import datetime, timezone

from src.coordinator.coordinator import Coordinator
from src.state.schema import WorkflowState, SchedulingDecision
from web.backend.event_types import SSEEvent, EventType
from web.backend.serializers import serialize_agent_output
from web.backend import log_capture as _lc


class InstrumentedCoordinator(Coordinator):
    def __init__(
        self,
        agents,
        judge_llm,
        scheduling_llm,
        event_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        cancel_flag: threading.Event = None,
    ):
        super().__init__(
            agents=agents, judge_llm=judge_llm, scheduling_llm=scheduling_llm
        )
        self._eq = event_queue
        self._loop = loop
        self._cancel = cancel_flag or threading.Event()
        self._current_agent: str = "system"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: EventType, data: dict):
        """Thread-safe push into the asyncio queue."""
        event = SSEEvent(event=event_type, data=data)
        asyncio.run_coroutine_threadsafe(self._eq.put(event), self._loop)

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _emit_text_stream(self, text: str, event_type: EventType, chunk_size: int = 4) -> None:
        """Replay text as token-chunk SSE events at ~25 ms cadence.

        Runs in the worker thread. Checks cancel_flag each iteration so
        a Stop request cleanly aborts mid-replay.
        """
        for i in range(0, len(text), chunk_size):
            if self._cancel.is_set():
                break
            chunk = text[i : i + chunk_size]
            self._emit(event_type, {"chunk": chunk})
            time.sleep(0.025)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def execute_workflow(self, question: str) -> WorkflowState:
        self._emit(
            EventType.WORKFLOW_STARTED, {"question": question, "timestamp": self._ts()}
        )
        t0 = time.time()
        state = super().execute_workflow(question)
        elapsed = round(time.time() - t0, 1)

        rec = state.get("recommendation")
        assess = state.get("assessment")
        direct_raw = state.get("direct_answer_output")
        if isinstance(direct_raw, dict):
            direct_out = direct_raw
        elif direct_raw is not None:
            direct_out = {
                "answer": getattr(direct_raw, "answer", ""),
                "answer_basis": getattr(direct_raw, "answer_basis", None),
                "guideline_source": getattr(direct_raw, "guideline_source", None),
                "caveats": getattr(direct_raw, "caveats", []) or [],
            }
        else:
            direct_out = None

        self._emit(
            EventType.WORKFLOW_COMPLETED,
            {
                "recommendation": {
                    "text": rec.text,
                    "strength": rec.strength,
                    "rationale": rec.rationale,
                    "caveats": rec.caveats,
                    "evidence_quality": rec.evidence_quality,
                }
                if rec
                else None,
                "direct_answer": direct_out,
                "assessment": {
                    "quality_score": assess.quality_score,
                    "gaps": assess.gaps,
                }
                if assess
                else None,
                "outcome_coverage": [
                    {"outcome": oc.outcome, "status": oc.status,
                     "evidence_ids": oc.evidence_ids, "note": oc.note}
                    for oc in (state.get("outcome_coverage") or [])
                    if hasattr(oc, "outcome")
                ] or None,
                "gap_searches": [
                    {"outcome": gs.outcome, "pubmed_query": gs.pubmed_query,
                     "rationale": gs.rationale}
                    for gs in (state.get("gap_searches") or [])
                    if hasattr(gs, "outcome")
                ] or None,
                "stats": {
                    "iteration_count": state["iteration_count"],
                    "agent_call_counts": state["agent_call_counts"],
                    "backtrack_count": len(state.get("backtrack_history", [])),
                    "total_elapsed_s": elapsed,
                },
                "timestamp": self._ts(),
            },
        )
        return state

    def execute_agent(self, agent_name: str, state: WorkflowState, on_agent_complete=None) -> WorkflowState:
        if self._cancel.is_set():
            raise RuntimeError("Workflow cancelled by client")

        self._current_agent = agent_name
        _lc.set_current_agent(agent_name)

        call_count = state["agent_call_counts"].get(agent_name, 0) + 1
        self._emit(
            EventType.AGENT_STARTED,
            {
                "agent": agent_name,
                "call_count": call_count,
                "iteration": state["iteration_count"] + 1,
                "timestamp": self._ts(),
            },
        )

        t0 = time.time()
        result_state = super().execute_agent(agent_name, state, on_agent_complete=on_agent_complete)
        elapsed = round(time.time() - t0, 1)

        # Stream final outputs to the answer area
        if agent_name == "Ask" and result_state.get("route_type") == "direct_answer":
            direct = result_state.get("direct_answer_output") or {}
            answer = direct.get("answer", "") if isinstance(direct, dict) else getattr(direct, "answer", "")
            if answer:
                self._emit_text_stream(answer, EventType.DIRECT_ANSWER_TOKEN)
        elif agent_name == "Apply":
            rec = result_state.get("recommendation")
            if rec and getattr(rec, "text", None):
                self._emit_text_stream(rec.text, EventType.REC_TEXT_TOKEN)

        output = serialize_agent_output(agent_name, result_state)
        self._emit(
            EventType.AGENT_COMPLETED,
            {
                "agent": agent_name,
                "call_count": call_count,
                "elapsed_s": elapsed,
                "output": output,
                "timestamp": self._ts(),
            },
        )

        # Judge evaluation from the latest observe
        if result_state.get("observe_history"):
            ev = result_state["observe_history"][-1].evaluation
            self._emit(
                EventType.JUDGE_COMPLETED,
                {
                    "agent": agent_name,
                    "call_count": call_count,
                    "evaluation": {
                        "overall_score": round(ev.overall_score, 3),
                        "pass_threshold": ev.pass_threshold,
                        "dimension_scores": {
                            k: round(v, 3) if v is not None else None
                            for k, v in ev.dimension_scores.items()
                        },
                        "issues": [
                            {
                                "severity": i.severity,
                                "dimension": i.dimension,
                                "description": i.description,
                            }
                            for i in ev.issues
                        ],
                        "summary": ev.summary,
                        "search_exhausted": ev.search_exhausted,
                    },
                },
            )

        return result_state

    def handle_scheduling_decision(
        self, state: WorkflowState, decision: SchedulingDecision
    ) -> WorkflowState:
        action = decision.action
        current_step = state["current_step"]

        is_fastpath = (
            "快速规则" in decision.reasoning or "循环Major规则" in decision.reasoning
        )

        if action.startswith("backtrack_to_"):
            target = action.replace("backtrack_to_", "").capitalize()
            self._emit(
                EventType.BACKTRACK_OCCURRED,
                {
                    "from_stage": current_step,
                    "to_stage": target,
                    "reason": decision.reasoning,
                    "timestamp": self._ts(),
                },
            )

        evt = (
            EventType.FASTPATH_TRIGGERED
            if is_fastpath
            else EventType.SCHEDULING_DECIDED
        )
        self._emit(
            evt,
            {
                "agent": current_step,
                "action": action,
                "reasoning": decision.reasoning,
                "is_fastpath": is_fastpath,
                "timestamp": self._ts(),
            },
        )

        return super().handle_scheduling_decision(state, decision)
