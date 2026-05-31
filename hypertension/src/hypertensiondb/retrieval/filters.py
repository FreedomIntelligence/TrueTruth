from dataclasses import dataclass, field
from typing import Optional

from qdrant_client import models as qm

_GRADE_ORDER = ["very_low", "low", "moderate", "high"]
_INDEXED_STATUSES = ["reviewed", "published"]


@dataclass
class SearchFilters:
    types: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    grade_min: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    include_draft: Optional[bool] = None

    def _has_any_constraint(self) -> bool:
        return bool(
            self.types
            or self.languages
            or self.year_min is not None
            or self.year_max is not None
            or self.grade_min
            or self.tags
            or self.sections
            or self.include_draft is not None
        )


def _grade_levels_at_or_above(grade_min: str) -> list[str]:
    """Return GRADE levels >= grade_min, e.g. 'moderate' -> ['moderate', 'high']."""
    if grade_min not in _GRADE_ORDER:
        raise ValueError(f"Invalid grade: {grade_min!r}")
    idx = _GRADE_ORDER.index(grade_min)
    return _GRADE_ORDER[idx:]


def build_qdrant_filter(filters: SearchFilters) -> Optional[qm.Filter]:
    """Translate SearchFilters into a Qdrant Filter (or None if no constraints)."""
    must: list[qm.FieldCondition] = []

    if filters.types:
        must.append(qm.FieldCondition(
            key="type", match=qm.MatchAny(any=filters.types)
        ))
    if filters.languages:
        must.append(qm.FieldCondition(
            key="language", match=qm.MatchAny(any=filters.languages)
        ))
    if filters.year_min is not None or filters.year_max is not None:
        must.append(qm.FieldCondition(
            key="year",
            range=qm.Range(gte=filters.year_min, lte=filters.year_max),
        ))
    if filters.grade_min:
        must.append(qm.FieldCondition(
            key="grade_level",
            match=qm.MatchAny(any=_grade_levels_at_or_above(filters.grade_min)),
        ))
    if filters.tags:
        must.append(qm.FieldCondition(
            key="tags", match=qm.MatchAny(any=filters.tags)
        ))
    if filters.sections:
        must.append(qm.FieldCondition(
            key="section_name", match=qm.MatchAny(any=filters.sections)
        ))
    if filters.include_draft is False:
        must.append(qm.FieldCondition(
            key="status", match=qm.MatchAny(any=_INDEXED_STATUSES)
        ))

    if not must:
        return None
    return qm.Filter(must=must)
