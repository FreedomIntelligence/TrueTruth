#!/usr/bin/env python3
"""Concurrent batch runner for bug hunting.

Loads experiments/bug_hunt_30.json and runs each question through src/main.py
with a configurable number of parallel workers. Each case gets its own log
under logs/bughunt_<ID>_<TS>.log; a TSV summary is updated as cases finish.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = ROOT / "experiments" / "bug_hunt_30.json"
LOG_DIR = ROOT / "logs"


def parse_log(log_path: Path) -> dict:
    result = {
        "question_type": "N/A",
        "strength": "N/A",
        "quality_score": "N/A",
        "duration_s": "N/A",
        "apply_calls": "N/A",
        "evidence_quality": "N/A",
        "n_evidence": "N/A",
        "status": "unknown",
        "first_error": "",
    }
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        result["status"] = "log_not_found"
        return result

    m = re.search(r"question_type=(\w+)", text)
    if m:
        result["question_type"] = m.group(1)

    m = re.search(r"Recommendation Strength\s*:\s*(.+)", text)
    if m:
        result["strength"] = m.group(1).strip()

    m = re.search(r"Evidence Quality\s*:\s*(.+)", text)
    if m:
        result["evidence_quality"] = m.group(1).strip()

    m = re.search(r"Overall Quality Score\s*:\s*([\d.]+)", text)
    if m:
        result["quality_score"] = m.group(1)

    m = re.search(r"Total workflow time:\s*([\d.]+)s", text)
    if m:
        result["duration_s"] = m.group(1)

    m = re.search(r"'Apply':\s*(\d+)", text)
    if m:
        result["apply_calls"] = m.group(1)

    m = re.search(r"EVIDENCE FOUND:\s*(\d+)", text)
    if m:
        result["n_evidence"] = m.group(1)

    # Status classification
    has_traceback = "Traceback" in text
    has_500 = "InternalServerError" in text or "APIStatusError" in text
    has_json_fail = "JSON parse failed" in text or "Failed to parse JSON" in text
    has_no_rec = "No recommendation generated" in text
    has_timeout_marker = "[TIMEOUT]" in text

    if has_traceback:
        # capture first traceback header
        tb = re.search(r"(Traceback[\s\S]{0,400})", text)
        if tb:
            result["first_error"] = tb.group(1).splitlines()[-1][:200]
        result["status"] = "traceback"
    elif has_timeout_marker:
        result["status"] = "timeout"
    elif has_no_rec or result["strength"] == "N/A":
        result["status"] = "incomplete"
    elif has_500:
        result["status"] = "api_error"
    elif has_json_fail:
        # If recovered, still counts as success — but flag it
        if result["strength"] != "N/A" and result["quality_score"] != "N/A":
            result["status"] = "success_with_json_recovery"
        else:
            result["status"] = "json_error"
    elif result["strength"] != "N/A" and result["quality_score"] != "N/A":
        result["status"] = "success"
    else:
        result["status"] = "incomplete"

    return result


def run_one(case: dict, batch_ts: str, timeout_s: int) -> dict:
    """Run a single case in a subprocess. Returns metrics + log path."""
    case_id = case["id"]
    log_file = LOG_DIR / f"bughunt_{case_id}_{batch_ts}.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    env["QUESTION"] = case["question"]

    cmd = ["py", "-3", str(ROOT / "src" / "main.py"), case["question"]]

    start = time.time()
    try:
        with log_file.open("w", encoding="utf-8") as f:
            f.write(f"### CASE {case_id} disease={case['disease']}\n")
            f.write(f"### QUESTION: {case['question']}\n")
            f.write(f"### START {datetime.now().isoformat()}\n")
            f.flush()
            try:
                subprocess.run(
                    cmd,
                    env=env,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    timeout=timeout_s,
                    cwd=str(ROOT),
                )
            except subprocess.TimeoutExpired:
                f.write(f"\n[TIMEOUT] killed after {timeout_s}s\n")
    except Exception as exc:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n[HARNESS-ERROR] {exc!r}\n")

    elapsed = time.time() - start
    metrics = parse_log(log_file)
    if metrics["duration_s"] == "N/A":
        metrics["duration_s"] = f"{elapsed:.1f}"

    return {"case": case, "metrics": metrics, "log_file": str(log_file)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3, help="Parallel workers")
    ap.add_argument("--timeout", type=int, default=900, help="Per-case timeout in seconds")
    ap.add_argument("--cases", type=int, nargs="*", help="Filter to specific 1-based case IDs (Q01 -> 1)")
    ap.add_argument("--questions", type=str, default=str(QUESTIONS_PATH))
    args = ap.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if args.cases:
        wanted = {f"Q{i:02d}" for i in args.cases}
        questions = [q for q in questions if q["id"] in wanted]

    batch_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(exist_ok=True)
    tsv_path = LOG_DIR / f"bughunt_summary_{batch_ts}.tsv"

    header = (
        "id\tdisease\tquestion_type\tstrength\tevidence_quality\tquality_score"
        "\tduration_s\tapply_calls\tn_evidence\tstatus\tfirst_error\tlog_file\n"
    )
    tsv_path.write_text(header, encoding="utf-8")
    write_lock = Lock()

    print(f"=== Bug hunt: {len(questions)} cases × {args.workers} workers ===")
    print(f"Summary TSV: {tsv_path}")

    results = []
    completed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, q, batch_ts, args.timeout): q for q in questions}
        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            completed += 1
            c, m = r["case"], r["metrics"]
            line = (
                f"{c['id']}\t{c['disease']}\t{m['question_type']}\t{m['strength']}"
                f"\t{m['evidence_quality']}\t{m['quality_score']}\t{m['duration_s']}"
                f"\t{m['apply_calls']}\t{m['n_evidence']}\t{m['status']}"
                f"\t{m['first_error'][:120]}\t{r['log_file']}\n"
            )
            with write_lock:
                with tsv_path.open("a", encoding="utf-8") as f:
                    f.write(line)
            elapsed = time.time() - t0
            print(
                f"[{completed:>2}/{len(questions)}] {c['id']:>4} {c['disease'][:30]:<30}"
                f"  type={m['question_type']:<11} strength={m['strength'][:18]:<18}"
                f"  status={m['status']:<28}  ({elapsed:.0f}s elapsed)"
            )

    print(f"\nFinished {len(results)} cases in {time.time() - t0:.1f}s")
    print(f"Summary: {tsv_path}")


if __name__ == "__main__":
    main()
