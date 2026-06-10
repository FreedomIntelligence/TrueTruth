"""Full 24-question EBM-only score sweep: report RAW (pre-cap = sum of 7 dims) and
CAPPED (post A->40 / B->60 cap = judge total_score) per question.

Shows exactly how much the safety cap costs each answer (raw - capped) and the
overall raw-vs-capped picture after the KB drug-safety block + strength-sync (A).

Usage:
  PYTHONIOENCODING=utf-8 JUDGE_MODEL=gpt-5.5 python scripts/measure_full24.py [questions.json] [K]
Defaults: questions=scripts/baseline_questions_24.json, K=1. Saves measure_full24.json.
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

qfile = sys.argv[1] if len(sys.argv) > 1 else "scripts/baseline_questions_24.json"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 1
OUT = ROOT / "measure_full24.json"
questions = json.loads((ROOT / qfile).read_text(encoding="utf-8"))

rows: list[dict] = []
def _save():
    OUT.write_text(json.dumps({"K": K, "qfile": qfile, "rows": rows}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

for r in range(1, K + 1):
    for q in questions:
        qid, question = q["id"], q["question"]
        print(f"[run {r}/{K}] {qid}", flush=True)
        try:
            res, _ = ebm5a_runner.run(question)
            txt = res.response_text
        except Exception as e:
            rows.append({"run": r, "id": qid, "error": f"pipeline:{e}"}); _save(); continue
        try:
            jr = judge(question, txt)
            ds = jr.dim_scores or {}
            raw = round(sum(v for v in ds.values() if isinstance(v, (int, float))), 1)
            rows.append({
                "run": r, "id": qid,
                "raw": raw,                       # pre-cap = sum of 7 dims
                "capped": jr.total_score,         # post A->40 / B->60 cap
                "cap_cost": round(raw - jr.total_score, 1),
                "safety_category": jr.safety_category,
                "dim_scores": ds,
                "safety_violations": jr.safety_violations,
                "response_text": txt,
            })
            print(f"    -> raw={raw} capped={jr.total_score} cat={jr.safety_category} cost={round(raw-jr.total_score,1)}", flush=True)
        except Exception as e:
            rows.append({"run": r, "id": qid, "error": f"judge:{e}", "response_text": txt})
        _save()

# ── aggregate ──
ok = [x for x in rows if "error" not in x]
by_q = defaultdict(list)
for x in ok:
    by_q[x["id"]].append(x)

print("\n" + "=" * 78)
print(f"FULL-24 RAW vs CAPPED (K={K}, {qfile})")
print(f"{'Q':5} {'raw':6} {'capped':7} {'cost':6} {'cat'}")
agg_raw, agg_capped = [], []
catcount = defaultdict(int)
for qid in [q["id"] for q in questions]:
    xs = by_q.get(qid, [])
    if not xs:
        print(f"{qid:5} (no valid run)"); continue
    raw = mean(x["raw"] for x in xs)
    capped = mean(x["capped"] for x in xs)
    cats = "/".join(str(x["safety_category"]) for x in xs)
    agg_raw.append(raw); agg_capped.append(capped)
    for x in xs: catcount[x["safety_category"]] += 1
    print(f"{qid:5} {raw:<6.1f} {capped:<7.1f} {raw-capped:<6.1f} {cats}")

n = len(agg_raw)
print("-" * 78)
if n:
    print(f"MEAN  raw={mean(agg_raw):.1f}  capped={mean(agg_capped):.1f}  cap_cost={mean(agg_raw)-mean(agg_capped):.1f}")
    tot = sum(catcount.values())
    print(f"Cap distribution over {tot} judged runs: " +
          ", ".join(f"{k}={v}({v/tot*100:.0f}%)" for k, v in sorted(catcount.items())))
    capped_qs = [qid for qid in by_q if any(x["safety_category"] in ("A", "B") for x in by_q[qid])]
    print(f"Questions ever capped (A or B): {len(capped_qs)}/{len(by_q)} -> {sorted(capped_qs)}")
err = [x for x in rows if "error" in x]
if err:
    print(f"\n{len(err)} errored cell(s): {[(x['run'], x['id']) for x in err]}")
print(f"\nsaved {OUT.name}")
