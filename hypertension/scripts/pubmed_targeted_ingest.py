"""针对性 PubMed 批量入库脚本：补充三类关键证据。

目标类别：
  1. TCM  — 中医/针灸高质量 RCT（改善 Q22/23/24 consistency）
  2. NEW  — 新型药物 RCT（SGLT2i、finerenone、renal denervation）
  3. CN   — 中国人群特异性研究（CSPPT 系列、STEP 系列等）

每类有独立的 PubMed 查询。仅处理有 PMC OA 全文的文章（通过 JATS 入库）。
已在 evidence/ 中存在同 PMID 的文章会被跳过（去重）。

Usage（在 hypertension/ 目录下运行）：
    py scripts/pubmed_targeted_ingest.py [--category tcm|new|cn|all] [--limit 20] [--dry-run]

所有配置从 hypertension/.env 读取，无需手动设置环境变量。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)


def _load_dotenv(env_path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ (skip comments/blanks).
    Already-set variables are NOT overwritten, so shell env takes precedence.
    """
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


# 自动加载 .env（脚本在 scripts/ 下，.env 在父目录）
_load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# PubMed 查询定义
# ---------------------------------------------------------------------------

QUERIES: dict[str, dict] = {
    "tcm": {
        "label": "中医/针灸 RCT",
        "ev_type": "TCM",
        "queries": [
            # 天麻钩藤饮 RCT
            '("Tianma Gouteng" OR "天麻钩藤") AND hypertension AND randomized',
            # 针灸降压 Cochrane / 高质量 RCT
            '("acupuncture" OR "electroacupuncture") AND hypertension AND '
            '("randomized controlled trial"[pt] OR "systematic review"[pt])',
            # 中药复方 + 高血压 RCT，近5年
            '("traditional Chinese medicine" OR "Chinese herbal") AND hypertension '
            'AND "randomized controlled trial"[pt] AND 2020:2026[pdat]',
        ],
    },
    "new": {
        "label": "新型药物 RCT（SGLT2i/finerenone/renal denervation）",
        "ev_type": "RCT",
        "queries": [
            # SGLT2i + 高血压
            '("SGLT2 inhibitor" OR "empagliflozin" OR "dapagliflozin" OR "canagliflozin") '
            'AND hypertension AND "randomized controlled trial"[pt] AND 2020:2026[pdat]',
            # finerenone + 高血压/CKD
            '"finerenone" AND ("hypertension" OR "blood pressure") '
            'AND "randomized controlled trial"[pt]',
            # renal denervation 最新 RCT（SPYRAL/RADIANCE/SYMPLICITY）
            '("renal denervation" OR "renal sympathetic denervation") '
            'AND ("randomized" OR "sham-controlled") AND 2020:2026[pdat]',
        ],
    },
    "cn": {
        "label": "中国人群特异性研究",
        "ev_type": "RCT",
        "queries": [
            # CSPPT 系列
            '"CSPPT" AND hypertension',
            # STEP 系列（已有主文但可能缺亚组/随访）
            '"STEP trial" AND hypertension AND Chinese',
            # 中国高血压大型 RCT，近5年
            'hypertension AND "randomized controlled trial"[pt] AND Chinese '
            'AND ("China" OR "Chinese population") AND 2020:2026[pdat] AND '
            '("blood pressure" OR "antihypertensive")',
        ],
    },
}

INTER_REQUEST_SLEEP = 1.2  # seconds between API calls


# ---------------------------------------------------------------------------
# 已有 PMID 去重
# ---------------------------------------------------------------------------

def _collect_existing_pmids(evidence_root: Path) -> set[str]:
    """Scan all evidence/*.md frontmatter for pmid fields."""
    import re
    pmids: set[str] = set()
    for f in evidence_root.glob("EV-*.md"):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^pmid:\s*['\"]?(\d+)['\"]?", text, re.MULTILINE)
        if m:
            pmids.add(m.group(1))
    return pmids


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------

