from datetime import datetime

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
    department_code: str | None
    department_name: str | None


class DepartmentResponse(BaseModel):
    code: str
    name: str
    email: str
    open_cases: int


class NotificationResponse(BaseModel):
    id: int
    message: str
    is_read: bool
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread: int


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: IssueStatus | None = None
