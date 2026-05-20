#!/usr/bin/env python3
"""
EBM 5A Clinical Decision Support System - Main Entry Point
"""

import sys
import io
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

# Force UTF-8 on Windows to avoid GBK encoding errors with Unicode characters.
# line_buffering=True so [TIMING] / stage markers flush as they happen — without
# this, when stdout is redirected to a file the buffer is block-sized and a
# subprocess killed mid-run produces an empty log, making timeouts invisible.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
else:
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
from src.config.llm_config import get_llm, get_fast_llm, get_cache_stats, get_ttft_samples
from src.agents.ask_agent import AskAgent
from src.agents.acquire_agent import AcquireAgent
from src.agents.appraise_agent import AppraiseAgent
from src.agents.apply_agent import ApplyAgent
from src.agents.assess_agent import AssessAgent
from src.judge.judge_llm import JudgeLLM
from src.scheduling.scheduling_llm import SchedulingLLM
from src.coordinator.coordinator import Coordinator


def _warmup_llms() -> None:
    """Fire one minimal request to each LLM purpose in parallel so HTTP
    connections and the upstream model are pre-warmed before the pipeline's
    first real call. Failures are swallowed — warmup must never block the run."""
    t0 = time.time()
    clients = [
        ("agent", get_llm(temperature=0.0, purpose="agent")),
        ("judge", get_fast_llm(temperature=0.0, purpose="judge")),
        ("scheduling", get_fast_llm(temperature=0.0, purpose="scheduling")),
    ]

    def _ping(name_client):
        name, client = name_client
        try:
            client.invoke("ok")
        except Exception as exc:
            print(f"[WARMUP] {name} failed (non-fatal): {exc}")

    with ThreadPoolExecutor(max_workers=len(clients)) as pool:
        list(pool.map(_ping, clients))
    print(f"[TIMING] warmup: {time.time() - t0:.2f}s")


def create_workflow() -> Coordinator:
    """
    Create and configure the workflow coordinator with all agents

    Returns:
        Configured Coordinator instance
    """
    _warmup_llms()

    # Initialize LLM
    llm = get_llm(temperature=0.0, purpose="agent")

    # Initialize agents
    agents = {
        "Ask": AskAgent(llm=llm),
        "Acquire": AcquireAgent(llm=llm),
        "Appraise": AppraiseAgent(llm=llm),
        "Apply": ApplyAgent(llm=llm),
        "Assess": AssessAgent(llm=llm),
    }

    # Initialize Judge LLM (use fast model for classification tasks)
    judge_llm = JudgeLLM(llm=get_fast_llm(temperature=0.0, purpose="judge"))

    # Initialize Scheduling LLM (use fast model for classification tasks)
    scheduling_llm = SchedulingLLM(llm=get_fast_llm(temperature=0.0, purpose="scheduling"))

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
    direct = state.get("direct_answer_output")

    if state.get("route_type") == "direct_answer" and direct:
        output.append(f"A: {direct.get('answer', '[empty]')}")
        output.append("")
        basis = direct.get("answer_basis")
        guideline = direct.get("guideline_source")
        if basis:
            output.append(f"   Answer Basis            : {basis}")
        if guideline:
            output.append(f"   Guideline Source        : {guideline}")
        caveats = direct.get("caveats") or []
        if caveats:
            output.append("   Caveats                 :")
            for c in caveats:
                output.append(f"     • {c}")
    elif rec:
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
        stats = get_cache_stats()
        # huatuogpt.cn gateway reports prefix caching by reducing prompt_tokens
        # rather than via cached_tokens — so we surface raw totals; comparing
        # prompt_tokens across runs of the same workflow shows the cache effect.
        print(
            f"[CACHE] calls={stats['calls']} "
            f"total_prompt_tokens={stats['prompt_tokens']} "
            f"cached_tokens(openai-style)={stats['cached_tokens']}"
        )

        # Per-purpose TTFT (time-to-first-token) summary from streamed calls.
        ttft_data = get_ttft_samples()
        if ttft_data:
            print("[TTFT] per-purpose summary (ttft / total elapsed in seconds):")
            for purpose, samples in sorted(ttft_data.items()):
                valid_ttft = [s["ttft"] for s in samples if s["ttft"] is not None]
                elapsed = [s["elapsed"] for s in samples]
                if not valid_ttft:
                    continue
                avg_ttft = sum(valid_ttft) / len(valid_ttft)
                med_ttft = sorted(valid_ttft)[len(valid_ttft) // 2]
                avg_elapsed = sum(elapsed) / len(elapsed)
                print(
                    f"  {purpose:14s} n={len(samples):2d}  "
                    f"ttft avg={avg_ttft:5.2f}s med={med_ttft:5.2f}s  "
                    f"elapsed avg={avg_elapsed:5.2f}s"
                )
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
