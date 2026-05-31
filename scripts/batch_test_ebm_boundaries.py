"""EBM 方法论边界条件测试集。

覆盖当前测试集未涉及的六类路径：
1. GRADE 升级路径（大效应量 + 观察性研究）
2. Publication bias（中文小样本全阳性发表偏倚）
3. Strong recommendation despite Low evidence（证据质量-推荐强度解耦）
4. Prognosis 题型（PICOT，队列研究证据层级）
5. Network meta / 间接比较（无直接头对头 RCT）
6. Harm / 不良反应题型（伤害问题证据层级）

学术依据：
- Richardson et al. 1995 (PMID 7582737)：EBM 五类问题类型
- Guyatt et al. 2011 GRADE series (PMID 21802902-21802904, 21803546)
- Andrews et al. 2013 (PMID 23570745)：证据质量与推荐强度解耦
- Salanti et al. 2011 (PMID 21242073)：网状 Meta 间接比较
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
    # ── 1. GRADE 升级路径 ────────────────────────────────────────────────────
    # 预期：证据主要来自观察性研究，但效应量大（RR≈0.77），
    # 系统应识别大效应量升级因子（Guyatt PMID 21802902），
    # 输出 Moderate 或 Low + 升级说明，而非直接 Very Low。
    "高血压合并收缩功能不全性心力衰竭患者，ACEI 治疗全因死亡率的相对风险约为 0.77（23% 降低），"
    "但部分证据来自观察性研究。请评估 GRADE 证据质量和推荐强度，并说明是否触发大效应量升级条件。",

    # ── 2. Publication bias（发表偏倚）────────────────────────────────────────
    # 预期：触发 publication bias downgrade，证据质量降至 Very Low 或 Low，
    # 推荐为 Conditional 并在 caveats 中说明漏斗图不对称/小样本偏倚风险。
    "天麻钩藤饮治疗原发性高血压：现有 RCT 几乎全为中文小样本（n<100）且全部报告阳性结果。"
    "请评估这批证据的 GRADE 质量，重点分析发表偏倚风险及其对推荐强度的影响。",

    # ── 3. Strong recommendation despite Low evidence（解耦场景）─────────────
    # 预期：证据质量 Low/Very Low（仅小型 RCT，如 INTERACT-2），
    # 但推荐强度应为 Strong（不降压危害极大，利弊权衡明确），
    # 体现 Andrews et al. 2013 证据质量≠推荐强度的 GRADE 原则。
    "高血压性脑出血急性期（发病 6 小时内，SBP>220 mmHg），"
    "是否应立即启动静脉降压治疗，目标 SBP 控制在什么范围？",

    # ── 4. Prognosis 题型（PICOT，队列研究）─────────────────────────────────
    # 预期：Ask 识别为 Prognosis 类型，PICO 加入 T（time horizon），
    # Acquire 检索队列/登记研究，Appraise 起始分 Low（观察性研究）。
    "高血压合并 2 型糖尿病患者，将血压控制至 <130/80 mmHg 后，"
    "与控制在 130–139/80–89 mmHg 相比，5 年内主要心血管不良事件（MACE）的绝对风险降低幅度是多少？",

    # ── 5. Network meta / 间接比较（无直接 RCT）─────────────────────────────
    # 预期：Ask 识别到无直接头对头比较，Acquire 应检索网状 Meta 或间接证据，
    # Appraise 对 indirectness 降级，Apply 注明证据来自间接比较。
    "在无 ARB 与 CCB 直接头对头 RCT 的情况下，"
    "如何从网状 Meta 分析的间接比较证据评估两者在高血压一级预防中脑卒中风险的差异？",

    # ── 6. Harm 题型（不良反应证据层级）────────────────────────────────────
    # 预期：Ask 识别为 Harm 类型，证据层级应接受队列/病例对照研究，
    # 不强求 RCT（因不良事件发生率低，RCT 统计效能不足）。
    "难治性高血压患者同时使用 ACEI 与螺内酯，高钾血症（血钾 >5.5 mmol/L）的发生率是多少，"
    "哪些患者特征会显著增加风险？",
]

EXPECTED = {
    0: "grade_upgrade — 大效应量升级（RR≈0.77），观察性研究默认 Low 但应升至 Moderate",
    1: "publication_bias — 发表偏倚 downgrade，Very Low 证据，Conditional + 强 caveats",
    2: "strong_rec_low_evidence — Strong 推荐 + Low/Very Low 证据（证据质量≠推荐强度）",
    3: "prognosis_pico — Prognosis 题型，PICOT 框架，队列研究，绝对风险降低",
    4: "network_meta — 间接比较，indirectness downgrade，注明网状 Meta 来源",
    5: "harm_question — Harm 题型，队列/病例对照证据优于 RCT，发生率 + 风险因素",
}

LOG_DIR = Path("logs/ebm_boundary_test")
LOG_DIR.mkdir(parents=True, exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
SUMMARY_FILE = LOG_DIR / f"summary_{RUN_ID}.json"
FULL_LOG = LOG_DIR / f"full_{RUN_ID}.log"


def run_question(idx: int, question: str) -> dict:
    expected = EXPECTED.get(idx, "unknown")
    label = expected.split(" — ")[0]
    print(f"\n[{idx+1:02d}/{len(QUESTIONS)}] [{label}]", flush=True)
    print(f"  Q: {question[:80]}...", flush=True)
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
    strength = None
    quality = None
    question_type = None
    grade_signals = []

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

            if m := re.search(r"strength=([\w ]+)", line):
                strength = m.group(1).strip()
            if m := re.search(r"quality=([\w ]+)", line):
                quality = m.group(1).strip()
            if m := re.search(r"type=(Therapy|Diagnosis|Prognosis|Harm|Economic)", line):
                question_type = m.group(1)

            if "out_of_domain" in line or "专注于高血压" in line:
                out_of_domain = True
            if "Insufficient Evidence" in line or "insufficient_evidence" in line:
                insufficient_evidence = True

            # Capture GRADE signals
            for kw in ["upgrade", "publication_bias", "Inconsistency", "imprecision",
                       "indirectness", "large effect", "dose-response", "网状",
                       "indirect", "Prognosis", "Harm", "Strong", "Conditional", "Very Low"]:
                if kw.lower() in line.lower() and line.strip():
                    grade_signals.append(line.strip()[:120])

            if "DECISION" in line or "backtrack" in line or "proceed" in line:
                scheduling_decisions.append(line.strip())

            if "Traceback" in line or ("Error:" in line and "TIMING" not in line):
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
        "label": label,
        "question": question,
        "expected": expected,
        "question_type_detected": question_type,
        "out_of_domain": out_of_domain,
        "insufficient_evidence": insufficient_evidence,
        "strength": strength,
        "quality": quality,
        "first_char_time_s": round(first_char_time, 1) if first_char_time else None,
        "ask_timing_s": ask_timing,
        "acquire_timing_s": acquire_timing,
        "appraise_timing_s": appraise_timing,
        "apply_timing_s": apply_timing,
        "total_timing_s": total_timing,
        "wall_time_s": round(wall_time, 1),
        "grade_signals": list(dict.fromkeys(grade_signals))[:8],
        "scheduling_decisions": scheduling_decisions[:8],
        "error": error,
        "exit_code": proc.returncode,
    }

    status = "✓" if not error else "✗"
    flags = []
    if out_of_domain:   flags.append("OOD")
    if insufficient_evidence: flags.append("InsuffEvid")
    if strength:        flags.append(f"str={strength}")
    if quality:         flags.append(f"q={quality}")
    if question_type:   flags.append(f"type={question_type}")
    flag_str = " ".join(flags)

    t = total_timing or wall_time
    print(f"  {status} {t:.1f}s  {flag_str}" + (f"  ERR={error[:50]}" if error else ""), flush=True)
    for sig in result["grade_signals"][:3]:
        print(f"    grade: {sig[:100]}", flush=True)

    with open(FULL_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n[{idx+1:02d}] [{label}]\n{question}\nExpected: {expected}\n{'='*80}\n")
        f.write("\n".join(output_lines) + "\n")

    return result


def main():
    print(f"EBM Boundary Test — {RUN_ID}")
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

    errors = [r for r in results if r["error"]]
    insuff = [r for r in results if r["insufficient_evidence"]]
    print(f"Total: {len(results)}  Errors: {len(errors)}  InsuffEvid: {len(insuff)}")

    ttimes = [r["total_timing_s"] for r in results if r["total_timing_s"]]
    if ttimes:
        print(f"Timing — avg: {sum(ttimes)/len(ttimes):.1f}s  max: {max(ttimes):.1f}s")

    print("\nPer-question:")
    for r in results:
        t = r["total_timing_s"] or r["wall_time_s"]
        qtype = r.get("question_type_detected") or "?"
        strength = r.get("strength") or "?"
        quality = r.get("quality") or "?"
        insuff_flag = "[InsuffEvid]" if r["insufficient_evidence"] else ""
        err_flag = f"[ERR]" if r["error"] else ""
        print(f"  [{r['idx']:02d}] {t:>6.1f}s  type={qtype:<10} str={strength:<20} q={quality:<12} {insuff_flag}{err_flag}  [{r['label']}]")

    print(f"\nFull log: {FULL_LOG}")
    print(f"Summary:  {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
