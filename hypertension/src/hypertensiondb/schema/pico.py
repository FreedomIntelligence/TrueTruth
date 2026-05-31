from typing import Optional
from pydantic import BaseModel, model_validator


class EffectSize(BaseModel):
    metric: Optional[str] = None
    value: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    p: Optional[float] = None

    @model_validator(mode="after")
    def ci_low_lt_ci_high(self) -> "EffectSize":
        if self.ci_low is not None and self.ci_high is not None:
            if self.ci_low > self.ci_high:
                raise ValueError("ci_low must be less than or equal to ci_high")
        return self


class Outcome(BaseModel):
    name: str
    effect_size: Optional[EffectSize] = None
    note: Optional[str] = None


class Outcomes(BaseModel):
    primary: list[Outcome] = []
    secondary: list[Outcome] = []


class Population(BaseModel):
    condition: str
    severity: Optional[str] = None
    age_range: Optional[str] = None
    sample_size: Optional[int] = None
    inclusion: list[str] = []
    exclusion: list[str] = []


class Intervention(BaseModel):
    name: str
    drug_class: list[str] = []
    dosage: Optional[str] = None
    duration_weeks: Optional[int] = None


class Comparison(BaseModel):
    name: str


class Pico(BaseModel):
    population: Population
    intervention: Intervention
    comparison: Optional[Comparison] = None
    outcomes: Outcomes = Outcomes()
