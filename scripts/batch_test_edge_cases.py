"""批量运行边界题，验证 pipeline 在以下场景的行为：
1. 高血压急症（非慢性治疗类题）
2. 领域内但数据库内容缺口
3. OOD 灰色地带（高血压相关但不是降压药疗效比较）
4. 证据冲突场景
5. 诊断/预后类 EBM 问题（非 Therapy 类型）
"""
import subprocess
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

QUESTIONS = [
    # ── 高血压急症（非慢性 Therapy 题，测试文献检索路径是否切换）──────────────
    "高血压急症（收缩压>180mmHg 伴急性意识改变），应选哪种静脉降压药？降压速度和目标血压如何设定？",

    # ── 数据库内容缺口（应稳定走 content gap → Insufficient Evidence）────────
    "螺内酯在难治性高血压中的剂量滴定方案：25mg/d 到 50mg/d 加量的证据",
    "肾动脉支架置入 vs 最优药物治疗高血压合并肾动脉狭窄的对比证据",

    # ── OOD 灰色地带（与高血压有关联，但主问题不是降压疗效）────────────────
    "高血压患者是否应常规使用阿司匹林进行心血管一级预防？",
    "高血压合并房颤患者，NOAC 与常用降压药之间的相互作用如何？",
    "利尿剂治疗高血压期间出现急性痛风发作，如何调整降压方案？",

    # ── 证据冲突（SPRINT vs ACCORD，测试 Appraise Inconsistency 处理）──────
    "SPRINT 研究支持强化降压（<120mmHg），ACCORD 在糖尿病患者未见获益，临床应如何统一推荐血压目标？",

    # ── 诊断类 EBM 题（非 Therapy，PICO Outcome 是诊断准确性）────────────────
    "家庭血压监测与动态血压监测（ABPM）在诊断白大衣高血压中的准确性比较",
]

# 每道题的预期行为标注（仅供分析参考，不影响运行）
EXPECTED_BEHAVIOR = {
    0: "hypertension_acute — 文献类型切换（急症 RCT）；数据库可能无相关文献→content gap",
    1: "content_gap — PATHWAY-2 未入库，应识别为内容缺口输出 Insufficient Evidence",
    2: "content_gap — 肾动脉狭窄介入 vs 药物 RCT 可能无入库，测试 content gap 路径",
    3: "ood_borderline — 阿司匹林一级预防，Ask agent 需判断是否领域内",
    4: "ood_borderline — 药物相互作用，主问题不是降压疗效",
    5: "ood_borderline — 痛风并发症处理，降压为背景",
    6: "conflicting_evidence — Inconsistency downgrade 触发，Apply 应表达矛盾而非选边",
    7: "diagnosis_pico — 诊断准确性问题，PICO Outcome = sensitivity/specificity",
}

