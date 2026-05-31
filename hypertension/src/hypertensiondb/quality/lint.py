from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter
from pydantic import ValidationError

from hypertensiondb.schema.loader import load_evidence


@dataclass
class LintIssue:
    path: Path
    code: str
    detail: str


@dataclass
class LintReport:
    total_files: int = 0
    draft_count: int = 0
    reviewed_count: int = 0
    published_count: int = 0
    quarantined_count: int = 0
    issues: list[LintIssue] = field(default_factory=list)


def run_lint(evidence_root: Path) -> LintReport:
    """Walk evidence_root, validate every .md, return a summary report."""
    evidence_root = Path(evidence_root)
    report = LintReport()

    doi_seen: dict[str, list[Path]] = defaultdict(list)
    pmid_seen: dict[str, list[Path]] = defaultdict(list)
    id_seen: dict[str, list[Path]] = defaultdict(list)

    if not evidence_root.exists():
        return report

    for md in sorted(evidence_root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue
        report.total_files += 1

        # Parse frontmatter loosely first to spot non-schema issues
        try:
            raw = frontmatter.load(str(md))
        except Exception as e:
            report.issues.append(LintIssue(
                path=md, code="parse_error", detail=str(e),
            ))
            continue

        meta = dict(raw.metadata)
        fm_id = meta.get("id", "")

        # Filename vs id
        if fm_id and md.name != f"{fm_id}.md":
            report.issues.append(LintIssue(
                path=md, code="filename_mismatch",
                detail=f"file is '{md.name}' but frontmatter id is '{fm_id}'",
            ))

        # Pydantic full validate
        try:
            fm, _ = load_evidence(md)
            status = str(fm.status)
            if status == "draft":
                report.draft_count += 1
            elif status == "reviewed":
                report.reviewed_count += 1
            elif status == "published":
                report.published_count += 1
            elif status == "quarantined":
                report.quarantined_count += 1
        except (ValidationError, ValueError) as e:
            report.issues.append(LintIssue(
                path=md, code="schema_error", detail=str(e)[:300],
            ))
            continue

        # Cross-file duplicate trackers
        if fm_id:
            id_seen[fm_id].append(md)
        doi = meta.get("doi")
        if doi:
            doi_seen[doi].append(md)
        pmid = meta.get("pmid")
        if pmid:
            pmid_seen[pmid].append(md)

    # Emit duplicate issues
    for did, paths in id_seen.items():
        if len(paths) > 1:
            for p in paths:
                report.issues.append(LintIssue(
                    path=p, code="duplicate_id",
                    detail=f"id '{did}' also at: {[str(x) for x in paths if x != p]}",
                ))
    for doi, paths in doi_seen.items():
        if len(paths) > 1:
            for p in paths:
                report.issues.append(LintIssue(
                    path=p, code="duplicate_doi",
                    detail=f"doi '{doi}' also at: {[str(x) for x in paths if x != p]}",
                ))
    for pmid, paths in pmid_seen.items():
        if len(paths) > 1:
            for p in paths:
                report.issues.append(LintIssue(
                    path=p, code="duplicate_pmid",
                    detail=f"pmid '{pmid}' also at: {[str(x) for x in paths if x != p]}",
                ))

    return report
