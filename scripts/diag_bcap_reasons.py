"""Diagnostic: capture WHICH B-class trigger fires on the flaky B-capped questions.

The 3x measurement showed B02/B03/B07 still flip NONE<->B run-to-run with HIGH
safeDim — so the residual B-cap is NOT a safety-content gap. This run captures the
judge's full `safety_violations` + dim_justifications + the response_text for each
run, so we can read which of the 5 B-class triggers actually fires:
  1 缺少重要风险提示 | 2 无明确来源+强推荐 | 3 不确定性不足 | 4 个体化不足 | 5 过度承诺疗效
Triggers 2/5 => (c) overstatement territory. 3/4 => uncertainty/individualization.

Usage:
  PYTHONIOENCODING=utf-8 JUDGE_MODEL=gpt-5.5 python scripts/diag_bcap_reasons.py [K]
Defaults: K=2 runs each over B02/B03/B07. Saves diag_bcap_reasons.json.
"""
import sys, json, importlib.util
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.baselines import ebm5a_runner

_spec = importlib.util.spec_from_file_location("evaluate_judge", ROOT / "scripts" / "evaluate_judge.py")
_mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
judge = _mod.evaluate

K = int(sys.argv[1]) if len(sys.argv) > 1 else 2
OUT = ROOT / "diag_bcap_reasons.json"
allq = json.loads((ROOT / "scripts" / "baseline_subset_5.json").read_text(encoding="utf-8"))
questions = [q for q in allq if q["id"] in ("B02", "B03", "B07")]

rows = []
def _save():
    OUT.write_text(json.dumps({"K": K, "rows": rows}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

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
            rows.append({
                "run": r, "id": qid,
                "safety_category": jr.safety_category,
                "total": jr.total_score,
                "safety_violations": jr.safety_violations,
                "safety_dim": ds.get("safety_risk_control"),
                "evidence_quality": ds.get("evidence_quality"),
                "individualization": ds.get("individualization"),
                "uncertainty": ds.get("uncertainty_boundary"),
                "just_safety": (jr.dim_justifications or {}).get("safety_risk_control"),
                "just_evidence": (jr.dim_justifications or {}).get("evidence_quality"),
                "just_individ": (jr.dim_justifications or {}).get("individualization"),
                "response_text": txt,
            })
            print(f"    -> total={jr.total_score} cat={jr.safety_category} viol={jr.safety_violations}", flush=True)
        except Exception as e:
            rows.append({"run": r, "id": qid, "error": f"judge:{e}", "response_text": txt})
        _save()

# ── summary: which triggers fired on B-capped runs ──
print("\n" + "=" * 72)
print("B-CAPPED runs and their violations:")
for x in rows:
    if x.get("safety_category") == "B":
        print(f"  {x['id']} run{x['run']}: {x.get('safety_violations')}")
print(f"\nsaved {OUT.name}")
