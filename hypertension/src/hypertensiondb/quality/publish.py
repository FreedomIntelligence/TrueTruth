from pathlib import Path
from typing import Literal

import frontmatter


class PublishError(Exception):
    """Raised when a publish attempt fails."""


_VALID_TARGETS = {"reviewed", "published"}
_ALLOWED_TRANSITIONS = {
    ("draft", "reviewed"),
    ("reviewed", "published"),
    ("draft", "published"),  # skip review only if reviewed_by set
}


def _find_by_id(evidence_id: str, evidence_root: Path) -> Path | None:
    if not evidence_root.exists():
        return None
    matches = list(evidence_root.rglob(f"{evidence_id}.md"))
    return matches[0] if matches else None


def publish_evidence(
    evidence_id: str,
    evidence_root: Path,
    target_status: Literal["reviewed", "published"],
) -> Path:
    """Promote a draft/reviewed file to a higher status.

    Raises PublishError on any safety violation.
    """
    if target_status not in _VALID_TARGETS:
        raise PublishError(
            f"target_status must be one of {_VALID_TARGETS}, got {target_status!r}"
        )

    path = _find_by_id(evidence_id, evidence_root)
    if path is None:
        raise PublishError(f"Evidence not found: {evidence_id}")

    post = frontmatter.load(str(path))
    meta = dict(post.metadata)
    current = str(meta.get("status", "draft"))

    if (current, target_status) not in _ALLOWED_TRANSITIONS:
        raise PublishError(
            f"Cannot transition status {current!r} → {target_status!r}"
        )

    # LLM-extracted drafts MUST have a human reviewer before promotion.
    extracted_by = meta.get("extracted_by")
    reviewed_by = meta.get("reviewed_by")
    if extracted_by == "llm" and not reviewed_by:
        raise PublishError(
            f"Refusing to promote LLM-extracted draft without human review. "
            f"Set extracted_by='human' or reviewed_by=<name> before publishing."
        )

    meta["status"] = target_status
    post.metadata = meta
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path
