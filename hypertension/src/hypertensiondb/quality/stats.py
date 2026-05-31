from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter


_DRAFT_PILEUP_RATIO = 0.20


@dataclass
class CorpusStats:
    total: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    by_grade: dict[str, int] = field(default_factory=dict)
    by_year: dict[int, int] = field(default_factory=dict)
    by_language: dict[str, int] = field(default_factory=dict)
    draft_pileup_alert: bool = False


def compute_stats(evidence_root: Path) -> CorpusStats:
    """Walk evidence_root, return aggregate stats."""
    evidence_root = Path(evidence_root)
    stats = CorpusStats()
    if not evidence_root.exists():
        return stats

    type_c: Counter[str] = Counter()
    status_c: Counter[str] = Counter()
    grade_c: Counter[str] = Counter()
    year_c: Counter[int] = Counter()
    lang_c: Counter[str] = Counter()

    for md in sorted(evidence_root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue
        try:
            raw = frontmatter.load(str(md))
        except Exception:
            continue
        m = raw.metadata
        stats.total += 1

        if m.get("type"):
            type_c[str(m["type"])] += 1
        if m.get("status"):
            status_c[str(m["status"])] += 1
        if m.get("language"):
            lang_c[str(m["language"])] += 1
        grade = (m.get("grade") or {}).get("level") if isinstance(m.get("grade"), dict) else None
        if grade:
            grade_c[str(grade)] += 1
        year = m.get("year")
        if isinstance(year, int):
            year_c[year] += 1

    stats.by_type = dict(type_c)
    stats.by_status = dict(status_c)
    stats.by_grade = dict(grade_c)
    stats.by_year = dict(year_c)
    stats.by_language = dict(lang_c)

    drafts = status_c.get("draft", 0)
    if stats.total > 0 and drafts / stats.total > _DRAFT_PILEUP_RATIO:
        stats.draft_pileup_alert = True

    return stats
