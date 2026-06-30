"""Decide and download PMC full text from PubMed screening audit files."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable, Protocol

from hypertensiondb.ingest.ncbi_client import NCBIClient


@dataclass(frozen=True)
class AuditDownloadDecision:
    pmid: str
    doi: str | None
    pmc_id: str | None
    title: str
    evidence_tier: str
    access_status: str
    decision: str
    reason: str
    output_path: str | None = None


class PMCFetchClient(Protocol):
    def efetch_pmc_xml(self, pmc_id: str) -> str:
        ...


def load_audit_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        rows.append(row)
    return rows


def collect_existing_citations(evidence_root: str | Path) -> set[str]:
    root = Path(evidence_root)
    if not root.exists():
        return set()
    citations: set[str] = set()
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        pmid = _frontmatter_scalar(text, "pmid")
        doi = _frontmatter_scalar(text, "doi")
        if pmid:
            citations.add(f"pmid:{pmid.lower()}")
        if doi:
            citations.add(f"doi:{doi.lower()}")
    return citations


def decide_download(
    candidate: dict[str, Any],
    *,
    existing_citations: set[str],
) -> AuditDownloadDecision:
    pmid = str(candidate.get("pmid") or "").strip()
    doi = _optional_string(candidate.get("doi"))
    pmc_id = _optional_string(candidate.get("pmc_id"))
    title = str(candidate.get("title") or "").strip()
    evidence_tier = str(candidate.get("evidence_tier") or "").strip()
    access_status = str(candidate.get("access_status") or "").strip()

    if pmid and f"pmid:{pmid.lower()}" in existing_citations:
        return _decision(candidate, "already_exists", "PMID already exists in evidence_root")
    if doi and f"doi:{doi.lower()}" in existing_citations:
        return _decision(candidate, "already_exists", "DOI already exists in evidence_root")

    if access_status != "oa_fulltext" or not pmc_id:
        return _decision(candidate, "no_open_fulltext", "no PMC open full text was identified")

    return AuditDownloadDecision(
        pmid=pmid,
        doi=doi,
        pmc_id=pmc_id,
        title=title,
        evidence_tier=evidence_tier,
        access_status=access_status,
        decision="download",
        reason="eligible PMC open full text candidate",
    )


def download_from_audit(
    *,
    audit_path: str | Path,
    evidence_root: str | Path,
    output_dir: str | Path,
    decisions_path: str | Path | None = None,
    citation_shells_path: str | Path | None = None,
    client: PMCFetchClient | None = None,
) -> dict[str, Any]:
    rows = load_audit_jsonl(audit_path)
    existing = collect_existing_citations(evidence_root)
    client = client or NCBIClient()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    decisions: list[AuditDownloadDecision] = []
    citation_shells: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for row in rows:
        decision = decide_download(row, existing_citations=existing)
        if decision.decision == "download" and decision.pmc_id:
            target = output / f"{decision.pmc_id}.xml"
            if target.exists():
                decision = _replace_decision(
                    decision,
                    decision="already_downloaded",
                    reason="PMC XML already exists in output_dir",
                    output_path=str(target),
                )
            else:
                xml = client.efetch_pmc_xml(decision.pmc_id)
                target.write_text(xml, encoding="utf-8")
                decision = _replace_decision(
                    decision,
                    decision="downloaded",
                    reason="PMC XML downloaded to output_dir",
                    output_path=str(target),
                )

        decisions.append(decision)
        if decision.decision == "citation_shell":
            citation_shells.append(_citation_shell(row, decision.reason))
        counts[decision.decision] = counts.get(decision.decision, 0) + 1

    if decisions_path is not None:
        write_decisions_jsonl(decisions, decisions_path)
    if citation_shells_path is not None:
        write_citation_shells_jsonl(citation_shells, citation_shells_path)

    return {
        **counts,
        "total": len(decisions),
        "decisions": decisions,
        "citation_shells": citation_shells,
    }


def write_decisions_jsonl(
    decisions: Iterable[AuditDownloadDecision],
    output_path: str | Path,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for decision in decisions:
            f.write(json.dumps(asdict(decision), ensure_ascii=False) + "\n")


def write_citation_shells_jsonl(
    citation_shells: Iterable[dict[str, Any]],
    output_path: str | Path,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for shell in citation_shells:
            f.write(json.dumps(shell, ensure_ascii=False) + "\n")


def _decision(candidate: dict[str, Any], decision: str, reason: str) -> AuditDownloadDecision:
    return AuditDownloadDecision(
        pmid=str(candidate.get("pmid") or "").strip(),
        doi=_optional_string(candidate.get("doi")),
        pmc_id=_optional_string(candidate.get("pmc_id")),
        title=str(candidate.get("title") or "").strip(),
        evidence_tier=str(candidate.get("evidence_tier") or "").strip(),
        access_status=str(candidate.get("access_status") or "").strip(),
        decision=decision,
        reason=reason,
    )


def _replace_decision(
    source: AuditDownloadDecision,
    *,
    decision: str | None = None,
    reason: str | None = None,
    output_path: str | None = None,
) -> AuditDownloadDecision:
    return AuditDownloadDecision(
        pmid=source.pmid,
        doi=source.doi,
        pmc_id=source.pmc_id,
        title=source.title,
        evidence_tier=source.evidence_tier,
        access_status=source.access_status,
        decision=decision or source.decision,
        reason=reason or source.reason,
        output_path=output_path,
    )


def _citation_shell(candidate: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "pmid": str(candidate.get("pmid") or "").strip(),
        "doi": _optional_string(candidate.get("doi")),
        "pmc_id": _optional_string(candidate.get("pmc_id")),
        "title": str(candidate.get("title") or "").strip(),
        "journal": _optional_string(candidate.get("journal")),
        "year": candidate.get("year"),
        "evidence_tier": str(candidate.get("evidence_tier") or "").strip(),
        "access_status": str(candidate.get("access_status") or "").strip(),
        "use_policy": "discovery_only",
        "allowed_use": ["gap_detection", "topic_routing", "citation_awareness"],
        "blocked_use": ["recommendation_support", "full_text_indexing"],
        "reason": reason,
    }


def _frontmatter_scalar(text: str, key: str) -> str | None:
    pattern = rf"^{re.escape(key)}:\s*['\"]?([^'\"\n]+)['\"]?\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()


def _optional_string(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True, help="Screening audit JSONL input.")
    parser.add_argument("--evidence-root", type=Path, default=Path("evidence"))
    parser.add_argument("--output-dir", type=Path, default=Path("staging/pmc_xml"))
    parser.add_argument("--decisions", type=Path, required=True, help="Decision JSONL output.")
    parser.add_argument("--citation-shells", type=Path, help="Citation shell JSONL output.")
    args = parser.parse_args(argv)

    summary = download_from_audit(
        audit_path=args.audit,
        evidence_root=args.evidence_root,
        output_dir=args.output_dir,
        decisions_path=args.decisions,
        citation_shells_path=args.citation_shells,
    )
    printable = {key: value for key, value in summary.items() if key not in {"decisions", "citation_shells"}}
    print(json.dumps(printable, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
