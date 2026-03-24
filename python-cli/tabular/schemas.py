from __future__ import annotations

from pydantic import BaseModel, Field


class SQLGenerationModel(BaseModel):
    sql: str = Field(..., min_length=1)
    referenced_columns: list[str] = Field(default_factory=list)
