"""EBM 5A pipeline runner — wraps the full workflow and extracts BaselineResult + evidence."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.baselines.protocol import BaselineResult
from src.state.schema import Evidence

if TYPE_CHECKING:
    from src.config.llm_config import _LLMClient


def _format_recommendation(state: dict) -> str:
    """Extract the user-facing recommendation text from workflow state.

    For the main recommendation path this delegates to the shared renderer,
    which converts internal [EV-id] citations into numbered references and
    keeps the audit-layer rationale out of the user-/Judge-facing text.
    """
    rec = state.get("recommendation")
    direct = state.get("direct_answer_output")

    if state.get("route_type") == "direct_answer" and direct:
        parts = [direct.get("answer", "")]
        basis = direct.get("answer_basis")
        guideline = direct.get("guideline_source")
        if basis:
            parts.append(f"\n推荐依据：{basis}")
        if guideline:
            parts.append(f"指南来源：{guideline}")
        caveats = direct.get("caveats") or []
        if caveats:
            parts.append("\n注意事项：")
            for c in caveats:
                parts.append(f"  • {c}")
        return "\n".join(parts)

    if rec:
        from src.render.recommendation import render_recommendation
        # Merge safety_evidence so grounded [EV-DRUGSAFETY-.../section] citations
        # resolve to their drug-label metadata in the reference list rather than
        # degrading to a fabricated-looking author line. Render-only merge.
        evidence_list = (state.get("evidence_list") or []) + (state.get("safety_evidence") or [])
        return render_recommendation(rec, evidence_list, state.get("outcome_coverage"))

    return "[未生成推荐——工作流未成功完成]"


def run(question: str, evidence=None, llm=None) -> tuple[BaselineResult, list[Evidence]]:
    """Run the full EBM 5A pipeline.

    Returns:
        (result, captured_evidence) — the evidence list from the Acquire stage,
        usable as frozen evidence for other baselines.
    """
    from src.main import create_workflow, _ensure_rag_services

    _ensure_rag_services()

    captured_evidence: list[Evidence] = []

    def _on_stage(agent_name: str, state: dict):
        if agent_name == "Acquire":
            ev = state.get("evidence_list") or []
            captured_evidence.clear()
            captured_evidence.extend(ev)

    coordinator = create_workflow()

    t0 = time.time()
    state = coordinator.execute_workflow(question, on_stage_complete=_on_stage)
    elapsed = time.time() - t0

    response_text = _format_recommendation(state)
    ev_ids = [e.evidence_id for e in (state.get("evidence_list") or [])]

    call_counts = state.get("agent_call_counts") or {}
    total_calls = sum(call_counts.values())

    metadata: dict = {
        "route_type": state.get("route_type"),
        "question_type": state.get("question_type"),
        "iteration_count": state.get("iteration_count", 0),
        "agent_call_counts": dict(call_counts),
    }
    rec = state.get("recommendation")
    if rec:
        metadata["strength"] = rec.strength
        metadata["evidence_quality"] = rec.evidence_quality
    assess = state.get("assessment")
    if assess:
        metadata["assess_score"] = assess.quality_score
        metadata["assess_needs_backtrack"] = assess.needs_backtrack

    result = BaselineResult(
        pipeline_name="ebm_5a",
        question=question,
        response_text=response_text,
        evidence_used=ev_ids,
        elapsed_s=round(elapsed, 2),
        llm_calls=total_calls,
        metadata=metadata,
    )

    return result, list(captured_evidence)
