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
from dataclasses import is_dataclass

from src.coordinator.coordinator import Coordinator
from src.state.schema import WorkflowState, SchedulingDecision
from web.backend.event_types import SSEEvent, EventType
from web.backend.serializers import serialize_agent_output
from web.backend import log_capture as _lc


class InstrumentedCoordinator(Coordinator):
    def __init__(self, agents, judge_llm, scheduling_llm,
                 event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop,
                 cancel_flag: threading.Event = None):
        super().__init__(agents=agents, judge_llm=judge_llm, scheduling_llm=scheduling_llm)
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

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def execute_workflow(self, question: str) -> WorkflowState:
        self._emit(EventType.WORKFLOW_STARTED, {"question": question, "timestamp": self._ts()})
        t0 = time.time()
        state = super().execute_workflow(question)
        elapsed = round(time.time() - t0, 1)

        rec = state.get("recommendation")
        assess = state.get("assessment")
        self._emit(EventType.WORKFLOW_COMPLETED, {
            "recommendation": {
                "text": rec.text,
                "strength": rec.strength,
                "rationale": rec.rationale,
                "caveats": rec.caveats,
                "evidence_quality": rec.evidence_quality,
            } if rec else None,
            "assessment": {
                "quality_score": assess.quality_score,
                "gaps": assess.gaps,
            } if assess else None,
            "stats": {
                "iteration_count": state["iteration_count"],
                "agent_call_counts": state["agent_call_counts"],
                "backtrack_count": len(state.get("backtrack_history", [])),
                "total_elapsed_s": elapsed,
            },
            "timestamp": self._ts(),
        })
        return state

    def execute_agent(self, agent_name: str, state: WorkflowState) -> WorkflowState:
        if self._cancel.is_set():
            raise RuntimeError("Workflow cancelled by client")

        self._current_agent = agent_name
        _lc.set_current_agent(agent_name)

        call_count = state["agent_call_counts"].get(agent_name, 0) + 1
        self._emit(EventType.AGENT_STARTED, {
            "agent": agent_name,
            "call_count": call_count,
            "iteration": state["iteration_count"] + 1,
            "timestamp": self._ts(),
        })

        t0 = time.time()
        result_state = super().execute_agent(agent_name, state)
        elapsed = round(time.time() - t0, 1)

        output = serialize_agent_output(agent_name, result_state)
        self._emit(EventType.AGENT_COMPLETED, {
            "agent": agent_name,
            "call_count": call_count,
            "elapsed_s": elapsed,
            "output": output,
            "timestamp": self._ts(),
        })

        # Judge evaluation from the latest observe
        if result_state.get("observe_history"):
            ev = result_state["observe_history"][-1].evaluation
            self._emit(EventType.JUDGE_COMPLETED, {
                "agent": agent_name,
                "call_count": call_count,
                "evaluation": {
                    "overall_score": round(ev.overall_score, 3),
                    "pass_threshold": ev.pass_threshold,
                    "dimension_scores": {k: round(v, 3) for k, v in ev.dimension_scores.items()},
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
            })

        return result_state

    def handle_scheduling_decision(self, state: WorkflowState, decision: SchedulingDecision) -> WorkflowState:
        action = decision.action
        current_step = state["current_step"]

        is_fastpath = (
            "快速规则" in decision.reasoning
            or "循环Major规则" in decision.reasoning
        )

        if action.startswith("backtrack_to_"):
            target = action.replace("backtrack_to_", "").capitalize()
            self._emit(EventType.BACKTRACK_OCCURRED, {
                "from_stage": current_step,
                "to_stage": target,
                "reason": decision.reasoning,
                "timestamp": self._ts(),
            })

        evt = EventType.FASTPATH_TRIGGERED if is_fastpath else EventType.SCHEDULING_DECIDED
        self._emit(evt, {
            "agent": current_step,
            "action": action,
            "reasoning": decision.reasoning,
            "is_fastpath": is_fastpath,
            "timestamp": self._ts(),
        })

        return super().handle_scheduling_decision(state, decision)
