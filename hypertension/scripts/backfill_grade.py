"""批量为 evidence/ 下已有文献补充 grade_level / rob_overall / study_type 字段。

只处理 grade_level 为空的文献（已有值的跳过）。
读取文献的 sections（Methods + Results + Conclusion），调 LLM 抽取，写回 frontmatter。
完成后需手动跑 hdb index update 重新索引。

Usage:
    cd hypertension
    OPENAI_API_KEY=xxx OPENAI_BASE_URL=https://api.huatuogpt.cn/v1 \\
    OPENAI_EXTRACT_MODEL=HuatuoGPT-3-32B-no-thinking \\
    EVIDENCE_ROOT=evidence \\
    py scripts/backfill_grade.py [--type RCT] [--limit 50] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows to handle non-ASCII author names in filenames
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

import openai
import yaml


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


_load_dotenv(Path(__file__).parent.parent / ".env")

EVIDENCE_ROOT = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
API_KEY = os.environ["OPENAI_API_KEY"]
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.huatuogpt.cn/v1")
MODEL = os.getenv("OPENAI_EXTRACT_MODEL", "HuatuoGPT-3-32B-no-thinking")
INTER_REQUEST_SLEEP = 1.0  # seconds between API calls

_CLIENT = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60)

_PROMPT = """You are a medical evidence quality assessor. Given this paper's text, output ONLY a JSON object with:
- study_type: one of RCT | SYSTEMATIC_REVIEW | META_ANALYSIS | COHORT | CASE_CONTROL | GUIDELINE | NARRATIVE_REVIEW | CASE_REPORT
- rob_overall: one of low | some_concerns | high  (risk of bias per RoB2/AMSTAR2)
- grade_level: one of high | moderate | low | very_low  (GRADE evidence quality)

Rules: Return ONLY valid JSON. First char must be {{. No markdown. Omit fields you cannot assess.

Paper:
{text}"""


def _extract_frontmatter_and_body(md_text: str) -> tuple[dict, str]:
    """Split markdown into frontmatter dict and body text."""
    if not md_text.startswith("---"):
        return {}, md_text
    end = md_text.find("\n---", 3)
    if end == -1:
        return {}, md_text
    fm_str = md_text[3:end]
    body = md_text[end + 4:]
    try:
        fm = yaml.safe_load(fm_str) or {}
    except Exception:
        fm = {}
    return fm, body


def _write_frontmatter(path: Path, fm: dict, body: str) -> None:
    """Rewrite file with updated frontmatter."""
    fm_str = yaml.dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(f"---\n{fm_str}---\n{body}", encoding="utf-8")


def _extract_relevant_sections(body: str, max_chars: int = 6000) -> str:
    """Extract Methods + Results + Conclusion sections from body."""
    # Try to find key sections
    patterns = [
        r"(?:##\s*(?:Methods?|方法)[^\n]*\n)([\s\S]+?)(?=\n##|\Z)",
        r"(?:##\s*(?:Results?|结果)[^\n]*\n)([\s\S]+?)(?=\n##|\Z)",
        r"(?:##\s*(?:Conclusion|结论|Discuss)[^\n]*\n)([\s\S]+?)(?=\n##|\Z)",
    ]
    parts = []
    for pat in patterns:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            parts.append(m.group(1)[:2000])
    if parts:
        return "\n\n".join(parts)[:max_chars]
    # Fallback: first max_chars of body
    return body[:max_chars]


def _call_llm(text: str) -> dict:
    prompt = _PROMPT.format(text=text[:6000])
    try:
        resp = _CLIENT.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = resp.choices[0].message.content or ""
        if "{" in content:
            start = content.index("{")
            depth = 0
            for i, ch in enumerate(content[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return json.loads(content[start:i + 1])
    except Exception as e:
        print(f"    [WARN] LLM failed: {e}")
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", help="Only process this type (RCT/META/SR/GL/TCM)")
    parser.add_argument("--limit", type=int, default=9999)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-study-type", action="store_true",
                        help="Re-derive study_type from full text even if already set")
    args = parser.parse_args()

    files = sorted(EVIDENCE_ROOT.glob("EV-*.md"))
    if args.type:
        files = [f for f in files if f"EV-{args.type}-" in f.name]

    # Process files missing grade_level OR study_type (or all if --force-study-type)
    to_process = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        fm, _ = _extract_frontmatter_and_body(text)
        grade = fm.get("grade", {})
        has_grade = isinstance(grade, dict) and grade.get("level")
        has_study_type = bool(fm.get("study_type"))
        if args.force_study_type:
            to_process.append(f)  # process all regardless
        elif has_grade and has_study_type:
            continue  # already complete
        else:
            to_process.append(f)

    to_process = to_process[:args.limit]
    print(f"Files to process: {len(to_process)} (dry_run={args.dry_run})")

    updated = skipped = failed = 0
    for i, path in enumerate(to_process, 1):
        text = path.read_text(encoding="utf-8")
        fm, body = _extract_frontmatter_and_body(text)
        ev_type = fm.get("type", "RCT")
        relevant = _extract_relevant_sections(body)

        print(f"[{i:03d}/{len(to_process)}] {path.name} ({ev_type}) ...", end=" ", flush=True)

        result = _call_llm(relevant)
        if not result:
            print("FAILED")
            failed += 1
            continue

        study_type = result.get("study_type")
        rob = result.get("rob_overall")
        grade_level = result.get("grade_level")

        if not grade_level and not study_type:
            print("nothing extracted, skipping")
            skipped += 1
            continue

        print(f"grade={grade_level} rob={rob} type={study_type}")

        if not args.dry_run:
            if study_type and (not fm.get("study_type") or args.force_study_type):
                fm["study_type"] = study_type
            if rob:
                if not isinstance(fm.get("risk_of_bias"), dict):
                    fm["risk_of_bias"] = {}
                fm["risk_of_bias"]["overall"] = rob
                # tool is required by schema
                fm["risk_of_bias"].setdefault("tool", "RoB2")
            if grade_level:
                if not isinstance(fm.get("grade"), dict):
                    fm["grade"] = {}
                fm["grade"]["level"] = grade_level
            _write_frontmatter(path, fm, body)
            updated += 1

        time.sleep(INTER_REQUEST_SLEEP)

    print(f"\nDone. updated={updated} skipped={skipped} failed={failed}")
    if not args.dry_run and updated > 0:
        print("\nRun: hdb index rebuild --confirm   (or hdb index update if incremental is enough)")


if __name__ == "__main__":
    main()
