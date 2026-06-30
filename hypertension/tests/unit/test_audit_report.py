import json
from pathlib import Path

import pytest

from hypertensiondb.ingest.audit_report import render_daily_report


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


@pytest.mark.unit
def test_render_daily_report_writes_chinese_html_and_markdown(tmp_path: Path):
    audit_path = tmp_path / "audits" / "pubmed-screen-nasal.jsonl"
    decisions_path = tmp_path / "audits" / "pubmed-download-decisions-nasal.jsonl"
    output_dir = tmp_path / "reports"

    _write_jsonl(
        audit_path,
        [
            {
                "pmid": "1001",
                "doi": "10.1000/a",
                "pmc_id": "PMC1001",
                "title": "Guideline for allergic rhinitis management",
                "journal": "Rhinology",
                "year": 2026,
                "topic_name": "allergic_rhinitis",
                "evidence_type": "guideline",
                "evidence_tier": "active_core",
                "access_status": "oa_fulltext",
                "score": 95,
                "reasons": ["disease/topic-specific terms detected"],
            },
            {
                "pmid": "1002",
                "title": "Paywalled trial",
                "topic_name": "nasal_polyps",
                "evidence_type": "rct",
                "evidence_tier": "paywalled_important",
                "access_status": "abstract_only",
                "score": 62,
                "reasons": [],
            },
        ],
    )
    _write_jsonl(
        decisions_path,
        [
            {
                "pmid": "1001",
                "doi": "10.1000/a",
                "pmc_id": "PMC1001",
                "title": "Guideline for allergic rhinitis management",
                "evidence_tier": "active_core",
                "access_status": "oa_fulltext",
                "decision": "downloaded",
                "reason": "PMC XML downloaded to output_dir",
                "output_path": "staging/pmc_xml/nasal/PMC1001.xml",
            },
            {
                "pmid": "1002",
                "doi": None,
                "pmc_id": None,
                "title": "Paywalled trial",
                "evidence_tier": "paywalled_important",
                "access_status": "abstract_only",
                "decision": "no_open_fulltext",
                "reason": "no PMC open full text was identified",
            },
        ],
    )

    result = render_daily_report(
        domain="nasal",
        date_label="2026-06-30",
        audit_path=audit_path,
        decisions_path=decisions_path,
        output_dir=output_dir,
    )

    assert result["screened"] == 2
    assert result["downloaded"] == 1
    assert result["no_open_fulltext"] == 1
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    markdown = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "鼻病 PubMed 自动审计" in html
    assert "已下载" in html
    assert "https://pubmed.ncbi.nlm.nih.gov/1001/" in html
    assert "Guideline for allergic rhinitis management" in html
    assert "鼻病 PubMed 自动审计" in markdown
    assert "| 1001 |" in markdown
