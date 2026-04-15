#!/usr/bin/env python3
"""
EBM 5A Clinical Decision Support System - Main Entry Point
"""

import sys
from typing import Dict, Any
from src.config.llm_config import get_llm, get_fast_llm
from src.agents.ask_agent import AskAgent
from src.agents.acquire_agent import AcquireAgent
from src.agents.appraise_agent import AppraiseAgent
from src.agents.apply_agent import ApplyAgent
from src.agents.assess_agent import AssessAgent
from src.judge.judge_llm import JudgeLLM
from src.scheduling.scheduling_llm import SchedulingLLM
from src.coordinator.coordinator import Coordinator


def create_workflow() -> Coordinator:
    """
    Create and configure the workflow coordinator with all agents

    Returns:
        Configured Coordinator instance
    """
    # Initialize LLM
    llm = get_llm(temperature=0.0)
    fast_llm = get_fast_llm(temperature=0.0)

    # Initialize agents
    agents = {
        "Ask": AskAgent(llm=llm),
        "Acquire": AcquireAgent(llm=llm),
        "Appraise": AppraiseAgent(llm=llm),
        "Apply": ApplyAgent(llm=llm),
        "Assess": AssessAgent(llm=llm),
    }

    # Initialize Judge LLM (use fast model for classification tasks)
    judge_llm = JudgeLLM(llm=fast_llm)

    # Initialize Scheduling LLM (use fast model for classification tasks)
    scheduling_llm = SchedulingLLM(llm=fast_llm)

    # Create coordinator
    coordinator = Coordinator(
        agents=agents, judge_llm=judge_llm, scheduling_llm=scheduling_llm
    )

    return coordinator


def run_clinical_question(question: str) -> Dict[str, Any]:
    """
    Run a clinical question through the complete 5A workflow

    Args:
        question: Clinical question to process

    Returns:
        Final workflow state with recommendation
    """
    coordinator = create_workflow()
    result = coordinator.execute_workflow(question)
    return result