LOG_DIR = Path("logs/edge_case_test")
LOG_DIR.mkdir(parents=True, exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
SUMMARY_FILE = LOG_DIR / f"summary_{RUN_ID}.json"
FULL_LOG = LOG_DIR / f"full_{RUN_ID}.log"


def run_question(idx: int, question: str) -> dict:
    expected = EXPECTED_BEHAVIOR.get(idx, "unknown")
    print(f"\n[{idx+1:02d}/{len(QUESTIONS)}] {question}", flush=True)
    print(f"  Expected: {expected}", flush=True)
    t_start = time.time()
    first_char_time = None

    proc = subprocess.Popen(
        [sys.executable, "src/main.py", question],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, "PYTHONPATH": str(Path.cwd())},
    )

    output_lines = []
    error = None
    out_of_domain = False
    insufficient_evidence = False
    total_timing = None
    ask_timing = None
    acquire_timing = None
    appraise_timing = None
    apply_timing = None
    scheduling_decisions = []

    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            output_lines.append(line)

            if first_char_time is None and line.strip() and not line.startswith("Processing") and not line.startswith("Question"):
                first_char_time = time.time() - t_start

            if m := re.search(r"\[TIMING\] Ask agent: ([\d.]+)s", line):
                ask_timing = float(m.group(1))
            if m := re.search(r"\[TIMING\] Acquire agent: ([\d.]+)s", line):
                acquire_timing = float(m.group(1))
            if m := re.search(r"\[TIMING\] Appraise agent: ([\d.]+)s", line):
                appraise_timing = float(m.group(1))
            if m := re.search(r"\[TIMING\] Apply agent: ([\d.]+)s", line):
                apply_timing = float(m.group(1))
            if m := re.search(r"\[TIMING\] Total workflow time: ([\d.]+)s", line):
                total_timing = float(m.group(1))

            if "out_of_domain" in line or "专注于高血压" in line:
                out_of_domain = True
            if "Insufficient Evidence" in line or "insufficient_evidence" in line or "证据不足" in line:
                insufficient_evidence = True

            # Capture scheduling decisions for analysis
            if "DECISION" in line or "backtrack" in line or "proceed" in line or "database_content_gap" in line:
                scheduling_decisions.append(line.strip())

            if "Traceback" in line or "Error:" in line:
                error = line

        proc.wait(timeout=900)
    except subprocess.TimeoutExpired:
        proc.kill()
        error = "TIMEOUT (>900s)"
    except Exception as e:
        error = str(e)

    wall_time = time.time() - t_start

    result = {
        "idx": idx + 1,
        "question": question,
        "expected_behavior": expected,
        "out_of_domain": out_of_domain,
        "insufficient_evidence": insufficient_evidence,
        "first_char_time_s": round(first_char_time, 1) if first_char_time else None,
        "ask_timing_s": ask_timing,
        "acquire_timing_s": acquire_timing,
        "appraise_timing_s": appraise_timing,
        "apply_timing_s": apply_timing,
        "total_timing_s": total_timing,
        "wall_time_s": round(wall_time, 1),
        "scheduling_decisions": scheduling_decisions[:10],
        "error": error,
        "exit_code": proc.returncode,
    }

    status = "✓" if not error else "✗"
    flags = []
    if out_of_domain:
        flags.append("OOD")
    if insufficient_evidence:
        flags.append("InsuffEvid")
    flag_str = f"[{'/'.join(flags)}]" if flags else ""

    print(
        f"  {status} {flag_str} 首字={result['first_char_time_s']}s "
        f"总={result['total_timing_s'] or result['wall_time_s']}s"
        + (f" ERR={error[:60]}" if error else ""),
        flush=True,
    )
    if scheduling_decisions:
        for d in scheduling_decisions[:3]:
            print(f"    sched: {d[:100]}", flush=True)

    with open(FULL_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n[{idx+1:02d}] {question}\nExpected: {expected}\n{'='*80}\n")
        f.write("\n".join(output_lines) + "\n")

    return result


def main():
    print(f"EBM 5A Edge Case Test — {RUN_ID}")
    print(f"Questions: {len(QUESTIONS)} | Log: {SUMMARY_FILE}")
    print("=" * 60)

    results = []
    for i, q in enumerate(QUESTIONS):
        r = run_question(i, q)
        results.append(r)
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    ood = [r for r in results if r["out_of_domain"]]
    insuff = [r for r in results if r["insufficient_evidence"]]
    errors = [r for r in results if r["error"]]
    normal = [r for r in results if not r["out_of_domain"] and not r["error"]]

    print(f"Total: {len(results)}")
    print(f"  OOD soft-reject:      {len(ood)}")
    print(f"  Insufficient Evidence: {len(insuff)}")
    print(f"  Normal completion:    {len(normal) - len(insuff)}")
    print(f"  Errors:               {len(errors)}")

    ttimes = [r["total_timing_s"] for r in results if r["total_timing_s"]]
    if ttimes:
        print(f"\nTiming — avg: {sum(ttimes)/len(ttimes):.1f}s  max: {max(ttimes):.1f}s")

    print("\nPer-question:")
    for r in results:
        flags = []
        if r["out_of_domain"]:   flags.append("OOD")
        if r["insufficient_evidence"]: flags.append("InsuffEvid")
        if r["error"]:           flags.append(f"ERR:{r['error'][:30]}")
        flag_str = " ".join(flags)
        t = r["total_timing_s"] or r["wall_time_s"]
        print(f"  [{r['idx']:02d}] {t:>6.1f}s  {flag_str:<25}  {r['question'][:60]}")

    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  [{r['idx']:02d}] {r['error'][:100]}")

    print(f"\nFull log: {FULL_LOG}")
    print(f"Summary:  {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
