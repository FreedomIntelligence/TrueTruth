import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml



_SECTION_HEADINGS = {
    "clinical_bottom_line": "## 临床要点 / Clinical Bottom Line",
    "abstract_zh": "## 中文摘要",
    "abstract_en": "## English Abstract",
    "background": "## 背景 / Background",
    "methods": "## 方法 / Methods",
    "results": "## 结果 / Results",
    "discussion": "## 讨论 / Discussion",
    "conclusion": "## 结论 / Conclusion",
}


@dataclass
class EvidenceWriteResult:
    path: Path
    evidence_id: str


def _render_markdown(frontmatter: dict, sections: dict) -> str:
    yaml_block = yaml.safe_dump(
        frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    body_parts: list[str] = []
    for key, heading in _SECTION_HEADINGS.items():
        text = sections.get(key, "").strip()
        if not text:
            continue
        body_parts.append(f"{heading}\n\n{text}")

    body = "\n\n".join(body_parts) if body_parts else "## 结果 / Results\n\n(content pending)"
    return f"---\n{yaml_block}---\n\n{body}\n"


def write_evidence_md(
    frontmatter: dict,
    sections: dict,
    evidence_root: Path,
    overwrite: bool = False,
) -> EvidenceWriteResult:
    """Write a complete evidence .md file to evidence_root/{type_subdir}/{id}.md.

    Raises FileExistsError if file already exists and overwrite=False.
    """
    ev_id = frontmatter.get("id")
    if not ev_id:
        raise ValueError("frontmatter.id is required")

    evidence_root.mkdir(parents=True, exist_ok=True)
    target = evidence_root / f"{ev_id}.md"

    if target.exists() and not overwrite:
        raise FileExistsError(f"Evidence file already exists: {target}")

    content = _render_markdown(frontmatter, sections)
    target.write_text(content, encoding="utf-8")
    return EvidenceWriteResult(path=target, evidence_id=ev_id)


def write_quarantine_md(
    partial_frontmatter: dict,
    sections: dict,
    error: str,
    evidence_root: Path,
    source_filename: str,
) -> EvidenceWriteResult:
    """Write a quarantine record for evidence that failed Pydantic validation.

    Filename is timestamped to avoid collisions when many bad inputs arrive.
    """
    subdir = evidence_root / "_quarantine"
    subdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"quarantine-{ts}-{int(time.monotonic_ns() % 1_000_000):06d}"
    target = subdir / f"{name}.md"

    header = {
        "_quarantine_error": error,
        "_quarantine_source": source_filename,
        "_quarantine_at": ts,
        **partial_frontmatter,
    }
    content = _render_markdown(header, sections)
    target.write_text(content, encoding="utf-8")
    return EvidenceWriteResult(path=target, evidence_id=name)
