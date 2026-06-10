"""Shared interface for baseline comparison pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from src.state.schema import Evidence


@dataclass
class BaselineResult:
    pipeline_name: str
    question: str
    response_text: str
    evidence_used: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    llm_calls: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def format_evidence_block(evidence: list[Evidence]) -> str:
    """Format a list of Evidence objects into a numbered text block for RAG prompts."""
    if not evidence:
        return "（未检索到相关医学证据）"

    blocks: list[str] = []
    for i, ev in enumerate(evidence, 1):
        parts: list[str] = []
        header = f"[证据 {i}]"
        if ev.title:
            header += f" {ev.title}"
        meta_parts: list[str] = []
        if ev.year:
            meta_parts.append(f"年份: {ev.year}")
        if ev.study_type:
            meta_parts.append(f"研究类型: {ev.study_type}")
        if meta_parts:
            header += f" ({', '.join(meta_parts)})"
        parts.append(header)

        for j, p in enumerate(ev.supporting_passages or [], 1):
            section = f"[{p.section}] " if p.section else ""
            parts.append(f"  段落{j}: {section}\"{p.snippet}\"")

        blocks.append("\n".join(parts))

    return "\n\n".join(blocks)
