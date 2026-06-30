"""Render Chinese PubMed audit summaries from screening and download JSONL files."""

from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
from typing import Any


_DOMAIN_LABELS = {
    "hypertension": "高血压",
    "nasal": "鼻病",
}

_DECISION_LABELS = {
    "downloaded": "已下载",
    "already_downloaded": "已下载过",
    "download": "待下载",
    "already_exists": "库内已存在",
    "no_open_fulltext": "无 PMC 免费全文",
    "failed": "失败",
}


def render_daily_report(
    *,
    domain: str,
    date_label: str,
    audit_path: str | Path,
    decisions_path: str | Path,
    output_dir: str | Path,
) -> dict[str, int]:
    audit_rows = _load_jsonl(audit_path)
    decision_rows = _load_jsonl(decisions_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    by_pmid = {
        str(row.get("pmid") or "").strip(): row
        for row in audit_rows
        if str(row.get("pmid") or "").strip()
    }
    merged = [_merge_row(by_pmid.get(str(row.get("pmid") or "").strip(), {}), row) for row in decision_rows]
    seen_pmids = {str(row.get("pmid") or "").strip() for row in decision_rows}
    for row in audit_rows:
        pmid = str(row.get("pmid") or "").strip()
        if pmid and pmid not in seen_pmids:
            merged.append(_merge_row(row, {}))

    counts = Counter(str(row.get("decision") or "not_decided") for row in merged)
    summary = {
        "screened": len(audit_rows),
        "total_decisions": len(decision_rows),
        "downloaded": counts["downloaded"] + counts["already_downloaded"],
        "already_exists": counts["already_exists"],
        "no_open_fulltext": counts["no_open_fulltext"],
    }

    (output / "summary.md").write_text(
        _render_markdown(domain=domain, date_label=date_label, rows=merged, summary=summary),
        encoding="utf-8",
    )
    (output / "index.html").write_text(
        _render_html(domain=domain, date_label=date_label, rows=merged, summary=summary),
        encoding="utf-8",
    )
    return summary


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{source}:{line_number} must contain a JSON object")
        rows.append(row)
    return rows


def _merge_row(audit: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    merged = dict(audit)
    merged.update({key: value for key, value in decision.items() if value is not None})
    return merged


def _render_markdown(
    *,
    domain: str,
    date_label: str,
    rows: list[dict[str, Any]],
    summary: dict[str, int],
) -> str:
    title = _title(domain, date_label)
    lines = [
        f"# {title}",
        "",
        f"- 检索候选：{summary['screened']}",
        f"- 已下载 PMC XML：{summary['downloaded']}",
        f"- 库内已存在：{summary['already_exists']}",
        f"- 无 PMC 免费全文：{summary['no_open_fulltext']}",
        "",
        "| PMID | 题名 | 主题 | 研究类型 | 决策 | 原因 | PubMed |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        pmid = _cell(row.get("pmid"))
        title_text = _cell(row.get("title"))
        topic = _cell(row.get("topic_name"))
        evidence_type = _cell(row.get("evidence_type"))
        decision = _decision_label(row.get("decision"))
        reason = _cell(row.get("reason") or _first_reason(row))
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid != "-" else "-"
        lines.append(f"| {pmid} | {title_text} | {topic} | {evidence_type} | {decision} | {reason} | {link} |")
    lines.append("")
    return "\n".join(lines)


def _render_html(
    *,
    domain: str,
    date_label: str,
    rows: list[dict[str, Any]],
    summary: dict[str, int],
) -> str:
    title = _title(domain, date_label)
    table_rows = "\n".join(_html_row(row) for row in rows)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ font-size: 24px; margin: 0 0 16px; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 12px; min-width: 130px; }}
    .metric strong {{ display: block; font-size: 22px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; }}
    a {{ color: #075985; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class="summary">
    <div class="metric"><span>检索候选</span><strong>{summary['screened']}</strong></div>
    <div class="metric"><span>已下载</span><strong>{summary['downloaded']}</strong></div>
    <div class="metric"><span>库内已存在</span><strong>{summary['already_exists']}</strong></div>
    <div class="metric"><span>无 PMC 免费全文</span><strong>{summary['no_open_fulltext']}</strong></div>
  </div>
  <table>
    <thead>
      <tr><th>PMID</th><th>题名</th><th>主题</th><th>研究类型</th><th>决策</th><th>原因</th><th>PubMed</th></tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>
</body>
</html>
"""


def _html_row(row: dict[str, Any]) -> str:
    pmid = _cell(row.get("pmid"))
    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid != "-" else ""
    link_html = f'<a href="{escape(link)}">打开</a>' if link else "-"
    cells = [
        pmid,
        _cell(row.get("title")),
        _cell(row.get("topic_name")),
        _cell(row.get("evidence_type")),
        _decision_label(row.get("decision")),
        _cell(row.get("reason") or _first_reason(row)),
    ]
    rendered = "".join(f"<td>{escape(value)}</td>" for value in cells)
    return f"      <tr>{rendered}<td>{link_html}</td></tr>"


def _title(domain: str, date_label: str) -> str:
    domain_label = _DOMAIN_LABELS.get(domain, domain)
    return f"{domain_label} PubMed 自动审计 - {date_label}"


def _decision_label(value: Any) -> str:
    text = str(value or "not_decided").strip()
    return _DECISION_LABELS.get(text, text)


def _cell(value: Any) -> str:
    text = str(value or "").strip()
    return text.replace("|", "\\|") if text else "-"


def _first_reason(row: dict[str, Any]) -> str:
    reasons = row.get("reasons")
    if isinstance(reasons, list) and reasons:
        return str(reasons[0])
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True, help="hypertension or nasal")
    parser.add_argument("--date", required=True, help="Date label, e.g. 2026-06-30")
    parser.add_argument("--audit", type=Path, required=True, help="Screening audit JSONL.")
    parser.add_argument("--decisions", type=Path, required=True, help="Download decisions JSONL.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Report output directory.")
    args = parser.parse_args(argv)

    summary = render_daily_report(
        domain=args.domain,
        date_label=args.date,
        audit_path=args.audit,
        decisions_path=args.decisions,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
