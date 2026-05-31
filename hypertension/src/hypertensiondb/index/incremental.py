from datetime import datetime, timezone
from pathlib import Path

from hypertensiondb.schema.loader import load_evidence
from hypertensiondb.index.qdrant_index_client import QdrantIndexClient


def find_files_needing_reindex(
    evidence_root: Path,
    qdrant_client: QdrantIndexClient,
) -> list[Path]:
    """Return .md files that are new or modified since they were last indexed."""
    needs_reindex: list[Path] = []

    for md in sorted(evidence_root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue

        try:
            fm, _ = load_evidence(md)
        except Exception:
            continue

        indexed_at_str = qdrant_client.get_evidence_indexed_at(fm.id)
        if indexed_at_str is None:
            needs_reindex.append(md)
            continue

        file_mtime = datetime.fromtimestamp(md.stat().st_mtime, tz=timezone.utc)
        indexed_at = datetime.fromisoformat(indexed_at_str)
        if indexed_at.tzinfo is None:
            indexed_at = indexed_at.replace(tzinfo=timezone.utc)

        # Tolerance to absorb clock-resolution skew between filesystem mtime
        # (sub-millisecond on Windows NTFS) and wall-clock timestamps from
        # datetime.now() (which can round down on Windows). Without this,
        # a file indexed immediately after writing can appear "modified after
        # indexing" by a few hundred microseconds.
        if (file_mtime - indexed_at).total_seconds() > 1.0:
            needs_reindex.append(md)

    return needs_reindex
