import re
from pathlib import Path

EVIDENCE_ROOT = Path(__file__).parent.parent.parent.parent / "evidence"

_VALID_TYPES = {"RCT", "SR", "META", "GL", "TCM"}


def next_id(ev_type: str, year: int, author_pinyin: str) -> str:
    """Return the next available evidence ID for the given type/year/author."""
    ev_type = ev_type.upper()
    author_pinyin = author_pinyin.upper()
    if ev_type not in _VALID_TYPES:
        raise ValueError(f"Unknown evidence type: {ev_type}")

    prefix = f"EV-{ev_type}-{year}-{author_pinyin}-"
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)

    existing = sorted(EVIDENCE_ROOT.glob(f"{prefix}*.md"))
    if not existing:
        serial = 1
    else:
        pattern = re.compile(rf"{re.escape(prefix)}(\d+)\.md$")
        serials = [
            int(m.group(1))
            for f in existing
            if (m := pattern.search(f.name))
        ]
        serial = max(serials) + 1 if serials else 1

    return f"{prefix}{serial:03d}"
