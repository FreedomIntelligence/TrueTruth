import hashlib
import uuid
from pathlib import Path

from hypertensiondb.schema.loader import load_evidence
from hypertensiondb.index.chunk import EvidenceChunk

_CLINICAL_BOTTOM_LINE_KEY = "clinical_bottom_line"
_MAX_SECTION_CHARS = 1500


def _make_point_id(evidence_id: str, section_name: str) -> str:
    """Derive a stable UUID from evidence_id + section_name."""
    sha1_bytes = hashlib.sha1(f"{evidence_id}:{section_name}".encode()).digest()
    return str(uuid.UUID(bytes=sha1_bytes[:16]))


def _frontmatter_to_metadata(fm) -> dict:
    """Extract key metadata fields from frontmatter model for Qdrant payload."""
    return {
        "evidence_id": fm.id,
        "type": str(fm.type),
        "year": fm.year,
        "language": str(fm.language),
        "status": str(fm.status),
        "grade_level": str(fm.grade.level) if getattr(fm, "grade", None) is not None else None,
        "rob_overall": str(fm.risk_of_bias.overall) if getattr(fm, "risk_of_bias", None) is not None else None,
        "tags": fm.tags,
        "title_zh": fm.title.zh,
        "title_en": fm.title.en,
        "study_type": fm.study_type,
    }


def split_evidence_into_chunks(path: Path) -> list[EvidenceChunk]:
    """Parse one evidence .md file and return its chunks.

    Returns [] if the file has status=draft or is invalid.
    """
    try:
        fm, sections = load_evidence(path)
    except Exception:
        return []

    metadata = _frontmatter_to_metadata(fm)
    chunks: list[EvidenceChunk] = []

    for section_key, text in sections.items():
        text = text.strip()
        if not text:
            continue

        if len(text) <= _MAX_SECTION_CHARS:
            chunks.append(EvidenceChunk(
                point_id=_make_point_id(fm.id, section_key),
                evidence_id=fm.id,
                section_name=section_key,
                text=text,
                is_clinical_bottom_line=(section_key == _CLINICAL_BOTTOM_LINE_KEY),
                metadata=metadata,
            ))
        else:
            sub_parts = _split_by_subheadings(text)
            # Fallback: if subheading split didn't help, split by paragraphs
            if len(sub_parts) == 1:
                sub_parts = _split_by_paragraphs(sub_parts[0], _MAX_SECTION_CHARS)
            for i, part in enumerate(sub_parts):
                part = part.strip()
                if not part:
                    continue
                sub_key = f"{section_key}_{i}"
                chunks.append(EvidenceChunk(
                    point_id=_make_point_id(fm.id, sub_key),
                    evidence_id=fm.id,
                    section_name=sub_key,
                    text=part,
                    is_clinical_bottom_line=False,
                    metadata=metadata,
                ))

    return chunks


def _split_by_subheadings(text: str) -> list[str]:
    """Split text on ### lines."""
    import re
    parts = re.split(r"(?=^###\s)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _split_by_paragraphs(text: str, max_chars: int) -> list[str]:
    """Group paragraphs into chunks not exceeding max_chars each.

    Individual paragraphs longer than max_chars are hard-split by sentences.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    # Expand paragraphs that exceed max_chars into sentence-level sub-paragraphs
    expanded: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            expanded.append(para)
        else:
            expanded.extend(_split_by_sentences(para, max_chars))

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in expanded:
        if current and current_len + len(para) + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks or [text[:max_chars]]


def _split_by_sentences(text: str, max_chars: int) -> list[str]:
    """Split text into pieces no longer than max_chars, breaking on sentence boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    parts: list[str] = []
    current_parts: list[str] = []
    current_len = 0
    for sent in sentences:
        if current_parts and current_len + len(sent) + 1 > max_chars:
            parts.append(" ".join(current_parts))
            current_parts = [sent]
            current_len = len(sent)
        else:
            current_parts.append(sent)
            current_len += len(sent) + 1
    if current_parts:
        parts.append(" ".join(current_parts))
    # Hard truncate any that are still too long (e.g. no sentence breaks)
    return [p[:max_chars] if len(p) > max_chars else p for p in parts if p.strip()]
