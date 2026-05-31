"""多轮一致性测试：对 batch_test_questions.py 的 30 道题跑 N 次，
统计推荐强度、证据质量在所有轮次中的一致率。

用法：
  py scripts/multi_run_consistency.py --runs 5
  py scripts/multi_run_consistency.py --runs 3 --questions 1-10

输出：
  logs/multi_run/summary_<RUN_ID>.json   — 所有轮次的原始结果
  logs/multi_run/report_<RUN_ID>.md      — 一致性统计报告
"""
import argparse
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

# Same question list as batch_test_questions.py
QUESTIONS = [
    "高血压患者首选 ARB 还是 ACEI？",
    "ARB 联合 CCB 治疗中重度原发性高血压的疗效如何？",
    "氨氯地平与硝苯地平在高血压治疗中的比较",
    "噻嗪类利尿剂用于高血压一线治疗的证据",
    "β 受体阻滞剂在高血压治疗中的地位",
    "单药治疗高血压血压不达标时如何加药？",
    "高血压患者何时需要三联降压方案？",
    "缬沙坦与氯沙坦在高血压患者中的降压疗效比较",
    "老年高血压患者的降压目标值应设多少？",
    "高血压合并 CKD 患者首选哪类降压药？",
    "高血压合并糖尿病患者的降压方案",
    "妊娠期高血压的安全降压药物选择",
    "高血压合并冠心病患者的降压治疗",
    "高血压合并心力衰竭的降压策略",
    "儿童高血压的诊断标准与治疗原则",
    "难治性高血压的定义和处理方法",
    "SGLT2 抑制剂对高血压的降压效果",
    "肾脏去神经术（Renal Denervation）治疗高血压的证据",
    "醛固酮合酶抑制剂在高血压中的应用",
    "高血压患者生活方式干预（运动、饮食）的降压效果",
    "家庭血压监测与诊室血压在高血压管理中的作用",
    "中药天麻钩藤饮治疗高血压的临床证据",
    "针灸降血压的效果如何？",
    "中西医结合治疗高血压与单纯西医治疗的比较",
    "二甲双胍治疗 2 型糖尿病的效果",
    "阿司匹林用于冠心病二级预防",
    "乳腺癌的筛查推荐年龄",
    "儿童哮喘的阶梯治疗方案",
    "他汀类药物治疗高胆固醇血症",
    "幽门螺旋杆菌的根除方案",
]

LOG_DIR = Path("logs/multi_run")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def run_one_question(question: str, timeout: int = 900) -> dict:
    """Run a single question and return structured result."""
    t0 = time.time()
    proc = subprocess.Popen(
        [sys.executable, "src/main.py", question],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, "PYTHONPATH": str(Path.cwd())},
    )
    lines = []
    strength = quality = acquire_query = None
    out_of_domain = insufficient = False
    error = None
    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            if m := re.search(r"Strength\s*:\s*(.+)", line):
                strength = m.group(1).strip()
            if m := re.search(r"Evidence Quality\s*:\s*(.+)", line):
                quality = m.group(1).strip()
            if m := re.search(r"Acquire NL query.*?: (.+)", line):
                acquire_query = m.group(1).strip()
            if "out_of_domain" in line or "专注于高血压" in line:
                out_of_domain = True
            if "Insufficient Evidence" in line or "insufficient_evidence" in line:
                insufficient = True
            if "Traceback" in line or ("Error:" in line and "TIMING" not in line):
                error = line
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        error = "TIMEOUT"
    except Exception as e:
        error = str(e)
    return {
        "question": question,
        "strength": strength,
        "quality": quality,
        "acquire_query": acquire_query,
        "out_of_domain": out_of_domain,
        "insufficient": insufficient,
        "error": error,
        "elapsed_s": round(time.time() - t0, 1),
    }


def run_batch(run_idx: int, questions: list[str]) -> list[dict]:
    """Run all questions once and return results list."""
    results = []
    for i, q in enumerate(questions):
        print(f"  [{run_idx+1}][{i+1:02d}/{len(questions)}] {q[:60]}", flush=True)
        r = run_one_question(q)
        status = "✓"
        if r["error"]:
            status = "✗"
        elif r["out_of_domain"]:
            status = "OOD"
        elif r["insufficient"]:
            status = "InsuffEvid"
        print(f"    {status} {r['elapsed_s']}s  str={r['strength']}  q={r['quality']}", flush=True)
        results.append(r)
    return results


def compute_consistency(all_runs: list[list[dict]]) -> dict:
    """Compute per-question and overall consistency across N runs."""
    n_runs = len(all_runs)
    n_q = len(all_runs[0])
    stats = []

    for qi in range(n_q):
        q_results = [all_runs[r][qi] for r in range(n_runs)]
        question = q_results[0]["question"]

        # Skip OOD (fast reject, strength not meaningful)
        if all(r["out_of_domain"] for r in q_results):
            stats.append({"question": question, "skip": "OOD", "strength_agree": None, "quality_agree": None})
            continue
        # Only consider non-error runs
        valid = [r for r in q_results if not r["error"] and not r["out_of_domain"]]
        if len(valid) < 2:
            stats.append({"question": question, "skip": "insufficient_valid", "strength_agree": None, "quality_agree": None})
            continue

        strengths = [r["strength"] for r in valid if r["strength"]]
        qualities = [r["quality"] for r in valid if r["quality"]]
        queries = [r["acquire_query"] for r in valid if r["acquire_query"]]

        strength_mode = max(set(strengths), key=strengths.count) if strengths else None
        quality_mode = max(set(qualities), key=qualities.count) if qualities else None
        str_agree = strengths.count(strength_mode) / len(strengths) if strengths else None
        q_agree = qualities.count(quality_mode) / len(qualities) if qualities else None

        # Query uniqueness: ratio of unique queries to total
        unique_q_ratio = len(set(queries)) / len(queries) if queries else None

        stats.append({
            "question": question,
            "skip": None,
            "strength_mode": strength_mode,
            "quality_mode": quality_mode,
            "strength_agreement": round(str_agree, 2) if str_agree else None,
            "quality_agreement": round(q_agree, 2) if q_agree else None,
            "query_unique_ratio": round(unique_q_ratio, 2) if unique_q_ratio else None,
            "strengths_seen": list(set(strengths)),
            "queries_seen": list(set(queries)),
            "n_valid": len(valid),
        })

    return {"per_question": stats, "n_runs": n_runs}


