"""对 baseline 结果 JSON 中所有 judge_result.error 的单元格，用已存的 response_text 重判一次。
评委确定性，截断/非法 JSON 通常重试即过。不重跑 pipeline。
用法: JUDGE_MODEL=gpt-5.5 python scripts/rejudge_errors.py d1_baselines_24.json
"""
import sys, json, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("evaluate_judge", ROOT / "scripts" / "evaluate_judge.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
judge = mod.evaluate

path = Path(sys.argv[1])
d = json.loads(path.read_text(encoding="utf-8"))
qs = d.get("questions", d if isinstance(d, list) else [])
order = ["ebm_5a", "direct_llm", "vanilla_rag", "cot_rag", "med_r2"]

fixed = failed = 0
for q in qs:
    for p in order:
        e = q["pipelines"].get(p, {})
        if "error" in e:
            continue
        jr = e.get("judge_result", {})
        if "error" not in jr:
            continue
        txt = e.get("response_text")
        if not txt:
            print(f"  SKIP {q['id']}/{p}: no response_text"); failed += 1; continue
        print(f"  rejudge {q['id']}/{p} ...", flush=True)
        try:
            r = judge(q["question"], txt)
            e["judge_result"] = {
                "total_score": r.total_score, "dim_scores": r.dim_scores,
                "dim_justifications": r.dim_justifications,
                "safety_category": r.safety_category,
                "safety_violations": r.safety_violations, "summary": r.summary,
            }
            print(f"    -> {r.total_score}/100 safety={r.safety_category}")
            fixed += 1
        except Exception as ex:
            print(f"    STILL FAILED: {ex}"); failed += 1

path.write_text(json.dumps(d, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"\nfixed={fixed} failed={failed} -> saved {path.name}")
