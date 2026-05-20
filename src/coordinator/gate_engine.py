from typing import Optional, List
from src.state.schema import WorkflowState, GateTrigger


def check_max_iterations_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if maximum iterations exceeded"""
    iteration_count = state.get("iteration_count", 0)
    agent_call_counts = state.get("agent_call_counts", {})

    if iteration_count > 20:
        return GateTrigger(
            gate_name="max_iterations",
            reason="Exceeded 20 total iterations",
            suggested_action="terminate",
            output_message={
                "status": "max_iterations_exceeded",
                "message": "系统已达到最大迭代次数限制（20次），无法继续。",
                "iteration_count": iteration_count,
            },
        )

    for agent, count in agent_call_counts.items():
        if count > 5:
            return GateTrigger(
                gate_name="max_iterations",
                reason=f"Agent {agent} called {count} times",
                suggested_action="terminate",
                output_message={
                    "status": "max_agent_calls_exceeded",
                    "message": f"阶段 {agent} 已被调用 {count} 次，超过单阶段限制（5次）。",
                    "agent": agent,
                    "call_count": count,
                },
            )
    return None


def check_dead_loop_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if system is stuck in a dead loop"""
    backtrack_history = state.get("backtrack_history", [])

    if len(backtrack_history) < 3:
        return None

    # Check last 3 backtracks
    recent_backtracks = backtrack_history[-3:]

    # If all 3 recent backtracks are to the same stage, it's a dead loop
    to_stages = [bt["to_stage"] for bt in recent_backtracks]
    if len(set(to_stages)) == 1:
        return GateTrigger(
            gate_name="dead_loop",
            reason=f"System stuck in loop, repeatedly backtracking to {to_stages[0]}",
            suggested_action="terminate",
            output_message={
                "status": "dead_loop_detected",
                "message": f"系统陷入死循环，连续3次回退到 {to_stages[0]} 阶段。",
                "loop_stage": to_stages[0],
            },
        )

    return None


def check_critical_issue_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if current observe has critical issues"""
    observe_history = state.get("observe_history", [])

    if not observe_history:
        return None

    current_observe = observe_history[-1]

    # Check for critical issues
    critical_issues = [
        issue
        for issue in current_observe.evaluation.issues
        if issue.severity == "critical"
    ]

    if critical_issues:
        return GateTrigger(
            gate_name="critical_issue",
            reason=f"Critical issue detected: {critical_issues[0].description}",
            suggested_action="backtrack_or_terminate",
            output_message={
                "status": "critical_issue",
                "message": "发现致命问题，需要立即处理。",
                "issues": [
                    {"dimension": issue.dimension, "description": issue.description}
                    for issue in critical_issues
                ],
            },
        )

    return None


def check_evidence_insufficiency_gate(state: WorkflowState) -> Optional[GateTrigger]:
    """Check if evidence is severely insufficient (graceful failure)"""

    # Scenario 1: Acquire stage tried 3+ times with 0 results
    if state["current_step"] == "Acquire":
        acquire_attempts = state["agent_call_counts"].get("Acquire", 0)
        evidence_list = state.get("evidence_list", [])

        if acquire_attempts >= 3 and len(evidence_list) == 0:
            return GateTrigger(
                gate_name="insufficient_evidence",
                reason="经过3次尝试仍无法找到相关证据",
                suggested_action="terminate",
                output_message={
                    "status": "evidence_insufficient",
                    "message": "未找到足够的循证医学证据支持该临床问题。建议：1) 重新定义问题；2) 咨询专家意见；3) 考虑其他证据来源。",
                    "attempts": acquire_attempts,
                    "evidence_count": 0,
                },
            )

    return None


def collect_soft_gate_signals(state: WorkflowState) -> List[str]:
    """Collect soft gate signals that don't force termination but inform scheduling"""
    signals = []

    observe_history = state.get("observe_history", [])
    if not observe_history:
        return signals

    current_observe = observe_history[-1]

    # Check for search_exhausted signal from Acquire judge
    if current_observe.stage == "Acquire":
        if getattr(current_observe.evaluation, "search_exhausted", False):
            signals.append("acquire_search_exhausted")

    # Check for low confidence data in Appraise stage
    if current_observe.stage == "Appraise":
        numerical_confidence = current_observe.output.get("numerical_confidence", 1.0)
        if numerical_confidence < 0.7:
            signals.append("low_confidence_data")

        bias_inconsistency = current_observe.output.get("bias_inconsistency", False)
        if bias_inconsistency:
            signals.append("bias_assessment_uncertain")

    # Check for unresolved conflicts in Apply stage
    if current_observe.stage == "Apply":
        unresolved_conflict = current_observe.output.get("unresolved_conflict", False)
        if unresolved_conflict:
            signals.append("evidence_conflict_unresolved")

    # Check for major issues
    major_issues = [
        issue
        for issue in current_observe.evaluation.issues
        if issue.severity == "major"
    ]
    if len(major_issues) >= 2:
        signals.append("multiple_major_issues")

    return signals


def check_hard_gates(state: WorkflowState) -> Optional[GateTrigger]:
    """Check all hard gates in priority order"""
    gates = [
        check_max_iterations_gate,
        check_dead_loop_gate,
        check_critical_issue_gate,
        check_evidence_insufficiency_gate,
    ]

    for gate_func in gates:
        trigger = gate_func(state)
        if trigger is not None:
            return trigger
    return None
