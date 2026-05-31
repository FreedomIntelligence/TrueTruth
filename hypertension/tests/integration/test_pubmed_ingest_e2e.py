"""End-to-end: mock NCBI HTTP → hdb ingest pubmed → evidence/rcts/*.md → lint."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from hypertensiondb.cli import app
from hypertensiondb.quality.lint import run_lint
from hypertensiondb.quality.stats import compute_stats


_FAKE_JATS = """<?xml version="1.0"?>
<article xml:lang="en">
  <front>
    <article-meta>
      <article-id pub-id-type="pmid">39111111</article-id>
      <article-id pub-id-type="pmc">PMC9999999</article-id>
      <article-id pub-id-type="doi">10.5555/integration</article-id>
      <title-group><article-title>Integration test paper on hypertension</article-title></title-group>
      <contrib-group><contrib contrib-type="author">
        <name><surname>Chen</surname><given-names>Wei</given-names></name>
      </contrib></contrib-group>
      <pub-date><year>2026</year></pub-date>
      <abstract><p>Integration test abstract. Combination therapy vs monotherapy.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec sec-type="methods"><title>Methods</title><p>Double-blind RCT with 612 patients.</p></sec>
    <sec sec-type="results"><title>Results</title><p>SBP fell 8 mmHg in combination arm.</p></sec>
    <sec sec-type="conclusions"><title>Conclusion</title><p>Combination superior.</p></sec>
  </body>
</article>"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_ROOT", str(tmp_path / "evidence"))
    return tmp_path


@pytest.mark.integration
def test_pubmed_to_markdown_to_lint(env):
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.esearch.return_value = ["39111111"]
    mock_client.efetch_pubmed.return_value = [{
        "pmid": "39111111", "doi": "10.5555/integration", "pmc_id": "PMC9999999",
        "title": "Integration test paper on hypertension",
        "abstract": "Integration test abstract.",
        "authors": ["Chen W"], "year": 2026, "journal": "J Hyp",
    }]
    mock_client.efetch_pmc_xml.return_value = _FAKE_JATS

    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "hypertension", "--type", "RCT",
        ])

    assert result.exit_code == 0, result.output
    written = list((env / "evidence" / "rcts").rglob("EV-RCT-2026-*.md"))
    assert len(written) == 1, f"output: {result.output}"

    # Lint the corpus — schema errors here would indicate a JATS → frontmatter bug.
    # JATS-sourced RCT drafts intentionally lack pico/risk_of_bias/grade (human fills
    # those in during review). Only those known-missing fields are acceptable schema
    # errors for a JATS-ingested draft; any other schema error is a real bug.
    report = run_lint(env / "evidence")
    unexpected_schema_errors = [
        i for i in report.issues
        if i.code == "schema_error"
        and not _is_expected_jats_schema_error(i.detail)
    ]
    assert not unexpected_schema_errors, f"unexpected schema errors: {unexpected_schema_errors}"

    # Stats reflect the new draft
    stats = compute_stats(env / "evidence")
    assert stats.total == 1
    assert stats.by_status.get("draft", 0) == 1


def _is_expected_jats_schema_error(detail: str) -> bool:
    """Return True if the schema error is a known JATS-sourced draft limitation.

    JATS XML doesn't carry PICO, risk-of-bias, or GRADE data — those are filled
    in by a human reviewer. Missing pico / risk_of_bias / grade fields are therefore
    expected for any RCT ingested via the PubMed pipeline.
    """
    known_missing = ("pico", "risk_of_bias", "grade")
    return any(field in detail for field in known_missing)


@pytest.mark.integration
def test_publish_cli_flow(env):
    """draft → reviewed → published end-to-end via CLI."""
    runner = CliRunner()

    # Seed a draft file
    content = """---
id: EV-RCT-2026-CHEN-001
type: RCT
title:
  zh: 测试
authors: [Chen W]
year: 2026
language: zh
status: draft
extracted_by: human
pico:
  population: {condition: 高血压}
  intervention: {name: 测试}
  outcomes: {}
risk_of_bias: {tool: RoB2, overall: low}
grade: {level: moderate}
---

## 方法 / Methods

x

## 结果 / Results

y

## 结论 / Conclusion

z

## 中文摘要

a
"""
    f = env / "evidence" / "rcts" / "EV-RCT-2026-CHEN-001.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")

    # draft → reviewed
    r1 = runner.invoke(app, ["publish", "EV-RCT-2026-CHEN-001", "--to", "reviewed"])
    assert r1.exit_code == 0, r1.output
    assert "status: reviewed" in f.read_text(encoding="utf-8")

    # reviewed → published
    r2 = runner.invoke(app, ["publish", "EV-RCT-2026-CHEN-001", "--to", "published"])
    assert r2.exit_code == 0, r2.output
    assert "status: published" in f.read_text(encoding="utf-8")
