from typing import Literal, Any, Optional
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.pico import Pico
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade


class SrFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.SR] = EvidenceType.SR
    pico: Optional[Pico] = None
    risk_of_bias: Optional[RiskOfBias] = None
    grade: Optional[Grade] = None
    included_studies: list[str] = []


class MetaFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.META] = EvidenceType.META
    pico: Optional[Pico] = None
    risk_of_bias: Optional[RiskOfBias] = None
    grade: Optional[Grade] = None
    included_studies: list[str] = []
    heterogeneity: dict[str, Any] = {}