def write_report(consistency: dict, run_id: str) -> Path:
    stats = consistency["per_question"]
    n_runs = consistency["n_runs"]

    valid = [s for s in stats if s.get("strength_agreement") is not None]
    if not valid:
        return None

    avg_str = sum(s["strength_agreement"] for s in valid) / len(valid)
    avg_q = sum(s["quality_agreement"] for s in valid if s.get("quality_agreement")) / max(1, len([s for s in valid if s.get("quality_agreement")]))
    perfect_str = sum(1 for s in valid if s["strength_agreement"] == 1.0)
    inconsistent = [s for s in valid if s["strength_agreement"] < 1.0]

    lines = [
        f"# Multi-Run Consistency Report — {run_id}",
        f"**Runs**: {n_runs}  **Valid questions**: {len(valid)}/{len(stats)}",
        "",
        "## Summary",
        f"| Metric | Value |",
        f"|---|---|",
        f"| 推荐强度平均一致率 | {avg_str:.1%} |",
        f"| 证据质量平均一致率 | {avg_q:.1%} |",
        f"| 100% 一致题数 | {perfect_str}/{len(valid)} |",
        f"| 有任意不一致题数 | {len(inconsistent)}/{len(valid)} |",
        "",
        "## 不一致题目（strength_agreement < 1.00）",
        "",
    ]
    for s in sorted(inconsistent, key=lambda x: x["strength_agreement"]):
        lines.append(f"### [{s['strength_agreement']:.0%}] {s['question'][:70]}")
        lines.append(f"- 最多见强度: **{s['strength_mode']}** (mode)")
        lines.append(f"- 出现过的强度: {s['strengths_seen']}")
        if s.get("query_unique_ratio") and s["query_unique_ratio"] > 0:
            lines.append(f"- Query 变异率: {s['query_unique_ratio']:.0%} unique")
            for q in s.get("queries_seen", [])[:3]:
                lines.append(f"  - `{q[:120]}`")
        lines.append("")

    lines += [
        "## 所有题目一致率",
        "| # | 一致率(强度) | 一致率(质量) | Query变异率 | 题目 |",
        "|---|---|---|---|---|",
    ]
    for i, s in enumerate(stats, 1):
        if s.get("skip"):
            lines.append(f"| {i:02d} | — | — | — | {s['question'][:60]} ({s['skip']}) |")
        else:
            str_pct = f"{s['strength_agreement']:.0%}" if s.get("strength_agreement") else "—"
            q_pct = f"{s['quality_agreement']:.0%}" if s.get("quality_agreement") else "—"
            uq = f"{s['query_unique_ratio']:.0%}" if s.get("query_unique_ratio") else "—"
            lines.append(f"| {i:02d} | {str_pct} | {q_pct} | {uq} | {s['question'][:60]} |")

    report_path = LOG_DIR / f"report_{run_id}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="Number of runs (default 3)")
    parser.add_argument("--questions", type=str, default="1-24",
                        help="Question range, e.g. '1-24' (default: domain questions only, skip OOD 25-30)")
    args = parser.parse_args()

    # Parse question range
    if "-" in args.questions:
        lo, hi = args.questions.split("-")
        q_indices = list(range(int(lo) - 1, int(hi)))
    else:
        q_indices = [int(x) - 1 for x in args.questions.split(",")]
    questions = [QUESTIONS[i] for i in q_indices if i < len(QUESTIONS)]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = LOG_DIR / f"summary_{run_id}.json"

    print(f"Multi-Run Consistency Test — {run_id}")
    print(f"Runs: {args.runs}  Questions: {len(questions)} ({args.questions})")
    print("=" * 60)

    all_runs = []
    for run_idx in range(args.runs):
        print(f"\n=== Run {run_idx + 1}/{args.runs} ===")
        results = run_batch(run_idx, questions)
        all_runs.append(results)
        # Save incrementally
        summary_path.write_text(json.dumps({"runs": all_runs, "meta": {
            "run_id": run_id, "n_runs": args.runs, "questions": questions
        }}, ensure_ascii=False, indent=2), encoding="utf-8")

    consistency = compute_consistency(all_runs)
    report_path = write_report(consistency, run_id)

    # Print summary
    valid = [s for s in consistency["per_question"] if s.get("strength_agreement") is not None]
    if valid:
        avg = sum(s["strength_agreement"] for s in valid) / len(valid)
        perfect = sum(1 for s in valid if s["strength_agreement"] == 1.0)
        print(f"\n{'='*60}")
        print(f"CONSISTENCY SUMMARY ({args.runs} runs)")
        print(f"{'='*60}")
        print(f"推荐强度平均一致率: {avg:.1%}")
        print(f"100%一致题数: {perfect}/{len(valid)}")
        print(f"Report: {report_path}")
        print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
