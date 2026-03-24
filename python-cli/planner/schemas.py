from __future__ import annotations

from pydantic import BaseModel, Field


class PlanStepModel(BaseModel):
    step: int = Field(..., ge=1)
    action: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)


class StructuredPlanModel(BaseModel):
    goal: str = Field(..., min_length=1)
    steps: list[PlanStepModel] = Field(..., min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
