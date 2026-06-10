"""Multi-run EBM-only measurement to beat the single-run eval noise.

Runs the full EBM 5A pipeline K times per question, judges each, and aggregates
per-question safety_category rate + mean total + mean safety_dim/uncertainty so
we can read STABLE estimates (single-run swings ±20 and the B-class cap flips
NONE<->B run-to-run — see project_bclass_safety_render_state).

Usage:
  PYTHONIOENCODING=utf-8 JUDGE_MODEL=gpt-5.5 python scripts/measure_safety_multirun.py [questions.json] [K]
Defaults: questions=scripts/baseline_subset_5.json, K=3. Saves measure_safety_multirun.json.
"""
import sys, json, importlib.util
from pathlib import Path
from collections import defaultdict
from statistics import mean

from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.baselines import ebm5a_runner

_spec = importlib.util.spec_from_file_location("evaluate_judge", ROOT / "scripts" / "evaluate_judge.py")
_mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
judge = _mod.evaluate

qfile = sys.argv[1] if len(sys.argv) > 1 else "scripts/baseline_subset_5.json"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 3
OUT = ROOT / "measure_safety_multirun.json"
questions = json.loads((ROOT / qfile).read_text(encoding="utf-8"))

rows: list[dict] = []
def _save():
    OUT.write_text(json.dumps({"K": K, "qfile": qfile, "rows": rows}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

for r in range(1, K + 1):
    for q in questions:
        qid, question = q["id"], q["question"]
        print(f"[run {r}/{K}] {qid}: {question[:40]}...", flush=True)
        try:
            res, _ = ebm5a_runner.run(question)
            txt = res.response_text
        except Exception as e:
            rows.append({"run": r, "id": qid, "error": f"pipeline:{e}"}); _save(); continue
        try:
            jr = judge(question, txt)
            ds = jr.dim_scores or {}
            rows.append({"run": r, "id": qid, "safety_category": jr.safety_category,
                         "total": jr.total_score, "safety_dim": ds.get("safety_risk_control"),
                         "uncertainty": ds.get("uncertainty_boundary"),
                         "medical_accuracy": ds.get("medical_accuracy")})
            print(f"    -> total={jr.total_score} cat={jr.safety_category} safeDim={ds.get('safety_risk_control')}", flush=True)
        except Exception as e:
            rows.append({"run": r, "id": qid, "error": f"judge:{e}"})
        _save()

# ── aggregate ──
by_q = defaultdict(list)
for x in rows:
    if "error" not in x:
        by_q[x["id"]].append(x)
print("\n" + "=" * 72)
print(f"AGGREGATE over K={K} runs ({qfile})")
print(f"{'Q':5} {'n':3} {'B-rate':7} {'mean total':11} {'mean safeDim':13} {'mean unc'}")
for qid in [q["id"] for q in questions]:
    xs = by_q.get(qid, [])
    if not xs:
        print(f"{qid:5} 0   (no valid judged runs)"); continue
    n = len(xs)
    brate = sum(1 for x in xs if x["safety_category"] == "B") / n
    arate = sum(1 for x in xs if x["safety_category"] == "A") / n
    mt = mean(x["total"] for x in xs if x["total"] is not None)
    msd = mean(x["safety_dim"] for x in xs if x["safety_dim"] is not None)
    munc = mean(x["uncertainty"] for x in xs if x["uncertainty"] is not None)
    cats = "/".join(str(x["safety_category"]) for x in xs)
    print(f"{qid:5} {n:<3} {brate:<7.2f} {mt:<11.1f} {msd:<13.1f} {munc:.1f}   cats=[{cats}] A-rate={arate:.2f}")
err = [x for x in rows if "error" in x]
if err:
    print(f"\n{len(err)} errored cell(s) — rerun or rejudge:", [(x['run'], x['id']) for x in err])
print(f"\nsaved {OUT.name}")
