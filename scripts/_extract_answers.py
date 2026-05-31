"""Extract CLINICAL ANSWER blocks from batch test full log."""
import re
from pathlib import Path

log = Path("logs/batch_test/full_20260529_104821.log").read_text(encoding="utf-8")

parts = re.split(r"={70,}\n\[(\d{2})/30\] (.+?)\n={70,}", log)

out_lines = []
out_lines.append("# EBM 5A 批量测试 — CLINICAL ANSWER 汇总")
out_lines.append("# 日期: 2026-05-29\n")

i = 1
while i < len(parts):
    idx = parts[i]
    question = parts[i+1]
    body = parts[i+2]
    i += 3

    timing_match = re.search(r"\[TIMING\] Total workflow time: ([\d.]+)s", body)
    timing = timing_match.group(1) if timing_match else "N/A"

    out_lines.append(f"\n{'='*80}")
    out_lines.append(f"[{idx}/30] {question}")
    out_lines.append(f"Total time: {timing}s")
    out_lines.append(f"{'='*80}")

    # Format is: ★+ \n CLINICAL ANSWER \n ★+ \n <content> \n ★+
    # Find all lines, collect from "CLINICAL ANSWER" line to 3rd ★ line
    lines = body.split("\n")
    ca_lines = []
    found_ca = False
    star_after_ca = 0
    for line in lines:
        if "CLINICAL ANSWER" in line and not found_ca:
            found_ca = True
            ca_lines.append("★" * 80)
            ca_lines.append(line)
            continue
        if found_ca:
            ca_lines.append(line)
            if line.strip().startswith("★★★"):
                star_after_ca += 1
                if star_after_ca >= 2:  # first ★ is after CLINICAL ANSWER, second is closing
                    break

    if len(ca_lines) > 3:
        out_lines.extend(ca_lines)
    elif "Traceback" in body:
        out_lines.append("[ERROR — 运行报错]")
    else:
        out_lines.append("[未找到 CLINICAL ANSWER 块]")

output_path = Path("logs/batch_test/clinical_answers_20260529.txt")
output_path.write_text("\n".join(out_lines), encoding="utf-8")
print(f"Written {len(out_lines)} lines to {output_path}")
