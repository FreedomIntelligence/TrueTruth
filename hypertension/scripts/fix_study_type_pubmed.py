"""用 PubMed Publication Type 修正 study_type 字段。

优先级：
  1. PMID → PubMed efetch → PublicationType 字段（最权威）
  2. 无 PMID → LLM（用改进提示词，明确要求判断"本篇文章自身"的设计）

PT → study_type 映射（按优先级，文章可能有多个 PT）：
  Meta-Analysis / Network Meta-Analysis  → META_ANALYSIS
  Systematic Review                       → SYSTEMATIC_REVIEW
  Randomized Controlled Trial             → RCT
  Clinical Trial (Phase I/II/III/IV)      → RCT
  Controlled Clinical Trial               → RCT
  Pragmatic Clinical Trial                → RCT
  Practice Guideline / Guideline          → GUIDELINE
  Observational Study                     → COHORT
  Case-Control Studies                    → CASE_CONTROL
  Case Reports                            → CASE_REPORT
  Review (without Systematic/Meta)        → NARRATIVE_REVIEW

完成后运行: hdb index rebuild --confirm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import openai
import yaml

# ── Auto-load .env ────────────────────────────────────────────────────────────
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

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

EVIDENCE_ROOT = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EFETCH_BATCH = 20   # PMIDs per request
EFETCH_SLEEP = 0.35  # NCBI rate limit: 3 req/s without API key

# PT priority order (higher index = higher priority)
_PT_PRIORITY: dict[str, tuple[str, int]] = {
    "meta-analysis":               ("META_ANALYSIS",      100),
    "network meta-analysis":       ("META_ANALYSIS",      100),
    "systematic review":           ("SYSTEMATIC_REVIEW",   90),
    "randomized controlled trial": ("RCT",                 80),
    "clinical trial, phase iv":    ("RCT",                 75),
    "clinical trial, phase iii":   ("RCT",                 75),
    "clinical trial, phase ii":    ("RCT",                 75),
    "clinical trial, phase i":     ("RCT",                 75),
    "controlled clinical trial":   ("RCT",                 73),
    "pragmatic clinical trial":    ("RCT",                 73),
    "clinical trial":              ("RCT",                 70),
    "practice guideline":          ("GUIDELINE",           60),
    "guideline":                   ("GUIDELINE",           60),
    "observational study":         ("COHORT",              50),
    "case-control studies":        ("CASE_CONTROL",        45),
    "case reports":                ("CASE_REPORT",         40),
    "review":                      ("NARRATIVE_REVIEW",    20),
    "journal article":             (None,                   0),  # too generic, skip
}

# ── LLM fallback ─────────────────────────────────────────────────────────────
_LLM_PROMPT = """You are a medical literature classifier. Determine the study design of THIS paper itself.

IMPORTANT: Judge the design of THIS paper, NOT the studies it reviewed or cited.
- If this paper IS a randomized trial → RCT
- If this paper IS a meta-analysis (pooled statistics, forest plot, I²) → META_ANALYSIS
- If this paper IS a systematic review (systematic search, no pooling) → SYSTEMATIC_REVIEW
- If this paper IS a prospective/retrospective cohort → COHORT
- If this paper IS a case-control study → CASE_CONTROL
- If this paper IS a clinical guideline → GUIDELINE
- If this paper IS a narrative/non-systematic review → NARRATIVE_REVIEW
- If this paper IS a case report → CASE_REPORT

