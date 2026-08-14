from datetime import datetime

from pydantic import BaseModel


class DepartmentScore(BaseModel):
    code: str
    name: str
    total_cases: int
    open_cases: int
    resolved_cases: int
    escalated_cases: int
    resolution_rate: int | None
    on_time_rate: int | None
    avg_resolution_days: float | None
    score: int | None
    grade: str | None


class TransparencyResponse(BaseModel):
    generated_at: datetime
    city: DepartmentScore
    departments: list[DepartmentScore]
    methodology: str