def format_output(state: Dict[str, Any]) -> str:
    """
    Format workflow output for display

    Args:
        state: Final workflow state

    Returns:
        Formatted output string
    """
    output = []
    output.append("=" * 80)
    output.append("EBM 5A CLINICAL DECISION SUPPORT SYSTEM")
    output.append("=" * 80)
    output.append("")

    # Original question
    output.append(f"QUESTION: {state['original_question']}")
    output.append("")

    # PICO
    if state.get("pico_query"):
        pico = state["pico_query"]
        output.append("STRUCTURED QUESTION (PICO):")
        output.append(f"  Patient: {pico.patient}")
        output.append(f"  Intervention: {pico.intervention}")
        output.append(f"  Comparison: {pico.comparison}")
        output.append(f"  Outcome: {pico.outcome}")
        output.append(f"  Keywords: {', '.join(pico.keywords)}")
        output.append("")

    # Evidence
    if state.get("evidence_list"):
        output.append(f"EVIDENCE FOUND: {len(state['evidence_list'])} articles")
        for i, evidence in enumerate(state["evidence_list"][:3], 1):
            output.append(f"  {i}. {evidence.title}")
            output.append(f"     Source: {evidence.source} (PMID: {evidence.pmid})")
            if evidence.grade_level:
                output.append(f"     Quality: {evidence.grade_level}")
        output.append("")

    # Recommendation
    if state.get("recommendation"):
        rec = state["recommendation"]
        output.append("RECOMMENDATION:")
        output.append(f"  {rec.text}")
        output.append(f"  Strength: {rec.strength}")
        output.append(f"  Evidence Quality: {rec.evidence_quality}")
        output.append(f"  Rationale: {rec.rationale}")
        if rec.caveats:
            output.append("  Caveats:")
            for caveat in rec.caveats:
                output.append(f"    - {caveat}")
        output.append("")

    # Assessment
    if state.get("assessment"):
        assess = state["assessment"]
        output.append("QUALITY ASSESSMENT:")
        output.append(f"  Quality Score: {assess.quality_score:.2f}/1.0")
        if assess.gaps:
            output.append("  Identified Gaps:")
            for gap in assess.gaps:
                output.append(f"    - {gap}")
        output.append("")

    # Observe History
    observe_history = state.get("observe_history", [])
    if observe_history:
        output.append("STAGE EVALUATIONS:")
        for obs in observe_history:
            output.append(f"  {obs.stage}:")
            output.append(f"    Overall Score: {obs.evaluation.overall_score:.2f}")
            output.append(
                f"    Pass: {'Yes' if obs.evaluation.pass_threshold else 'No'}"
            )
            if obs.evaluation.issues:
                output.append("    Issues:")
                for issue in obs.evaluation.issues:
                    output.append(
                        f"      - [{issue.severity.upper()}] {issue.dimension}: {issue.description}"
                    )
        output.append("")

    # Scheduling Decisions
    decision_history = state.get("decision_history", [])
    if decision_history:
        output.append("SCHEDULING DECISIONS:")
        for i, decision in enumerate(decision_history, 1):
            output.append(f"  Decision {i}: {decision.action}")
            output.append(f"    Reasoning: {decision.reasoning[:200]}...")
        output.append("")

    # Backtrack History
    backtrack_history = state.get("backtrack_history", [])
    if backtrack_history:
        output.append("BACKTRACK EVENTS:")
        for bt in backtrack_history:
            output.append(
                f"  From {bt['from_stage']} to {bt['to_stage']}: {bt['reason'][:100]}..."
            )
        output.append("")

    # Human Intervention Requests
    human_requests = state.get("human_intervention_requests", [])
    if human_requests:
        output.append("HUMAN INTERVENTION REQUESTS:")
        for req in human_requests:
            output.append(f"  Scope: {req.review_scope}")
            output.append(f"  Reason: {req.reason}")
        output.append("")

    # Workflow stats
    output.append("WORKFLOW STATISTICS:")
    output.append(f"  Total Iterations: {state['iteration_count']}")
    output.append(f"  Remaining Budget: {state.get('remaining_budget', 0)}")
    output.append(f"  Agent Calls: {state['agent_call_counts']}")
    output.append(f"  Backtracks: {len(backtrack_history)}")
    output.append(f"  Human Interventions: {len(human_requests)}")
    output.append("")

    output.append("=" * 80)

    # ── CLINICAL ANSWER (placed last so it's the most visible result) ──────────
    output.append("")
    output.append("★" * 80)
    output.append("CLINICAL ANSWER")
    output.append("★" * 80)
    output.append(f"Q: {state['original_question']}")
    output.append("")

    rec = state.get("recommendation")
    assess = state.get("assessment")

    if rec:
        output.append(f"A: {rec.text}")
        output.append("")
        output.append(f"   Recommendation Strength : {rec.strength}")
        output.append(f"   Evidence Quality        : {rec.evidence_quality}")
        output.append(f"   Rationale               : {rec.rationale}")
        if rec.caveats:
            output.append("   Caveats                 :")
            for c in rec.caveats:
                output.append(f"     • {c}")
        if assess:
            output.append(
                f"   Overall Quality Score   : {assess.quality_score:.2f} / 1.0"
            )
            if assess.gaps:
                output.append("   Identified Gaps         :")
                for g in assess.gaps:
                    output.append(f"     • {g}")
    else:
        output.append(
            "A: [No recommendation generated — workflow did not complete successfully]"
        )

    output.append("")
    output.append("★" * 80)

    return "\n".join(output)


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print('Usage: python -m src.main "<clinical question>"')
        print("\nExample:")
        print(
            '  python -m src.main "Should I prescribe aspirin for primary prevention in a 60-year-old patient?"'
        )
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    print("Processing clinical question...")
    print(f"Question: {question}\n")

    try:
        result = run_clinical_question(question)
        output = format_output(result)
        print(output)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
