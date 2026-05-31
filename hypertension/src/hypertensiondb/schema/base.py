import re
from datetime import date
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class EvidenceType(StrEnum):
    RCT = "RCT"
    SR = "SR"
    META = "META"
    GL = "GL"
    TCM = "TCM"


class Language(StrEnum):
    ZH = "zh"
    EN = "en"
    BILINGUAL = "bilingual"


class Status(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    RETRACTED = "retracted"
    QUARANTINED = "quarantined"


class FullTextStatus(StrEnum):
    COMPLETE = "complete"
    ABSTRACT_ONLY = "abstract_only"
    SECTION_PARTIAL = "section_partial"


_ID_PATTERN = re.compile(
    r"^EV-(RCT|SR|META|GL|TCM)-\d{4}-.+-\d{3}$"
)


class Title(BaseModel):
    zh: Optional[str] = None
    en: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one(self) -> "Title":
        if not self.zh and not self.en:
            raise ValueError("Title must have at least one of zh or en")
        return self


class BaseFrontmatter(BaseModel):
    id: str
    type: EvidenceType
    title: Title
    authors: list[str]
    year: int
    language: Language
    first_author_pinyin: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    full_text_status: FullTextStatus = FullTextStatus.COMPLETE
    source: Optional[str] = None
    ingested_at: Optional[date] = None
    reviewed_by: Optional[str] = None
    tags: list[str] = []
    mesh_terms: list[str] = []
    clinical_questions: list[str] = []
    status: Status = Status.DRAFT
    quality_score: Optional[float] = None
    superseded_by: Optional[str] = None
    extracted_by: Optional[str] = None
    study_type: Optional[str] = None

    @field_validator("id")
    @classmethod
    def id_must_match_pattern(cls, v: str) -> str:
        if not _ID_PATTERN.match(v):
            raise ValueError(
                f"id '{v}' does not match pattern EV-{{TYPE}}-{{YEAR}}-{{AUTHOR}}-{{NNN}}"
            )
        return v

    @field_validator("year")
    @classmethod
    def year_in_range(cls, v: int) -> int:
        current_year = date.today().year
        if not (1900 <= v <= current_year + 1):
            raise ValueError(f"year {v} out of plausible range 1900-{current_year + 1}")
        return v

    @field_validator("quality_score")
    @classmethod
    def quality_score_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("quality_score must be between 0.0 and 1.0")
        return v
