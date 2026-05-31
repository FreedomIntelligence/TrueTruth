from enum import StrEnum
from typing import Any
from pydantic import BaseModel


class RobTool(StrEnum):
    ROB2 = "RoB2"
    ROBINS_I = "ROBINS-I"
    AMSTAR2 = "AMSTAR2"
    AGREE_II = "AGREE-II"


class RobOverall(StrEnum):
    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"
    NOT_ASSESSED = "not_assessed"


class GradeLevel(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"
    NOT_ASSESSED = "not_assessed"


class RiskOfBias(BaseModel):
    tool: RobTool
    overall: RobOverall
    domains: dict[str, Any] = {}


class Grade(BaseModel):
    level: GradeLevel
    reasons: list[str] = []
