from typing import Literal, Optional
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType


class LabelFrontmatter(BaseFrontmatter):
    """Frontmatter for a drug-label safety record (openFDA / DailyMed).

    Unlike study evidence (RCT/SR/META/GL/TCM) these carry no GRADE or
    risk-of-bias — a regulatory label is an authoritative primary source, not a
    graded study. The body is split into SmPC dimensions (contraindications,
    warnings/precautions, interactions, pregnancy/lactation/special populations,
    adverse reactions, optional boxed warning); see schema.sections.

    Bibliographic fields inherited from BaseFrontmatter are reused as:
      authors -> ["U.S. FDA"] (or the labeler), year -> label revision year,
      url -> DailyMed/openFDA source URL, source -> "openFDA".
    """

    type: Literal[EvidenceType.DRUG_SAFETY] = EvidenceType.DRUG_SAFETY
    drug_name: str
    drug_class: Optional[str] = None
    brand_names: list[str] = []
    # openFDA Structured Product Label identifiers (for provenance / refresh).
    spl_set_id: Optional[str] = None
    spl_version: Optional[str] = None
    effective_time: Optional[str] = None
