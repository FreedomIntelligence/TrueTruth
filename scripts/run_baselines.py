#!/usr/bin/env python3
"""
Baseline Comparison: EBM 5A vs simpler pipelines.

Runs 5 pipelines (Direct LLM, Vanilla RAG, CoT-RAG, Med-R², EBM 5A) on the
same clinical questions, then scores each output using the 7-dimension
100-point LLM-Judge rubric from 评价标准.md.

Usage:
    python scripts/run_baselines.py --questions scripts/baseline_questions.json
    python scripts/run_baselines.py --question "高血压患者首选 ARB 还是 ACEI？"
    python scripts/run_baselines.py --questions ... --skip-ebm
    python scripts/run_baselines.py --questions ... --output report.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.baselines.protocol import BaselineResult
from src.config.llm_config import get_llm

# Import evaluate_judge — it lives in scripts/ which isn't a package,
# so we use importlib to load it by file path.
import importlib.util
_judge_spec = importlib.util.spec_from_file_location(
    "evaluate_judge", _PROJECT_ROOT / "scripts" / "evaluate_judge.py"
)
_judge_mod = importlib.util.module_from_spec(_judge_spec)
_judge_spec.loader.exec_module(_judge_mod)
judge_evaluate = _judge_mod.evaluate
compute_objective_metrics = _judge_mod.compute_objective_metrics

PIPELINE_ORDER = ["direct_llm", "vanilla_rag", "cot_rag", "med_r2", "ebm_5a"]

DIM_LABELS = {
    "medical_accuracy": ("Acc", 20),
    "evidence_quality": ("Evid", 20),
    "relevance": ("Rel", 10),
    "safety_risk_control": ("Safe", 20),
    "individualization": ("Indiv", 10),
    "clarity_actionability": ("Clar", 10),
    "uncertainty_boundary": ("Uncert", 10),
}


def run_single_question(
    question: str,
    skip_ebm: bool = False,
    llm=None,
) -> dict:
    """Run all pipelines on a single question, judge each, return results dict."""
    from src.baselines import direct_llm, vanilla_rag, cot_rag, medr2_pipeline

    if llm is None:
        llm = get_llm(temperature=0.0, purpose="baseline")

    results: dict[str, dict] = {}

    # ── EBM 5A ────────────────────────────────────────────────────────────────
    if not skip_ebm:
        print("  [ebm_5a] Running full pipeline...")
        try:
            from src.baselines import ebm5a_runner
            ebm_result, captured_ev = ebm5a_runner.run(question)
            results["ebm_5a"] = _evaluate_result(ebm_result, question)
            print(f"  [ebm_5a] Done ({ebm_result.elapsed_s:.1f}s, {len(captured_ev)} evidence docs)")
        except Exception as e:
            print(f"  [ebm_5a] FAILED: {e}")
            results["ebm_5a"] = {"error": str(e)}

    # ── Direct LLM ────────────────────────────────────────────────────────────
    print("  [direct_llm] Running...")
    try:
        r = direct_llm.run(question, llm=llm)
        results["direct_llm"] = _evaluate_result(r, question)
        print(f"  [direct_llm] Done ({r.elapsed_s:.1f}s)")
    except Exception as e:
        print(f"  [direct_llm] FAILED: {e}")
        results["direct_llm"] = {"error": str(e)}
    time.sleep(2)

    # ── Vanilla RAG (independent retrieval) ─────────────────────────────────
    print("  [vanilla_rag] Running (own retrieval)...")
    try:
        r = vanilla_rag.run(question, llm=llm)
        results["vanilla_rag"] = _evaluate_result(r, question)
        print(f"  [vanilla_rag] Done ({r.elapsed_s:.1f}s, {len(r.evidence_used)} docs)")
    except Exception as e:
        print(f"  [vanilla_rag] FAILED: {e}")
        results["vanilla_rag"] = {"error": str(e)}
    time.sleep(2)

    # ── CoT-RAG (independent retrieval) ───────────────────────────────────
    print("  [cot_rag] Running (own retrieval)...")
    try:
        r = cot_rag.run(question, llm=llm)
        results["cot_rag"] = _evaluate_result(r, question)
        print(f"  [cot_rag] Done ({r.elapsed_s:.1f}s, {len(r.evidence_used)} docs)")
    except Exception as e:
        print(f"  [cot_rag] FAILED: {e}")
        results["cot_rag"] = {"error": str(e)}
    time.sleep(2)

    # ── Med-R² (classify→rewrite→retrieve→rerank→CoT) ────────────────────
    print("  [med_r2] Running (Med-R² pipeline)...")
    try:
        r = medr2_pipeline.run(question, llm=llm)
        results["med_r2"] = _evaluate_result(r, question)
        meta = r.metadata
        print(f"  [med_r2] Done ({r.elapsed_s:.1f}s, {len(r.evidence_used)} docs, "
              f"ebm={meta.get('ebm_category')}, nlp={meta.get('nlp_type')}, "
              f"{r.llm_calls} LLM calls)")
    except Exception as e:
        print(f"  [med_r2] FAILED: {e}")
        results["med_r2"] = {"error": str(e)}

    return {
        "question": question,
        "pipelines": results,
    }


def _evaluate_result(result: BaselineResult, question: str) -> dict:
    """Run Judge + objective metrics on a single BaselineResult."""
    entry: dict = {
        "response_text": result.response_text,
        "elapsed_s": result.elapsed_s,
        "llm_calls": result.llm_calls,
        "evidence_used": result.evidence_used,
        "metadata": result.metadata,
    }

    # LLM Judge (7-dim 100pt rubric from 评价标准.md)
    try:
        judge_result = judge_evaluate(question, result.response_text)
        entry["judge_result"] = {
            "total_score": judge_result.total_score,
            "dim_scores": judge_result.dim_scores,
            "dim_justifications": judge_result.dim_justifications,
            "safety_category": judge_result.safety_category,
            "safety_violations": judge_result.safety_violations,
            "summary": judge_result.summary,
        }
    except Exception as e:
        print(f"    [Judge] FAILED: {e}")
        entry["judge_result"] = {"error": str(e)}
    time.sleep(2)

    # Objective metrics
    entry["objective_metrics"] = compute_objective_metrics(result.response_text)

    return entry


# ─── Aggregate Statistics ────────────────────────────────────────────────────

def compute_aggregate(question_results: list[dict]) -> dict:
    """Compute per-pipeline mean scores and pairwise win rates."""
    scores: dict[str, list[float]] = {p: [] for p in PIPELINE_ORDER}
    dim_scores: dict[str, dict[str, list[float]]] = {
        p: {d: [] for d in DIM_LABELS} for p in PIPELINE_ORDER
    }
    safety: dict[str, dict[str, int]] = {
        p: {"A": 0, "B": 0, "NONE": 0} for p in PIPELINE_ORDER
    }
    times: dict[str, list[float]] = {p: [] for p in PIPELINE_ORDER}

    for qr in question_results:
        for pipe in PIPELINE_ORDER:
            entry = qr["pipelines"].get(pipe, {})
            if "error" in entry:
                continue
            jr = entry.get("judge_result", {})
            if "error" in jr:
                continue
            total = jr.get("total_score")
            if total is not None:
                scores[pipe].append(total)
            ds = jr.get("dim_scores", {})
            for dim in DIM_LABELS:
                val = ds.get(dim)
                if val is not None:
                    dim_scores[pipe][dim].append(val)
            cat = jr.get("safety_category", "NONE")
            safety[pipe][cat] = safety[pipe].get(cat, 0) + 1
            elapsed = entry.get("elapsed_s")
            if elapsed is not None:
                times[pipe].append(elapsed)

    def _mean(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    mean_scores = {p: _mean(scores[p]) for p in PIPELINE_ORDER}
    mean_dims = {
        p: {d: _mean(dim_scores[p][d]) for d in DIM_LABELS}
        for p in PIPELINE_ORDER
    }
    mean_times = {p: _mean(times[p]) for p in PIPELINE_ORDER}

    # Pairwise win rates
    wins: dict[str, dict[str, int]] = {}
    for i, pa in enumerate(PIPELINE_ORDER):
        for pb in PIPELINE_ORDER[i + 1:]:
            key = f"{pa}_vs_{pb}"
            w = {pa: 0, pb: 0, "tie": 0}
            for qr in question_results:
                ea = qr["pipelines"].get(pa, {})
                eb = qr["pipelines"].get(pb, {})
                sa = (ea.get("judge_result") or {}).get("total_score")
                sb = (eb.get("judge_result") or {}).get("total_score")
                if sa is None or sb is None:
                    continue
                if sa > sb + 2:
                    w[pa] += 1
                elif sb > sa + 2:
                    w[pb] += 1
                else:
                    w["tie"] += 1
            wins[key] = w

    return {
        "mean_scores": mean_scores,
        "mean_dims": mean_dims,
        "mean_times": mean_times,
        "safety": safety,
        "pairwise_wins": wins,
    }


def print_summary(agg: dict, n_questions: int):
    """Print formatted summary table to console."""
    print("\n" + "=" * 100)
    print(f"BASELINE COMPARISON SUMMARY ({n_questions} questions)")
    print("=" * 100)

    # Header
    dim_headers = "".join(f"{label:<8}" for label, _ in DIM_LABELS.values())
    print(f"{'Pipeline':<15} {'Score':<8} {dim_headers}{'Time':<8}")
    print("-" * 100)

    for pipe in PIPELINE_ORDER:
        ms = agg["mean_scores"].get(pipe)
        if ms is None:
            print(f"{pipe:<15} {'N/A'}")
            continue
        dims = agg["mean_dims"].get(pipe, {})
        dim_vals = "".join(
            f"{dims.get(d, 'N/A'):<8}" if dims.get(d) is not None else f"{'N/A':<8}"
            for d in DIM_LABELS
        )
        mt = agg["mean_times"].get(pipe)
        time_str = f"{mt:.0f}s" if mt is not None else "N/A"
        print(f"{pipe:<15} {ms:<8.1f} {dim_vals}{time_str:<8}")

    # Pairwise wins
    print(f"\nPairwise Win Rates (margin > 2pt):")
    for key, w in agg["pairwise_wins"].items():
        parts = key.split("_vs_")
        if len(parts) == 2:
            pa, pb = parts
            print(f"  {pa} vs {pb}: {w.get(pa, 0)}W / {w.get(pb, 0)}L / {w.get('tie', 0)}T")

    print("=" * 100)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Baseline Comparison for EBM 5A")
    parser.add_argument("--questions", "-q", help="JSON file with question list")
    parser.add_argument("--question", help="Single question to test")
    parser.add_argument("--output", "-o", help="Output JSON report path")
    parser.add_argument("--skip-ebm", action="store_true", help="Skip EBM 5A pipeline (faster, for debugging)")
    args = parser.parse_args()

    if args.question:
        questions = [{"id": "CLI", "question": args.question}]
    elif args.questions:
        qpath = Path(args.questions)
        if not qpath.exists():
            print(f"Error: file not found: {qpath}")
            sys.exit(1)
        questions = json.loads(qpath.read_text(encoding="utf-8"))
    else:
        print("Error: provide --question or --questions")
        sys.exit(1)

    llm = get_llm(temperature=0.0, purpose="baseline")

    print(f"Baseline Comparison — {len(questions)} question(s)")
    if args.skip_ebm:
        print("  (--skip-ebm: EBM 5A pipeline skipped)")
    print("=" * 70)

    output_path = args.output or f"baseline_report_{time.strftime('%Y%m%d_%H%M%S')}.json"

    all_results: list[dict] = []
    for i, q in enumerate(questions):
        qid = q.get("id", f"Q{i+1}")
        question = q["question"]
        print(f"\n[{i+1}/{len(questions)}] {qid}: {question[:60]}...")
        qr = run_single_question(question, skip_ebm=args.skip_ebm, llm=llm)
        qr["id"] = qid
        all_results.append(qr)

        # Incremental save after each question (network-drop resilience).
        Path(output_path).write_text(
            json.dumps({"in_progress": True, "metadata": {"skip_ebm": args.skip_ebm},
                        "questions": all_results}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        # Print per-question mini summary
        for pipe in PIPELINE_ORDER:
            entry = qr["pipelines"].get(pipe, {})
            if "error" in entry:
                print(f"    {pipe}: ERROR")
            else:
                jr = entry.get("judge_result", {})
                score = jr.get("total_score", "?")
                safety = jr.get("safety_category", "?")
                elapsed = entry.get("elapsed_s", "?")
                print(f"    {pipe}: {score}/100  safety={safety}  time={elapsed}s")

    # Aggregate
    agg = compute_aggregate(all_results)
    print_summary(agg, len(questions))

    # Build report
    report = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "num_questions": len(questions),
            "skip_ebm": args.skip_ebm,
        },
        "aggregate": agg,
        "questions": all_results,
    }

    # Save final report (overwrites the incremental in-progress file)
    Path(output_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()
