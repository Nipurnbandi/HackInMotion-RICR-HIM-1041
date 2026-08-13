from pydantic import BaseModel, Field

from app.core.issue_types import IssueStatus
from app.schemas.citizen import DESCRIPTION_MAX_LENGTH, IssueResponse


class AdminDashboardResponse(BaseModel):
    message: str
    role: str
    total_issues: int
    total_citizens: int


class AdminAnalyticsResponse(BaseModel):
    total_issues: int
    open_issues: int
    closed_issues: int
    total_citizens: int


class AdminIssueResponse(IssueResponse):
    title: str
    citizen_id: int


class AdminCaseResponse(AdminIssueResponse):
    citizen_count: int
    days_open: int
    priority_score: float


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: IssueStatus | None = None
