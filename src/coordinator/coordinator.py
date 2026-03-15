from typing import Dict, Any, Optional
import time
from datetime import datetime
from src.state.schema import WorkflowState, ExecutionNode, HumanInterventionRequest, SchedulingDecision
from src.coordinator.gate_engine import check_hard_gates, collect_soft_gate_signals
from src.judge.judge_llm import JudgeLLM
from src.scheduling.scheduling_llm import SchedulingLLM

class Coordinator:
    """Central coordinator for the EBM 5A workflow"""

    def __init__(self, agents: Dict[str, Any], judge_llm: JudgeLLM, scheduling_llm: SchedulingLLM):
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
            question_type=None
        )

    def execute_agent(self, agent_name: str, state: WorkflowState) -> WorkflowState:
        """Execute a single agent and update state"""
        agent = self.agents[agent_name]

        # Update agent call count
        state["agent_call_counts"][agent_name] = state["agent_call_counts"].get(agent_name, 0) + 1
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
            scheduling_decision=None
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

    def handle_scheduling_decision(self, state: WorkflowState, decision) -> WorkflowState:
        """Handle scheduling decision"""
        action = decision.action

        if action == "proceed":
            # Move to next stage
            next_step = self.route_next(state)
            state["current_step"] = next_step

        elif action.startswith("backtrack_to_"):
            # Extract target stage
            target_stage = action.replace("backtrack_to_", "").capitalize()

            # Record backtrack
            state["backtrack_history"].append({
                "from_stage": state["current_step"],
                "to_stage": target_stage,
                "reason": decision.reasoning,
                "timestamp": datetime.now()
            })

            state["current_step"] = target_stage
            state["backtrack_reason"] = decision.reasoning

        elif action == "retry_current":
            # Stay on current stage, will be re-executed
            state["backtrack_reason"] = decision.reasoning

        elif action == "terminate":
            state["should_terminate"] = True
            state["backtrack_reason"] = decision.reasoning

        elif action == "request_human_review":
            # Record human intervention request
            params = decision.parameters or {}
            request = HumanInterventionRequest(
                review_scope=params.get("review_scope", "unknown"),
                reason=params.get("reason", decision.reasoning),
                context=params.get("context", {}),
                resume_after_review=params.get("resume_after_review", True),
                timestamp=datetime.now()
            )
            state["human_intervention_requests"].append(request)

            # For MVP, we'll just log and continue
            print(f"\n{'='*80}")
            print(f"HUMAN INTERVENTION REQUESTED")
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

    def execute_workflow(self, question: str) -> WorkflowState:
        """Execute complete workflow with Judge and Scheduling LLMs"""
        state = self.initialize_state(question)
        workflow_start = time.time()
        timing_summary: Dict[str, float] = {}  # stage -> cumulative seconds

        while not state.get("should_terminate"):
            current_step = state["current_step"]

            if current_step is None:
                break

            # Execute current agent (includes Judge timing inside execute_agent)
            state = self.execute_agent(current_step, state)

            # Check hard gates first
            gate_trigger = check_hard_gates(state)
            if gate_trigger:
                state["gate_triggered"] = gate_trigger.gate_name
                state["backtrack_reason"] = gate_trigger.reason

                if gate_trigger.suggested_action == "terminate":
                    state["should_terminate"] = True
                    if gate_trigger.output_message:
                        print(f"\n{'='*80}")
                        print(f"WORKFLOW TERMINATED: {gate_trigger.output_message.get('status')}")
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

            # Fast-path Rule 1: if score passes threshold AND all issues are Minor (no critical/major),
            # skip Scheduling LLM entirely and auto-proceed — matches the mandatory scheduling rule.
            has_critical_or_major = any(
                getattr(issue, "severity", "") in ("critical", "major")
                for issue in current_observe.evaluation.issues
            )
            if current_observe.evaluation.pass_threshold and not has_critical_or_major:
                decision = SchedulingDecision(
                    reasoning="自动前进（快速规则）：所有问题均为Minor级别且评分通过阈值，无需LLM决策。",
                    action="proceed",
                    parameters=None,
                )
                print(f"[FAST-PATH] Stage {current_step} passed with no critical/major issues — auto-proceeding.")

            elif current_observe.evaluation.pass_threshold and has_critical_or_major:
                # Fast-path Rule 2: pass_threshold=True but the current major issue
                # dimension set has appeared in ANY previous attempt of the same stage
                # → the retry feedback loop is cycling and cannot improve → auto-proceed.
                current_major_dims = frozenset(
                    getattr(issue, "dimension", "")
                    for issue in current_observe.evaluation.issues
                    if getattr(issue, "severity", "") in ("critical", "major")
                )
                # Collect all previous same-stage observations (excluding current)
                prev_same_stage_obs = [
                    obs for obs in state["observe_history"][:-1]
                    if getattr(obs, "stage", None) == current_step
                ]

                # Check whether current dims appeared in ANY prior same-stage attempt
                dims_seen_before = any(
                    current_major_dims == frozenset(
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
                        soft_gate_signals=soft_gate_signals
                    )
                    print(f"[TIMING] Scheduling ({current_step}): {time.time()-t0:.1f}s")

            else:
                # fail_threshold → Make scheduling decision using Scheduling LLM
                t0 = time.time()
                decision = self.scheduling_llm.make_decision(
                    observe=current_observe,
                    state=state,
                    soft_gate_signals=soft_gate_signals
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
        print(f"\n[TIMING] Total workflow time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
        return state
