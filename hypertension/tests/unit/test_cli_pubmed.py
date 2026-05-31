import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from hypertensiondb.cli import app

runner = CliRunner()


_PMC_JATS = """<?xml version="1.0"?>
<article xml:lang="en">
  <front>
    <article-meta>
      <article-id pub-id-type="pmid">39111111</article-id>
      <article-id pub-id-type="pmc">PMC9999999</article-id>
      <article-id pub-id-type="doi">10.1234/x</article-id>
      <title-group><article-title>API ingest test</article-title></title-group>
      <contrib-group><contrib contrib-type="author">
        <name><surname>Smith</surname><given-names>John</given-names></name>
      </contrib></contrib-group>
      <pub-date><year>2026</year></pub-date>
      <abstract><p>Test abstract content here.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec sec-type="methods"><title>Methods</title><p>Trial design here.</p></sec>
    <sec sec-type="results"><title>Results</title><p>SBP fell 8 mmHg.</p></sec>
    <sec sec-type="conclusions"><title>Conclusion</title><p>Effective.</p></sec>
  </body>
</article>"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCE_ROOT", str(tmp_path / "evidence"))
    return tmp_path


@pytest.mark.unit
def test_ingest_pubmed_writes_drafts(env):
    """pubmed search → 1 PMID with PMC OA → JATS → draft written."""
    mock_client = MagicMock()
    mock_client.esearch.return_value = ["39111111"]
    mock_client.efetch_pubmed.return_value = [{
        "pmid": "39111111", "doi": "10.1234/x", "pmc_id": "PMC9999999",
        "title": "API ingest test",
        "abstract": "Test abstract content here.",
        "authors": ["Smith J"], "year": 2026, "journal": "J Hyp",
    }]
    mock_client.efetch_pmc_xml.return_value = _PMC_JATS

    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "hypertension", "--limit", "5",
            "--type", "RCT",
        ])

    assert result.exit_code == 0, result.output
    assert "1" in result.output
    written = list((env / "evidence" / "rcts").rglob("EV-RCT-2026-*.md"))
    assert len(written) == 1


@pytest.mark.unit
def test_ingest_pubmed_skips_non_oa(env):
    """A PMID without pmc_id is skipped."""
    mock_client = MagicMock()
    mock_client.esearch.return_value = ["39111111"]
    mock_client.efetch_pubmed.return_value = [{
        "pmid": "39111111", "doi": "10.1234/x", "pmc_id": None,
        "title": "Abstract only", "abstract": "x", "authors": ["A"],
        "year": 2026, "journal": "J",
    }]

    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "x", "--limit", "5", "--type", "RCT",
        ])

    assert result.exit_code == 0, result.output
    assert "skipped" in result.output.lower() or "0 ingested" in result.output.lower()
    written = list((env / "evidence" / "rcts").rglob("EV-RCT-2026-*.md"))
    assert len(written) == 0


@pytest.mark.unit
def test_ingest_pubmed_no_results(env):
    mock_client = MagicMock()
    mock_client.esearch.return_value = []
    with patch("hypertensiondb.cli.NCBIClient", return_value=mock_client):
        result = runner.invoke(app, [
            "ingest", "pubmed", "--query", "nothing", "--type", "RCT",
        ])
    assert result.exit_code == 0
    assert "no results" in result.output.lower() or "0" in result.output
