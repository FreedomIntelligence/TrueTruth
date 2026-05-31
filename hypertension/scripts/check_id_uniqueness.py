#!/usr/bin/env python3
"""Check that all evidence IDs are unique across the evidence/ directory."""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import frontmatter

EVIDENCE_ROOT = Path("evidence")


def main() -> None:
    ids: list[tuple[str, Path]] = []
    for md in EVIDENCE_ROOT.rglob("*.md"):
        if "_quarantine" in md.parts:
            continue
        try:
            raw = frontmatter.load(str(md))
            ev_id = raw.metadata.get("id", "")
            if ev_id:
                ids.append((ev_id, md))
        except Exception:
            pass

    counter = Counter(ev_id for ev_id, _ in ids)
    duplicates = [ev_id for ev_id, count in counter.items() if count > 1]

    if duplicates:
        print("Duplicate evidence IDs found:")
        for dup_id in duplicates:
            paths = [str(p) for ev_id, p in ids if ev_id == dup_id]
            print(f"  {dup_id}: {paths}")
        sys.exit(1)
    else:
        print(f"OK: {len(ids)} unique evidence IDs")
        sys.exit(0)


if __name__ == "__main__":
    main()
