from typing import Literal, Any, Optional
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.pico import Pico
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade


class TcmFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.TCM] = EvidenceType.TCM
    pico: Optional[Pico] = None
    risk_of_bias: Optional[RiskOfBias] = None
    grade: Optional[Grade] = None
    tcm_syndrome: dict[str, Any] = {}
