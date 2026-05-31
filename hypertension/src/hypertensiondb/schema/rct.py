from typing import Literal, Optional
from pydantic import model_validator
from hypertensiondb.schema.base import BaseFrontmatter, EvidenceType
from hypertensiondb.schema.pico import Pico
from hypertensiondb.schema.bias_grade import RiskOfBias, Grade


class RctFrontmatter(BaseFrontmatter):
    type: Literal[EvidenceType.RCT] = EvidenceType.RCT
    pico: Optional[Pico] = None
    risk_of_bias: Optional[RiskOfBias] = None
    grade: Optional[Grade] = None

    @model_validator(mode="after")
    def type_must_be_rct(self) -> "RctFrontmatter":
        if self.type != EvidenceType.RCT:
            raise ValueError("RctFrontmatter requires type=RCT")
        return self
