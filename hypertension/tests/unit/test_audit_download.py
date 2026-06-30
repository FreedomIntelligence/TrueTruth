import json
from pathlib import Path

import pytest

from hypertensiondb.ingest.audit_download import (
    AuditDownloadDecision,
    collect_existing_citations,
    decide_download,
    download_from_audit,
    load_audit_jsonl,
    write_decisions_jsonl,
)


def _candidate(**overrides):
    data = {
        "pmid": "1001",
        "doi": "10.1000/download",
        "pmc_id": "PMC1001",
        "title": "Guideline for hypertension management",
        "access_status": "oa_fulltext",
        "evidence_tier": "active_core",
        "download_eligible": True,
        "allowed_use": ["recommendation_support", "full_text_indexing"],
        "blocked_use": [],
    }
    data.update(overrides)
    return data


@pytest.mark.unit
def test_collect_existing_citations_reads_pmid_and_doi(tmp_path: Path):
    (tmp_path / "EV-RCT-2026-TEST-001.md").write_text(
        "---\npmid: '1001'\ndoi: 10.1000/download\n---\n",
        encoding="utf-8",
    )

    existing = collect_existing_citations(tmp_path)

    assert "pmid:1001" in existing
    assert "doi:10.1000/download" in existing


@pytest.mark.unit
def test_decide_download_accepts_open_fulltext_candidate():
    decision = decide_download(_candidate(), existing_citations=set())

    assert decision.decision == "download"
    assert decision.pmc_id == "PMC1001"


@pytest.mark.unit
def test_decide_download_rejects_existing_evidence():
    decision = decide_download(
        _candidate(),
        existing_citations={"pmid:1001"},
    )

    assert decision.decision == "already_exists"
    assert "already exists" in decision.reason


@pytest.mark.unit
def test_decide_download_rejects_paywalled_candidate():
    decision = decide_download(
        _candidate(access_status="abstract_only", pmc_id=None, evidence_tier="paywalled_important"),
        existing_citations=set(),
    )

    assert decision.decision == "no_open_fulltext"


@pytest.mark.unit
def test_decide_download_ignores_relevance_tier_when_pmc_fulltext_exists():
    decision = decide_download(
        _candidate(evidence_tier="rejected", allowed_use=[]),
        existing_citations=set(),
    )

    assert decision.decision == "download"


@pytest.mark.unit
def test_decide_download_ignores_staging_tier_when_pmc_fulltext_exists():
    decision = decide_download(
        _candidate(evidence_tier="staging"),
        existing_citations=set(),
    )

    assert decision.decision == "download"


@pytest.mark.unit
def test_decide_download_ignores_audit_download_eligible_flag_when_pmc_fulltext_exists():
    decision = decide_download(
        _candidate(download_eligible=False, download_blockers=["animal_or_mechanistic_only"]),
        existing_citations=set(),
    )

    assert decision.decision == "download"


@pytest.mark.unit
def test_download_from_audit_marks_paywalled_important_as_no_open_fulltext(tmp_path: Path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        json.dumps(
            _candidate(
                pmid="1007",
                doi="10.1000/paywalled",
                pmc_id=None,
                access_status="abstract_only",
                evidence_tier="paywalled_important",
                download_eligible=False,
                title="Important randomized trial of antihypertensive therapy",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    summary = download_from_audit(
        audit_path=audit,
        evidence_root=tmp_path / "evidence",
        output_dir=tmp_path / "staging",
        decisions_path=tmp_path / "decisions.jsonl",
        citation_shells_path=tmp_path / "citation-shells.jsonl",
        client=None,
    )

    assert summary["no_open_fulltext"] == 1
    assert (tmp_path / "citation-shells.jsonl").read_text(encoding="utf-8") == ""


@pytest.mark.unit
def test_load_and_write_decisions_jsonl(tmp_path: Path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(json.dumps(_candidate()) + "\n", encoding="utf-8")
    rows = load_audit_jsonl(audit)
    decision = decide_download(rows[0], existing_citations=set())
    output = tmp_path / "decisions.jsonl"

    write_decisions_jsonl([decision], output)

    written = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert written[0]["pmid"] == "1001"
    assert written[0]["decision"] == "download"


@pytest.mark.unit
def test_download_from_audit_fetches_only_download_decisions(tmp_path: Path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        "\n".join(
            [
                json.dumps(_candidate(pmid="1001", pmc_id="PMC1001")),
                json.dumps(_candidate(pmid="1002", pmc_id=None, access_status="abstract_only")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeClient:
        def efetch_pmc_xml(self, pmc_id):
            assert pmc_id == "PMC1001"
            return "<article><body>ok</body></article>"

    summary = download_from_audit(
        audit_path=audit,
        evidence_root=tmp_path / "evidence",
        output_dir=tmp_path / "staging",
        decisions_path=tmp_path / "decisions.jsonl",
        client=FakeClient(),
    )

    assert summary["downloaded"] == 1
    assert summary["no_open_fulltext"] == 1
    assert (tmp_path / "staging" / "PMC1001.xml").exists()
    assert isinstance(summary["decisions"][0], AuditDownloadDecision)
