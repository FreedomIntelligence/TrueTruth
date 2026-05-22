from typing import Dict, Any, Optional
import time
from datetime import datetime
from src.state.schema import (
    WorkflowState,
    ExecutionNode,
    HumanInterventionRequest,
    SchedulingDecision,
)
from src.coordinator.gate_engine import check_hard_gates, collect_soft_gate_signals
from src.judge.judge_llm import JudgeLLM
from src.scheduling.scheduling_llm import SchedulingLLM


def _build_feedback(decision: SchedulingDecision) -> str:
    """Combine reasoning + adjust_strategy into a single feedback string for agents."""
    parts = [decision.reasoning]
    params = decision.parameters or {}
    if params.get("adjust_strategy"):
        parts.append(f"具体修改指令：{params['adjust_strategy']}")
    if params.get("focus_on"):
        parts.append(f"重点关注：{params['focus_on']}")
    return "\n".join(parts)


class Coordinator:
    """Central coordinator for the EBM 5A workflow"""

    def __init__(
        self, agents: Dict[str, Any], judge_llm: JudgeLLM, scheduling_llm: SchedulingLLM
    ):
        """
        Initialize coordinator with agents and LLMs

        Args:
            agents: Dictionary mapping agent names to agent instances
            judge_llm: Judge LLM for evaluating stage outputs
            scheduling_llm: Scheduling LLM for making decisions
        """
        self.agents = agents
        self.judge_llm = judge_llm
        self.scheduling_llm = scheduling_llm
        self.agent_sequence = ["Ask", "Acquire", "Appraise", "Apply", "Assess"]

    def initialize_state(self, question: str) -> WorkflowState:
        """Initialize workflow state"""
        return WorkflowState(
            original_question=question,
            current_step="Ask",
            iteration_count=0,
            agent_call_counts={},
            pico_query=None,
            evidence_list=None,
            appraisal_results=None,
            recommendation=None,
            assessment=None,
            gate_triggered=None,
            backtrack_reason=None,
            should_terminate=False,
            execution_history=[],
            observe_history=[],
            decision_history=[],
            backtrack_history=[],
            human_intervention_requests=[],
            remaining_budget=20,
            soft_gate_signals=[],
            question_type=None,
            # Routing fields (populated by AskAgent)
            route_type=None,
            route_confidence=None,
            direct_answer_output=None,
            ebm_query=None,
            sub_pico_queries=None,
            sub_question_index=None,
            sub_question_total=None,
        )

    def execute_agent(self, agent_name: str, state: WorkflowState, on_agent_complete=None) -> WorkflowState:
        """Execute a single agent and update state"""
        agent = self.agents[agent_name]

        # Update agent call count
        state["agent_call_counts"][agent_name] = (
            state["agent_call_counts"].get(agent_name, 0) + 1
        )
        state["iteration_count"] += 1
        state["remaining_budget"] = 20 - state["iteration_count"]

        # Execute agent
        t0 = time.time()
        result = agent.execute(state)
        agent_elapsed = time.time() - t0
        print(f"[TIMING] {agent_name} agent: {agent_elapsed:.1f}s")

        # Update state with agent outputs
        for key, value in result.items():
            state[key] = value

        # Notify caller immediately after agent output is ready (before Judge)
        if on_agent_complete is not None:
            try:
                on_agent_complete(agent_name, state)
            except Exception:
                pass

        # Generate observe using Judge LLM
        t0 = time.time()
        observe = self.judge_llm.evaluate_stage(agent_name, result, state)
        judge_elapsed = time.time() - t0
        print(f"[TIMING] Judge ({agent_name}): {judge_elapsed:.1f}s")
        state["observe_history"].append(observe)

        # Record execution in history
        node = ExecutionNode(
            id=f"{agent_name}_{state['iteration_count']}",
            agent_type=agent_name,
            timestamp=datetime.now(),
            inputs={"question": state["original_question"]},
            outputs=result,
            tools_used=[],
            gate_triggered=None,
            status="completed",
            observe=observe,
            scheduling_decision=None,
        )
        state["execution_history"].append(node)

        return state

    def route_next(self, state: WorkflowState) -> Optional[str]:
        """Determine next agent to execute based on scheduling decision"""
        current_step = state["current_step"]

        # Check if we should terminate
        if state.get("should_terminate"):
            return None

        # Check if assessment is complete
        if current_step == "Assess" and state.get("assessment"):
            return None  # Workflow complete

        # Normal forward flow
        try:
            current_idx = self.agent_sequence.index(current_step)
            if current_idx < len(self.agent_sequence) - 1:
                return self.agent_sequence[current_idx + 1]
        except ValueError:
            pass

        return None

    def handle_scheduling_decision(
        self, state: WorkflowState, decision
    ) -> WorkflowState:
        """Handle scheduling decision"""
        action = decision.action

        if action == "proceed":
            # Move to next stage
            next_step = self.route_next(state)
            state["current_step"] = next_step

        elif action.startswith("backtrack_to_"):
            # Extract target stage
            target_stage = action.replace("backtrack_to_", "").capitalize()

            # Guard: backtrack_to_acquire is only legitimate when Acquire returned 0 results
            # OR evidence is completely unrelated to the clinical question.
            # If evidence exists (even low quality / indirect), proceed instead — GRADE handles
            # indirectness via downgrade factors in Appraise, not by refusing to continue.
            if target_stage == "Acquire":
                evidence_list = state.get("evidence_list") or []
                acquire_backtracks = sum(
                    1 for bt in state.get("backtrack_history", [])
                    if bt.get("to_stage") == "Acquire"
                )
                if len(evidence_list) > 0 and acquire_backtracks >= 1:
                    # Already backtracked to Acquire once and still found evidence — proceed instead
                    print(
                        f"[GUARD] backtrack_to_acquire overridden → proceed "
                        f"(evidence_list has {len(evidence_list)} items, "
                        f"already backtracked {acquire_backtracks}x to Acquire)"
                    )
                    decision.action = "proceed"
                    next_step = self.route_next(state)
                    state["current_step"] = next_step
                    return state

            # Record backtrack
            state["backtrack_history"].append(
                {
                    "from_stage": state["current_step"],
                    "to_stage": target_stage,
                    "reason": decision.reasoning,
                    "timestamp": datetime.now(),
                }
            )

            state["current_step"] = target_stage
            state["backtrack_reason"] = _build_feedback(decision)

        elif action == "retry_current":
            # Stay on current stage, will be re-executed
            state["backtrack_reason"] = _build_feedback(decision)

        elif action == "terminate":
            state["should_terminate"] = True
            state["backtrack_reason"] = _build_feedback(decision)

        elif action == "request_human_review":
            # Record human intervention request
            params = decision.parameters or {}
            request = HumanInterventionRequest(
                review_scope=params.get("review_scope", "unknown"),
                reason=params.get("reason", decision.reasoning),
                context=params.get("context", {}),
                resume_after_review=params.get("resume_after_review", True),
                timestamp=datetime.now(),
            )
            state["human_intervention_requests"].append(request)

            # For MVP, we'll just log and continue
            print(f"\n{'='*80}")
            print("HUMAN INTERVENTION REQUESTED")
            print(f"{'='*80}")
            print(f"Scope: {request.review_scope}")
            print(f"Reason: {request.reason}")
            print(f"Context: {request.context}")
            print(f"{'='*80}\n")

            # Continue to next stage for now
            if request.resume_after_review:
                next_step = self.route_next(state)
                state["current_step"] = next_step
            else:
                state["should_terminate"] = True

        return state

    def execute_workflow(self, question: str, on_stage_complete=None) -> WorkflowState:
        """Execute complete workflow with Judge and Scheduling LLMs"""
        state = self.initialize_state(question)
        workflow_start = time.time()

        while not state.get("should_terminate"):
            current_step = state["current_step"]

            if current_step is None:
                break

            # Execute current agent — on_stage_complete fires inside execute_agent
            # immediately after agent output is ready (before Judge), so the user
            # sees Ask results ~12s earlier than waiting for Judge to finish.
            state = self.execute_agent(current_step, state, on_agent_complete=on_stage_complete)

            # ── Direct-answer early exit ────────────────────────────────────────
            # If the Ask agent decided the question can be answered directly from
            # established knowledge, skip the full pipeline and return immediately.
            if current_step == "Ask" and state.get("route_type") == "direct_answer":
                print("[ROUTE] direct_answer — skipping full pipeline.")
                state["should_terminate"] = True
                state["current_step"] = None
                break

            # Check hard gates first
            gate_trigger = check_hard_gates(state)
            if gate_trigger:
                state["gate_triggered"] = gate_trigger.gate_name
                state["backtrack_reason"] = gate_trigger.reason

                if gate_trigger.suggested_action == "terminate":
                    state["should_terminate"] = True
                    if gate_trigger.output_message:
                        print(f"\n{'='*80}")
                        print(
                            f"WORKFLOW TERMINATED: {gate_trigger.output_message.get('status')}"
                        )
                        print(f"{'='*80}")
                        print(f"Message: {gate_trigger.output_message.get('message')}")
                        print(f"{'='*80}\n")
                    break

            # Collect soft gate signals
            soft_gate_signals = collect_soft_gate_signals(state)
            state["soft_gate_signals"] = soft_gate_signals

            # Get current observe
            current_observe = state["observe_history"][-1]

            # Assess is the final stage: no scheduling needed, workflow ends here
            if current_step == "Assess":
                state["current_step"] = None
                break

            # Presentation-only issue dimensions in Apply that are always retry_current
            # (pure formatting defects — backtracking upstream cannot fix them).
            _APPLY_PRESENTATION_DIMS = frozenset({
                "citation_traceable",
                "recommendation_specific",
                "patient_preference_considered",
            })

            # Fast-path Rule 3: fail_threshold but same stage already retried ≥3 times
            # → stop cycling. Acquire with 0 results → backtrack to Ask once to broaden
            # PICO; if Ask already received that hint and Acquire still empty, terminate.
            current_stage_retries = state["agent_call_counts"].get(current_step, 0) - 1
            if not current_observe.evaluation.pass_threshold and current_stage_retries >= 3:
                if current_step == "Acquire" and not state.get("evidence_list"):
                    ask_broaden_backtracks = sum(
                        1 for bt in state.get("backtrack_history", [])
                        if bt.get("to_stage") == "Ask"
                        and "broaden_pico" in (bt.get("reason") or "")
                    )
                    if ask_broaden_backtracks == 0:
                        decision = SchedulingDecision(
                            reasoning=(
                                "broaden_pico：Acquire 已 4 次空结果，疑似 PICO 过窄。"
                                "回退到 Ask 拓宽检索词（去除合并症细节、加同义词、放宽研究类型至 case report / guideline）。"
                            ),
                            action="backtrack_to_ask",
                            parameters={
                                "adjust_strategy": (
                                    "Acquire 4 次返回 0 篇文献，请重写 PICO："
                                    "①保留核心病种与治疗意图，去除次要合并症；"
                                    "②补充英文/MeSH 同义词与上位词；"
                                    "③放宽 study_type 接受范围（允许 case report / guideline / observational）。"
                                ),
                            },
                        )
                        print(
                            f"[FAST-PATH-3] Acquire empty {current_stage_retries + 1}x — backtracking to Ask to broaden PICO."
                        )
                    else:
                        decision = SchedulingDecision(
                            reasoning=(
                                f"自动终止（Acquire空结果上限）：Acquire 已执行 "
                                f"{current_stage_retries + 1} 次仍未检索到任何证据，且 Ask "
                                "已收到 broaden_pico 提示，终止流程并由 Apply 报 Insufficient Evidence。"
                            ),
                            action="terminate",
                            parameters=None,
                        )
                        print(
                            f"[FAST-PATH-3] Acquire empty after Ask already broadened — terminating."
                        )
                else:
                    decision = SchedulingDecision(
                        reasoning=(
                            f"自动前进（重试上限规则）：{current_step} 阶段已执行 "
                            f"{current_stage_retries + 1} 次仍未通过，继续重试无收益，强制前进。"
                        ),
                        action="proceed",
                        parameters=None,
                    )
                    print(
                        f"[FAST-PATH-3] Stage {current_step}: retried {current_stage_retries} times without passing — force proceed."
                    )

            # Fast-path Rule 4: Apply stage, all non-passing issues are presentation-only
            # → always retry_current, never backtrack upstream.
            elif current_step == "Apply" and not current_observe.evaluation.pass_threshold:
                failing_dims = frozenset(
                    getattr(issue, "dimension", "")
                    for issue in current_observe.evaluation.issues
                    if getattr(issue, "severity", "") in ("critical", "major", "minor")
                    and "PARTIAL" not in getattr(issue, "description", "")
                )
                if failing_dims and failing_dims.issubset(_APPLY_PRESENTATION_DIMS):
                    decision = SchedulingDecision(
                        reasoning=(
                            "自动重试（呈现类规则）：Apply阶段失败维度全为呈现/格式问题 "
                            f"({', '.join(sorted(failing_dims))})，根因在Apply内部，重试可修复，禁止回退上游。"
                        ),
                        action="retry_current",
                        parameters={"adjust_strategy": "请使用PMID而非内部编号标注文献，确保推荐足够具体，并纳入患者偏好讨论。"},
                    )
                    print(
                        f"[FAST-PATH-4] Apply: all failures are presentation-only ({', '.join(sorted(failing_dims))}) — auto retry_current."
                    )
                else:
                    # Fall through to normal LLM scheduling below
                    decision = None
            else:
                decision = None

            # Fast-path Rule 5: soft_gate acquire_search_exhausted — proceed, let Apply report insufficient evidence
            if decision is None and "acquire_search_exhausted" in soft_gate_signals:
                if current_step == "Acquire":
                    decision = SchedulingDecision(
                        reasoning=(
                            "自动前进（检索穷尽规则）：acquire_search_exhausted信号触发，"
                            "该临床领域文献有限，继续检索无益，由Apply输出Insufficient Evidence。"
                        ),
                        action="proceed",
                        parameters=None,
                    )
                    print("[FAST-PATH-5] acquire_search_exhausted — auto-proceed to Appraise.")

            # Fast-path Rule 1: if score passes threshold AND all issues are Minor (no critical/major),
            # skip Scheduling LLM entirely and auto-proceed — matches the mandatory scheduling rule.
            has_critical_or_major = any(
                getattr(issue, "severity", "") in ("critical", "major")
                for issue in current_observe.evaluation.issues
            )
            if decision is not None:
                pass  # already decided above
            elif current_observe.evaluation.pass_threshold and not has_critical_or_major:
                decision = SchedulingDecision(
                    reasoning="自动前进（快速规则）：所有问题均为Minor级别且评分通过阈值，无需LLM决策。",
                    action="proceed",
                    parameters=None,
                )
                print(
                    f"[FAST-PATH] Stage {current_step} passed with no critical/major issues — auto-proceeding."
                )

            elif decision is None and current_observe.evaluation.pass_threshold and has_critical_or_major:
                # Fast-path Rule 2a: all major/critical issues are PARTIAL (not NO/missing)
                # → score passed threshold and no hard failures → auto-proceed.
                all_partial = all(
                    "PARTIAL" in getattr(issue, "description", "")
                    for issue in current_observe.evaluation.issues
                    if getattr(issue, "severity", "") in ("critical", "major")
                )
                if all_partial:
                    decision = SchedulingDecision(
                        reasoning=(
                            "自动前进（PARTIAL规则）：所有Major/Critical问题均为PARTIAL（部分通过），"
                            "分数已通过阈值，重试无法显著改善，直接前进。"
                        ),
                        action="proceed",
                        parameters=None,
                    )
                    print(
                        f"[FAST-PATH-2a] Stage {current_step}: all major issues are PARTIAL — auto-proceeding."
                    )
                else:
                    # Fast-path Rule 2b: same major dimension set seen before → cycling → auto-proceed.
                    current_major_dims = frozenset(
                        getattr(issue, "dimension", "")
                        for issue in current_observe.evaluation.issues
                        if getattr(issue, "severity", "") in ("critical", "major")
                    )
                    prev_same_stage_obs = [
                        obs
                        for obs in state["observe_history"][:-1]
                        if getattr(obs, "stage", None) == current_step
                    ]
                    dims_seen_before = any(
                        current_major_dims
                        == frozenset(
                            getattr(issue, "dimension", "")
                            for issue in obs.evaluation.issues
                            if getattr(issue, "severity", "") in ("critical", "major")
                        )
                        for obs in prev_same_stage_obs
                    )

                    if dims_seen_before:
                        decision = SchedulingDecision(
                            reasoning=(
                                "自动前进（循环Major规则）：当前Major问题维度组合在本阶段历史尝试中已出现过，"
                                "重试无法改善，且分数已通过阈值，直接前进。"
                            ),
                            action="proceed",
                            parameters=None,
                        )
                        print(
                            f"[FAST-PATH-2] Stage {current_step}: cycling major issues "
                            f"({', '.join(sorted(current_major_dims))}) seen before — auto-proceeding."
                        )
                    else:
                        t0 = time.time()
                        decision = self.scheduling_llm.make_decision(
                            observe=current_observe,
                            state=state,
                            soft_gate_signals=soft_gate_signals,
                        )
                        print(
                            f"[TIMING] Scheduling ({current_step}): {time.time()-t0:.1f}s"
                        )

            elif decision is None:
                # fail_threshold → Make scheduling decision using Scheduling LLM
                t0 = time.time()
                decision = self.scheduling_llm.make_decision(
                    observe=current_observe,
                    state=state,
                    soft_gate_signals=soft_gate_signals,
                )
                sched_elapsed = time.time() - t0
                print(f"[TIMING] Scheduling ({current_step}): {sched_elapsed:.1f}s")

            # Record decision
            state["decision_history"].append(decision)

            # Update last execution node with decision
            if state["execution_history"]:
                state["execution_history"][-1].scheduling_decision = decision

            # Handle scheduling decision
            state = self.handle_scheduling_decision(state, decision)

            # Check if we've reached the end
            if state["current_step"] is None:
                break

        total_elapsed = time.time() - workflow_start
        print(
            f"\n[TIMING] Total workflow time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)"
        )
        return state
