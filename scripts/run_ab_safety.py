#!/usr/bin/env python3
"""A/B harness for the grounded-safety effort (P3 validation).

Runs the full EBM 5A pipeline e2e across:  questions × runs × 2 arms.

  control   = P0 only          (EBM_AB_ARM=control: skip DRUG_SAFETY sub-retrieval,
                                use the pre-P1/P2 baseline Apply prompt)
  treatment = P0 + P1 + P2     (default worktree behaviour: grounded openFDA safety
                                section + Step 1.6 anti-overreach population gate)

The two arms differ ONLY by P1+P2 (toggled via the EBM_AB_ARM env var that
apply_agent.py / acquire_agent.py read at call time). Everything else — P0
renderer/JSON-retry fixes, retrieval, GRADE — is shared.

Scoring reuses the standalone deterministic Judge (temperature=0, seed=42) so
the only source of variation is the generation side, which is exactly what the
within-question volatility metric measures.

Metrics captured per run: total_score, all 7 dim scores, safety_category (A/B/NONE),
safety_violations, JSON-fail flag, backtrack/overreach proxy, elapsed, llm_calls,
objective metrics (length, citation density, drug/effect specificity, clarity).

Usage (run from the worktree root):
    py -3 scripts/run_ab_safety.py --runs 3 --ids B01,B03,B04,B08,B09,B10 \
        --output ab_safety_report.json
    py -3 scripts/run_ab_safety.py --runs 3            # all of baseline_questions.json
    py -3 scripts/run_ab_safety.py --runs 1 --ids B01  # quick smoke (both arms)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import traceback
from pathlib import Path

# Make `src` importable when invoked as a bare script from the worktree root.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DIMS = [
    "medical_accuracy",
    "evidence_quality",
    "relevance",
    "safety_risk_control",
    "individualization",
    "clarity_actionability",
    "uncertainty_boundary",
]


def _load_questions(args) -> list[dict]:
    path = Path(args.questions)
    items = json.loads(path.read_text(encoding="utf-8"))
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        items = [q for q in items if q.get("id") in wanted]
        missing = wanted - {q.get("id") for q in items}
        if missing:
            print(f"[WARN] requested ids not found and skipped: {sorted(missing)}")
    if args.limit:
        items = items[: args.limit]
    return items


def _run_one(arm: str, question: str, judge: bool = True) -> dict:
    """Run one (arm, question) full pipeline + Judge. Never raises.

    judge=False runs the pipeline only (no scoring) — used for behavioural
    smoke tests when no Judge endpoint is configured yet.
    """
    from src.baselines import ebm5a_runner
    from scripts.evaluate_judge import evaluate as judge_evaluate, compute_objective_metrics

    os.environ["EBM_AB_ARM"] = arm

    rec: dict = {"arm": arm, "ok": False, "json_fail": False, "error": None}
    try:
        result, _ev = ebm5a_runner.run(question)
        text = result.response_text or ""
        json_fail = ("[未生成推荐" in text) or (len(text.strip()) == 0)
        rec.update(
            {
                "response_text": text,
                "elapsed_s": result.elapsed_s,
                "llm_calls": result.llm_calls,
                "strength": result.metadata.get("strength"),
                "evidence_quality": result.metadata.get("evidence_quality"),
                "iteration_count": result.metadata.get("iteration_count", 0),
                "assess_needs_backtrack": result.metadata.get("assess_needs_backtrack"),
                "route_type": result.metadata.get("route_type"),
                "evidence_used": result.evidence_used,
                "json_fail": json_fail,
            }
        )
        if not json_fail and judge:
            jr = judge_evaluate(question, text)
            rec["total_score"] = jr.total_score
            # Raw pre-safety-cap dimension sum. The A/B/NONE safety cap (A→40,
            # B→60) flattens total_score, hiding dimension-level P1/P2 effects;
            # raw_score exposes them.
            rec["raw_score"] = round(sum(float(v) for v in jr.dim_scores.values()), 1)
            rec["dim_scores"] = jr.dim_scores
            rec["safety_category"] = jr.safety_category
            rec["safety_violations"] = jr.safety_violations
            rec["judge_summary"] = jr.summary
            rec["objective_metrics"] = compute_objective_metrics(text)
            rec["ok"] = True
        elif not json_fail and not judge:
            # behavioural smoke: capture text + objective metrics, no Judge
            rec["total_score"] = None
            rec["safety_category"] = "NO_JUDGE"
            rec["objective_metrics"] = compute_objective_metrics(text)
            # behavioural markers for the toggle check
            rec["has_safety_section"] = any(
                m in text for m in ("安全性", "禁忌", "特殊人群", "不良反应")
            )
            rec["has_drugsafety_citation"] = "DRUGSAFETY" in text
            rec["ok"] = True
        else:
            # Failed to produce a usable recommendation — treated like the
            # baseline's FAIL bucket; no Judge score.
            rec["total_score"] = None
            rec["safety_category"] = "FAIL"
    except Exception as exc:  # pragma: no cover - resilience path
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc()
        rec["json_fail"] = True
        rec["total_score"] = None
        rec["safety_category"] = "FAIL"
        print(f"[ERROR] arm={arm} run failed: {rec['error']}")
    return rec


def _aggregate(runs: list[dict], arms: list[str], questions: list[dict]) -> dict:
    """Per-arm aggregate: mean score, within-question volatility, distributions."""
    agg: dict = {}
    for arm in arms:
        arm_runs = [r for r in runs if r["arm"] == arm]
        scored = [r for r in arm_runs if r.get("total_score") is not None]
        scores = [r["total_score"] for r in scored]
        raw_scores = [r["raw_score"] for r in scored if r.get("raw_score") is not None]

        # within-question volatility: std of score across runs, per question,
        # averaged across questions that have >=2 scored runs.
        per_q_std = []
        per_q_mean = {}
        for q in questions:
            qid = q["id"]
            q_scores = [
                r["total_score"]
                for r in scored
                if r["question_id"] == qid
            ]
            if q_scores:
                per_q_mean[qid] = round(statistics.mean(q_scores), 2)
            if len(q_scores) >= 2:
                per_q_std.append(statistics.pstdev(q_scores))

        # safety category distribution (incl FAIL)
        safety_dist: dict = {}
        for r in arm_runs:
            cat = r.get("safety_category", "NONE")
            safety_dist[cat] = safety_dist.get(cat, 0) + 1

        # dim means (only scored runs)
        dim_means = {}
        for d in DIMS:
            vals = [r["dim_scores"].get(d) for r in scored if r.get("dim_scores")]
            vals = [v for v in vals if v is not None]
            if vals:
                dim_means[d] = round(statistics.mean(vals), 2)

        # backtrack / overreach proxy
        backtracks = sum(1 for r in arm_runs if r.get("assess_needs_backtrack"))
        json_fails = sum(1 for r in arm_runs if r.get("json_fail"))

        obj = [r["objective_metrics"] for r in scored if r.get("objective_metrics")]
        mean_len = round(statistics.mean([o["response_length"] for o in obj]), 0) if obj else None
        mean_cit = round(statistics.mean([o["citation_count"] for o in obj]), 2) if obj else None

        agg[arm] = {
            "n_runs": len(arm_runs),
            "n_scored": len(scored),
            "mean_score": round(statistics.mean(scores), 2) if scores else None,
            "mean_raw_score": round(statistics.mean(raw_scores), 2) if raw_scores else None,
            "safety_trigger_count": sum(1 for r in arm_runs if r.get("safety_category") in ("A", "B")),
            "score_stdev_overall": round(statistics.pstdev(scores), 2) if len(scores) >= 2 else None,
            "within_question_volatility": round(statistics.mean(per_q_std), 2) if per_q_std else None,
            "per_question_mean": per_q_mean,
            "safety_distribution": safety_dist,
            "json_fail_count": json_fails,
            "backtrack_count": backtracks,
            "dim_means": dim_means,
            "mean_elapsed_s": round(statistics.mean([r["elapsed_s"] for r in arm_runs if r.get("elapsed_s")]), 1)
            if any(r.get("elapsed_s") for r in arm_runs) else None,
            "mean_llm_calls": round(statistics.mean([r["llm_calls"] for r in arm_runs if r.get("llm_calls")]), 1)
            if any(r.get("llm_calls") for r in arm_runs) else None,
            "mean_response_length": mean_len,
            "mean_citation_count": mean_cit,
        }
    return agg


def _print_summary(agg: dict, arms: list[str]) -> None:
    print("\n" + "=" * 64)
    print("A/B SAFETY-GROUNDING SUMMARY")
    print("=" * 64)
    for arm in arms:
        a = agg[arm]
        print(f"\n── arm = {arm} ── ({a['n_scored']}/{a['n_runs']} scored)")
        print(f"  mean_score (capped)   : {a['mean_score']}")
        print(f"  mean_raw_score        : {a['mean_raw_score']}  (pre safety-cap)")
        print(f"  safety triggers (A+B) : {a['safety_trigger_count']} / {a['n_runs']}")
        print(f"  within-Q volatility   : {a['within_question_volatility']}  (lower=better)")
        print(f"  overall score stdev   : {a['score_stdev_overall']}")
        print(f"  safety distribution   : {a['safety_distribution']}")
        print(f"  json_fail / backtrack : {a['json_fail_count']} / {a['backtrack_count']}")
        print(f"  clarity / relevance   : {a['dim_means'].get('clarity_actionability')} / {a['dim_means'].get('relevance')}")
        print(f"  safety_risk_control   : {a['dim_means'].get('safety_risk_control')}")
        print(f"  mean len / citations  : {a['mean_response_length']} / {a['mean_citation_count']}")
        print(f"  mean elapsed / calls  : {a['mean_elapsed_s']}s / {a['mean_llm_calls']}")
    if "control" in agg and "treatment" in agg:
        c, t = agg["control"], agg["treatment"]
        if c["mean_score"] is not None and t["mean_score"] is not None:
            print("\n── treatment − control ──")
            print(f"  Δ mean_score (capped) : {round(t['mean_score'] - c['mean_score'], 2):+}")
            if c['mean_raw_score'] is not None and t['mean_raw_score'] is not None:
                print(f"  Δ mean_raw_score      : {round(t['mean_raw_score'] - c['mean_raw_score'], 2):+}  (want > 0)")
            print(f"  Δ safety triggers     : {t['safety_trigger_count'] - c['safety_trigger_count']:+}  (want < 0)")
            if c["within_question_volatility"] and t["within_question_volatility"]:
                print(f"  Δ volatility          : {round(t['within_question_volatility'] - c['within_question_volatility'], 2):+}  (want < 0)")
            print(f"  Δ clarity             : {round((t['dim_means'].get('clarity_actionability') or 0) - (c['dim_means'].get('clarity_actionability') or 0), 2):+}")
            print(f"  Δ safety_risk_control : {round((t['dim_means'].get('safety_risk_control') or 0) - (c['dim_means'].get('safety_risk_control') or 0), 2):+}")
    print("=" * 64 + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="A/B harness for grounded-safety (P3)")
    p.add_argument("--questions", default=str(_ROOT / "scripts" / "baseline_questions.json"))
    p.add_argument("--ids", default="", help="comma-separated question ids subset, e.g. B01,B03")
    p.add_argument("--runs", type=int, default=3, help="runs per (arm, question)")
    p.add_argument("--arms", default="control,treatment")
    p.add_argument("--limit", type=int, default=0, help="cap number of questions")
    p.add_argument("--sleep", type=float, default=3.0, help="seconds between runs")
    p.add_argument("--no-judge", action="store_true", help="run pipeline only, skip scoring (behavioural smoke)")
    p.add_argument("--resume", action="store_true",
                   help="reuse OK runs already in --output; only re-run failed/missing (qid,arm,run) cells")
    p.add_argument("--output", default=str(_ROOT / "ab_safety_report.json"))
    args = p.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    questions = _load_questions(args)
    total = len(arms) * len(questions) * args.runs
    print(f"[A/B] arms={arms} questions={[q['id'] for q in questions]} runs={args.runs} → {total} pipeline runs")

    runs: list[dict] = []
    out_path = Path(args.output)
    # Resume: carry forward OK cells from a prior (possibly network-interrupted)
    # run, re-run only the failed/missing (qid, arm, run_idx) cells.
    done_cells: set = set()
    if args.resume and out_path.exists():
        prior = json.loads(out_path.read_text(encoding="utf-8")).get("runs", [])
        for r in prior:
            cell = (r.get("question_id"), r.get("arm"), r.get("run_idx"))
            if r.get("ok") and r.get("total_score") is not None:
                done_cells.add(cell)
                runs.append(r)
        print(f"[A/B] resume: carried {len(done_cells)} OK cells, will re-run the rest")

    idx = 0
    t_start = time.time()
    # Interleave arms tightly per (question, run) so any time-correlated API
    # drift hits both arms equally.
    for q in questions:
        for run_idx in range(args.runs):
            for arm in arms:
                idx += 1
                if (q["id"], arm, run_idx) in done_cells:
                    print(f"[A/B] ({idx}/{total}) q={q['id']} run={run_idx+1} arm={arm} :: SKIP (already OK)")
                    continue
                print(f"\n[A/B] ({idx}/{total}) q={q['id']} run={run_idx+1} arm={arm} :: {q['question']}")
                rec = _run_one(arm, q["question"], judge=not args.no_judge)
                rec["question_id"] = q["id"]
                rec["question"] = q["question"]
                rec["run_idx"] = run_idx
                sc = rec.get("total_score")
                print(f"[A/B] → score={sc} safety={rec.get('safety_category')} "
                      f"elapsed={rec.get('elapsed_s')}s calls={rec.get('llm_calls')}")
                runs.append(rec)
                # Incremental save so a crash mid-batch keeps partial data.
                out_path.write_text(
                    json.dumps({"in_progress": True, "runs": runs}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                if args.sleep:
                    time.sleep(args.sleep)

    agg = _aggregate(runs, arms, questions)
    report = {
        "metadata": {
            "arms": arms,
            "question_ids": [q["id"] for q in questions],
            "runs_per_cell": args.runs,
            "total_runs": total,
            "wall_clock_s": round(time.time() - t_start, 1),
            "judge_model": os.getenv("JUDGE_MODEL", os.getenv("EVAL_MODEL", "gpt-4o")),
        },
        "aggregate": agg,
        "runs": runs,
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_summary(agg, arms)
    print(f"[A/B] full report → {out_path}")


if __name__ == "__main__":
    main()
