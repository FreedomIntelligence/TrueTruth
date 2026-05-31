"""批量运行 30 个问题，记录首字时间、总耗时、错误，生成结构化报告。"""
import subprocess
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime

# Force UTF-8 output on Windows to handle Chinese and special characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

QUESTIONS = [
    # ── 一线药物 (8题) ──────────────────────────────────────────────────────
    "高血压患者首选 ARB 还是 ACEI？",
    "ARB 联合 CCB 治疗中重度原发性高血压的疗效如何？",
    "氨氯地平与硝苯地平在高血压治疗中的比较",
    "噻嗪类利尿剂用于高血压一线治疗的证据",
    "β 受体阻滞剂在高血压治疗中的地位",
    "单药治疗高血压血压不达标时如何加药？",
    "高血压患者何时需要三联降压方案？",
    "缬沙坦与氯沙坦在高血压患者中的降压疗效比较",

    # ── 特殊人群 (8题) ──────────────────────────────────────────────────────
    "老年高血压患者的降压目标值应设多少？",
    "高血压合并 CKD 患者首选哪类降压药？",
    "高血压合并糖尿病患者的降压方案",
    "妊娠期高血压的安全降压药物选择",
    "高血压合并冠心病患者的降压治疗",
    "高血压合并心力衰竭的降压策略",
    "儿童高血压的诊断标准与治疗原则",
    "难治性高血压的定义和处理方法",

    # ── 新型药物/干预 (5题) ─────────────────────────────────────────────────
    "SGLT2 抑制剂对高血压的降压效果",
    "肾脏去神经术（Renal Denervation）治疗高血压的证据",
    "醛固酮合酶抑制剂在高血压中的应用",
    "高血压患者生活方式干预（运动、饮食）的降压效果",
    "家庭血压监测与诊室血压在高血压管理中的作用",

    # ── 中医药 (3题) ────────────────────────────────────────────────────────
    "中药天麻钩藤饮治疗高血压的临床证据",
    "针灸降血压的效果如何？",
    "中西医结合治疗高血压与单纯西医治疗的比较",

    # ── 领域外（应软拒绝，6题）─────────────────────────────────────────────
    "二甲双胍治疗 2 型糖尿病的效果",
    "阿司匹林用于冠心病二级预防",
    "乳腺癌的筛查推荐年龄",
    "儿童哮喘的阶梯治疗方案",
    "他汀类药物治疗高胆固醇血症",
    "幽门螺旋杆菌的根除方案",
]

LOG_DIR = Path("logs/batch_test")
LOG_DIR.mkdir(parents=True, exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
SUMMARY_FILE = LOG_DIR / f"summary_{RUN_ID}.json"
FULL_LOG = LOG_DIR / f"full_{RUN_ID}.log"


def run_question(idx: int, question: str) -> dict:
    """Run one question and return structured result."""
    print(f"\n[{idx+1:02d}/30] {question}", flush=True)
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
    total_timing = None
    ask_timing = None
    acquire_timing = None

    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            output_lines.append(line)

            # 首字时间：第一个非空输出（排除 "Processing..." 启动行）
            if first_char_time is None and line.strip() and not line.startswith("Processing") and not line.startswith("Question"):
                first_char_time = time.time() - t_start

            # 解析关键 TIMING
            if m := re.search(r"\[TIMING\] Ask agent: ([\d.]+)s", line):
                ask_timing = float(m.group(1))
            if m := re.search(r"\[TIMING\] Acquire agent: ([\d.]+)s", line):
                acquire_timing = float(m.group(1))
            if m := re.search(r"\[TIMING\] Total workflow time: ([\d.]+)s", line):
                total_timing = float(m.group(1))

            # 软拒绝检测
            if "out_of_domain" in line or "专注于高血压" in line:
                out_of_domain = True

            # 错误检测
            if "Traceback" in line or "Error:" in line:
                error = line

        proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        error = "TIMEOUT (>600s)"
    except Exception as e:
        error = str(e)

    wall_time = time.time() - t_start

    result = {
        "idx": idx + 1,
        "question": question,
        "out_of_domain": out_of_domain,
        "first_char_time_s": round(first_char_time, 1) if first_char_time else None,
        "ask_timing_s": ask_timing,
        "acquire_timing_s": acquire_timing,
        "total_timing_s": total_timing,
        "wall_time_s": round(wall_time, 1),
        "error": error,
        "exit_code": proc.returncode,
    }

    status = "✓" if not error else "✗"
    domain_tag = "[OOD]" if out_of_domain else ""
    print(
        f"  {status} {domain_tag} 首字={result['first_char_time_s']}s "
        f"总={result['total_timing_s'] or result['wall_time_s']}s"
        + (f" ERR={error[:60]}" if error else ""),
        flush=True,
    )

    # Append to full log
    with open(FULL_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n[{idx+1:02d}/30] {question}\n{'='*80}\n")
        f.write("\n".join(output_lines) + "\n")

    return result


def main():
    print(f"EBM 5A Batch Test — {RUN_ID}")
    print(f"Questions: {len(QUESTIONS)} | Log: {SUMMARY_FILE}")
    print("=" * 60)

    results = []
    for i, q in enumerate(QUESTIONS):
        r = run_question(i, q)
        results.append(r)
        # Save incrementally
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    ood = [r for r in results if r["out_of_domain"]]
    errors = [r for r in results if r["error"]]
    normal = [r for r in results if not r["out_of_domain"] and not r["error"]]

    print(f"Total: {len(results)} | Normal: {len(normal)} | OOD soft-reject: {len(ood)} | Errors: {len(errors)}")

    if normal:
        ftimes = [r["first_char_time_s"] for r in normal if r["first_char_time_s"]]
        ttimes = [r["total_timing_s"] for r in normal if r["total_timing_s"]]
        if ftimes:
            print(f"First-char time — avg: {sum(ftimes)/len(ftimes):.1f}s  min: {min(ftimes):.1f}s  max: {max(ftimes):.1f}s")
        if ttimes:
            print(f"Total time      — avg: {sum(ttimes)/len(ttimes):.1f}s  min: {min(ttimes):.1f}s  max: {max(ttimes):.1f}s")

    if ood:
        ood_ftimes = [r["first_char_time_s"] for r in ood if r["first_char_time_s"]]
        if ood_ftimes:
            print(f"OOD reject time — avg: {sum(ood_ftimes)/len(ood_ftimes):.1f}s")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors:
            print(f"  [{r['idx']:02d}] {r['question'][:50]} — {r['error'][:80]}")

    print(f"\nFull log: {FULL_LOG}")
    print(f"Summary:  {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