Output ONLY a JSON object: {{"study_type": "<value>"}}
No markdown. First char must be {{.

Paper title and abstract:
{text}"""


def _parse(md_text: str) -> tuple[dict, str]:
    if not md_text.startswith("---"):
        return {}, md_text
    end = md_text.find("\n---", 3)
    if end == -1:
        return {}, md_text
    try:
        fm = yaml.safe_load(md_text[3:end]) or {}
    except Exception:
        fm = {}
    return fm, md_text[end + 4:]


def _write(path: Path, fm: dict, body: str) -> None:
    fm_str = yaml.dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(f"---\n{fm_str}---\n{body}", encoding="utf-8")


# ── PubMed fetch ──────────────────────────────────────────────────────────────
def fetch_pubmed_pts(pmids: list[str]) -> dict[str, str]:
    """Return {pmid: study_type} for the given PMIDs via PubMed efetch."""
    result: dict[str, str] = {}
    for i in range(0, len(pmids), EFETCH_BATCH):
        batch = pmids[i: i + EFETCH_BATCH]
        try:
            resp = httpx.get(
                EFETCH_URL,
                params={"db": "pubmed", "id": ",".join(batch), "rettype": "xml", "retmode": "xml"},
                timeout=30,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            for article in root.findall(".//PubmedArticle"):
                pmid_el = article.find(".//PMID")
                if pmid_el is None:
                    continue
                pmid = pmid_el.text or ""
                pts = [
                    pt.text.lower()
                    for pt in article.findall(".//PublicationType")
                    if pt.text
                ]
                # Pick highest-priority study_type
                best_type: str | None = None
                best_prio = -1
                for pt in pts:
                    entry = _PT_PRIORITY.get(pt)
                    if entry and entry[0] and entry[1] > best_prio:
                        best_type, best_prio = entry[0], entry[1]
                if best_type:
                    result[pmid] = best_type
        except Exception as e:
            print(f"  [WARN] PubMed fetch failed for batch {i//EFETCH_BATCH+1}: {e}")
        time.sleep(EFETCH_SLEEP)
    return result


# ── LLM fallback ──────────────────────────────────────────────────────────────
def llm_study_type(fm: dict, body: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.huatuogpt.cn/v1")
    model = os.getenv("OPENAI_EXTRACT_MODEL", "HuatuoGPT-3-32B-no-thinking")
    if not api_key:
        return None

    title_en = (fm.get("title") or {}).get("en") or ""
    title_zh = (fm.get("title") or {}).get("zh") or ""
    title = title_en or title_zh or ""
    abstract = body[:2000]
    text = f"Title: {title}\n\n{abstract}"

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=60)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _LLM_PROMPT.format(text=text)}],
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
                        data = json.loads(content[start: i + 1])
                        return data.get("study_type")
    except Exception as e:
        print(f"    [WARN] LLM failed: {e}")
    return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM fallback for no-PMID files")
    parser.add_argument("--only-meta", action="store_true", help="Only fix META/SR/GL files (no RCT/TCM)")
    args = parser.parse_args()

    files = sorted(EVIDENCE_ROOT.glob("EV-*.md"))

    # Collect files needing fix + their PMIDs
    to_fix: list[tuple[Path, dict, str]] = []   # (path, fm, body)
    for f in files:
        text = f.read_text(encoding="utf-8")
        fm, body = _parse(text)
        ev_type = fm.get("type", "")
        if args.only_meta and ev_type not in ("META", "SR", "GL"):
            continue
        to_fix.append((f, fm, body))

    print(f"Files to check: {len(to_fix)}  dry_run={args.dry_run}")

    # Step 1: PubMed lookup for all PMIDs
    pmid_to_path: dict[str, Path] = {}
    for path, fm, body in to_fix:
        pmid = str(fm.get("pmid") or "").strip()
        if pmid:
            pmid_to_path[pmid] = path

    print(f"\nStep 1: PubMed lookup for {len(pmid_to_path)} PMIDs...")
    pmid_results = fetch_pubmed_pts(list(pmid_to_path.keys()))
    print(f"  Got results for {len(pmid_results)}/{len(pmid_to_path)} PMIDs")

    # Step 2: Apply results
    updated_pubmed = updated_llm = skipped = failed_llm = 0
    no_pmid_files: list[tuple[Path, dict, str]] = []

    for path, fm, body in to_fix:
        pmid = str(fm.get("pmid") or "").strip()
        current = fm.get("study_type")

        if pmid and pmid in pmid_results:
            new_type = pmid_results[pmid]
            if new_type == current:
                skipped += 1
                continue
            source = f"PubMed PT (PMID={pmid})"
            print(f"  {path.name}: {current!r} → {new_type!r}  [{source}]")
            if not args.dry_run:
                fm["study_type"] = new_type
                _write(path, fm, body)
            updated_pubmed += 1
        elif not pmid:
            no_pmid_files.append((path, fm, body))
        else:
            # PMID present but PubMed returned no result
            skipped += 1

    # Step 3: LLM fallback for no-PMID files
    if no_pmid_files and not args.no_llm:
        print(f"\nStep 2: LLM fallback for {len(no_pmid_files)} files without PMID...")
        for path, fm, body in no_pmid_files:
            current = fm.get("study_type")
            print(f"  {path.name} ({fm.get('type')}) current={current!r}...", end=" ", flush=True)
            new_type = llm_study_type(fm, body)
            if not new_type:
                print("FAILED")
                failed_llm += 1
                continue
            if new_type == current:
                print(f"unchanged ({current})")
                skipped += 1
                continue
            print(f"→ {new_type!r}")
            if not args.dry_run:
                fm["study_type"] = new_type
                _write(path, fm, body)
            updated_llm += 1
            time.sleep(1.0)
    elif no_pmid_files:
        print(f"\nSkipped LLM fallback (--no-llm). {len(no_pmid_files)} files without PMID unchanged.")
        skipped += len(no_pmid_files)

    print(f"""
Results:
  Updated via PubMed PT : {updated_pubmed}
  Updated via LLM       : {updated_llm}
  Skipped (already correct or no result): {skipped}
  LLM failed            : {failed_llm}
""")
    if not args.dry_run and (updated_pubmed + updated_llm) > 0:
        print("Run: hdb index rebuild --confirm")


if __name__ == "__main__":
    main()
