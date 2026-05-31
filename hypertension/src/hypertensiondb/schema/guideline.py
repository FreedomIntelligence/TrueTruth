from typing import Literal, Optional
from pydantic import BaseModel
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.bias_grade import RiskOfBias, GradeLevel


class Recommendation(BaseModel):
    text: str
    strength: Optional[str] = None
    grade: Optional[GradeLevel] = None
    note: Optional[str] = None


class GuidelineFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.GL] = EvidenceType.GL
    risk_of_bias: Optional[RiskOfBias] = None
    recommendations: list[Recommendation] = []
    target_population: Optional[str] = None
    scope: Optional[str] = None