def run_category(
    cat_key: str,
    cat: dict,
    evidence_root: Path,
    existing_pmids: set[str],
    limit: int,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Run all queries for one category. Returns (ingested, skipped, failed)."""
    from hypertensiondb.ingest.ncbi_client import NCBIClient
    from hypertensiondb.ingest.jats_converter import jats_to_evidence
    from hypertensiondb.ingest.writer import write_evidence_md
    from hypertensiondb.ingest.frontmatter_extractor_llm import LLMFrontmatterExtractor
    from hypertensiondb.utils import id_gen
    from hypertensiondb.utils.pinyin import to_first_author_pinyin

    api_key = os.environ["OPENAI_API_KEY"]
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.huatuogpt.cn/v1")
    model = os.getenv("OPENAI_EXTRACT_MODEL", "HuatuoGPT-3-32B-no-thinking")

    client = NCBIClient()
    llm = LLMFrontmatterExtractor(api_key=api_key, base_url=base_url, model=model)
    id_gen.EVIDENCE_ROOT = evidence_root

    ev_type = cat["ev_type"]
    ingested = skipped = failed = 0
    seen_this_run: set[str] = set()  # dedup within this run across queries

    for query in cat["queries"]:
        print(f"\n  [QUERY] {query[:80]}{'...' if len(query)>80 else ''}")
        try:
            pmids = client.esearch(query=query, db="pubmed", retmax=limit)
        except Exception as e:
            print(f"    esearch failed: {e}")
            continue

        print(f"    → {len(pmids)} PMIDs found")

        for pmid in pmids:
            if ingested >= limit:
                break
            if pmid in existing_pmids or pmid in seen_this_run:
                print(f"    PMID {pmid}: already exists, skip")
                skipped += 1
                continue

            seen_this_run.add(pmid)

            # Fetch PubMed metadata
            try:
                records = client.efetch_pubmed([pmid])
            except Exception as e:
                print(f"    PMID {pmid}: efetch_pubmed failed: {e}")
                failed += 1
                continue

            if not records:
                failed += 1
                continue

            rec = records[0]
            pmc_id = rec.get("pmc_id")

            if not pmc_id:
                print(f"    PMID {pmid}: no PMC OA → skip")
                skipped += 1
                continue

            # Fetch JATS full text
            try:
                jats = client.efetch_pmc_xml(pmc_id)
            except Exception as e:
                print(f"    PMID {pmid}: efetch_pmc_xml failed: {e}")
                failed += 1
                continue

            # Convert JATS → frontmatter + sections
            try:
                fm, sections = jats_to_evidence(jats, evidence_type=ev_type)
            except Exception as e:
                print(f"    PMID {pmid}: jats_to_evidence failed: {e}")
                failed += 1
                continue

            # Patch metadata from PubMed record
            if rec.get("doi"):
                fm["doi"] = rec["doi"]
            fm["pmid"] = pmid
            if rec.get("journal"):
                fm["journal"] = rec["journal"]

            # LLM enrichment for grade/rob/pico
            try:
                body_text = " ".join(sections.values())[:8000]
                llm_fm = llm.extract(text=body_text, evidence_type=ev_type)
                # Only take grade/rob/pico from LLM; keep jats-derived title/authors/year
                for field in ("pico", "risk_of_bias", "grade", "tags"):
                    if llm_fm.get(field):
                        fm[field] = llm_fm[field]
            except Exception as e:
                print(f"    PMID {pmid}: LLM enrichment failed (non-fatal): {e}")

            # Assign ID
            first_author = fm.get("authors", ["Unknown"])[0]
            pinyin = to_first_author_pinyin(first_author)
            fm["id"] = id_gen.next_id(ev_type, fm.get("year", 2026), pinyin)
            fm["status"] = "reviewed"  # auto-promote like hdb ingest pdf
            fm["extracted_by"] = "api+llm"

            title_en = (fm.get("title") or {}).get("en", "N/A")
            print(f"    PMID {pmid}: {title_en[:60]} → {fm['id']}", end="")

            if dry_run:
                print(" [DRY-RUN]")
                ingested += 1
                continue

            try:
                write_evidence_md(frontmatter=fm, sections=sections,
                                  evidence_root=evidence_root)
                existing_pmids.add(pmid)
                ingested += 1
                print(" ✓")
            except FileExistsError:
                print(" [already exists]")
                skipped += 1
            except Exception as e:
                print(f" FAILED: {e}")
                failed += 1

            time.sleep(INTER_REQUEST_SLEEP)

    return ingested, skipped, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="针对性 PubMed 批量入库")
    parser.add_argument(
        "--category", "-c",
        choices=["tcm", "new", "cn", "all"],
        default="all",
        help="要处理的类别（默认 all）",
    )
    parser.add_argument("--limit", type=int, default=15,
                        help="每个 query 最多入库几篇（默认 15）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印，不写文件")
    args = parser.parse_args()

    evidence_root = Path(os.getenv("EVIDENCE_ROOT", "evidence"))
    cats = QUERIES if args.category == "all" else {args.category: QUERIES[args.category]}

    print(f"Evidence root: {evidence_root.resolve()}")
    print(f"Dry-run: {args.dry_run}")
    print("Scanning existing PMIDs...")
    existing_pmids = _collect_existing_pmids(evidence_root)
    print(f"  {len(existing_pmids)} existing PMIDs found\n")

    total_ingested = total_skipped = total_failed = 0

    for cat_key, cat in cats.items():
        print(f"{'='*60}")
        print(f"Category: {cat['label']} ({cat_key})")
        print(f"{'='*60}")
        i, s, f = run_category(
            cat_key, cat, evidence_root, existing_pmids,
            limit=args.limit, dry_run=args.dry_run,
        )
        print(f"\n  [{cat_key}] ingested={i} skipped={s} failed={f}")
        total_ingested += i
        total_skipped += s
        total_failed += f

    print(f"\n{'='*60}")
    print(f"TOTAL: ingested={total_ingested} skipped={total_skipped} failed={total_failed}")
    if not args.dry_run and total_ingested > 0:
        print("\n下一步: cd hypertension && hdb index update")


if __name__ == "__main__":
    main()
