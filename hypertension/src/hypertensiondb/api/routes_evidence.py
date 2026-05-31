import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from hypertensiondb.schema.loader import load_evidence

router = APIRouter()


class EvidenceListItem(BaseModel):
    evidence_id: str
    type: str
    year: int
    language: str
    title: dict
    status: str
    grade_level: Optional[str] = None
    source_path: str


class EvidenceListResponse(BaseModel):
    items: list[EvidenceListItem]
    total: int


class EvidenceDetailResponse(BaseModel):
    evidence_id: str
    frontmatter: dict
    sections: dict
    source_path: str


def _evidence_root() -> Path:
    return Path(os.getenv("EVIDENCE_ROOT", "evidence"))


def _find_file_by_id(evidence_id: str) -> Optional[Path]:
    root = _evidence_root()
    if not root.exists():
        return None
    matches = list(root.rglob(f"{evidence_id}.md"))
    return matches[0] if matches else None


@router.get("/evidence/{evidence_id}", response_model=EvidenceDetailResponse)
def get_evidence(evidence_id: str) -> EvidenceDetailResponse:
    path = _find_file_by_id(evidence_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")
    try:
        fm, sections = load_evidence(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse: {e}")
    return EvidenceDetailResponse(
        evidence_id=fm.id,
        frontmatter=fm.model_dump(mode="json"),
        sections=sections,
        source_path=str(path),
    )


@router.get("/evidence", response_model=EvidenceListResponse)
def list_evidence(
    type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None, ge=1900, le=2100),
    year_max: Optional[int] = Query(None, ge=1900, le=2100),
    tags: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> EvidenceListResponse:
    root = _evidence_root()
    if not root.exists():
        return EvidenceListResponse(items=[], total=0)

    type_set = {t.strip() for t in type.split(",")} if type else None
    lang_set = {l.strip() for l in language.split(",")} if language else None
    tags_set = {t.strip() for t in tags.split(",")} if tags else None
    status_set = {s.strip() for s in status.split(",")} if status else None

    items: list[EvidenceListItem] = []
    for md in sorted(root.rglob("*.md")):
        if "_quarantine" in md.parts:
            continue
        try:
            fm, _ = load_evidence(md)
        except Exception:
            continue
        if type_set and str(fm.type) not in type_set:
            continue
        if lang_set and str(fm.language) not in lang_set:
            continue
        if year_min is not None and fm.year < year_min:
            continue
        if year_max is not None and fm.year > year_max:
            continue
        if tags_set and not (set(fm.tags) & tags_set):
            continue
        if status_set and str(fm.status) not in status_set:
            continue

        items.append(EvidenceListItem(
            evidence_id=fm.id,
            type=str(fm.type),
            year=fm.year,
            language=str(fm.language),
            title={"zh": fm.title.zh, "en": fm.title.en},
            status=str(fm.status),
            grade_level=str(fm.grade.level) if hasattr(fm, "grade") and fm.grade else None,
            source_path=str(md),
        ))
        if len(items) >= limit:
            break

    return EvidenceListResponse(items=items, total=len(items))
