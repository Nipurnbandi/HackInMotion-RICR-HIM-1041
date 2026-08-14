from datetime import datetime

from pydantic import BaseModel, Field

from app.core.issue_types import IssueCategory, IssueStatus
from app.schemas.citizen import DESCRIPTION_MAX_LENGTH, IssueResponse


class AdminDashboardResponse(BaseModel):
    message: str
    role: str
    total_issues: int
    total_citizens: int


class CategoryCount(BaseModel):
    category: IssueCategory
    label: str
    count: int


class StatusCount(BaseModel):
    status: IssueStatus
    count: int


class DepartmentPerformance(BaseModel):
    code: str | None
    name: str
    total_cases: int
    open_cases: int
    resolved_cases: int
    avg_resolution_days: float | None


class HotspotResponse(BaseModel):
    latitude: float
    longitude: float
    case_count: int
    report_count: int
    address: str | None
    top_category: IssueCategory
    top_category_label: str


class AdminAnalyticsResponse(BaseModel):
    total_issues: int
    open_issues: int
    closed_issues: int
    total_citizens: int
    total_reports: int
    avg_resolution_days: float | None
    by_category: list[CategoryCount]
    by_status: list[StatusCount]
    departments: list[DepartmentPerformance]
    hotspots: list[HotspotResponse]


class AdminIssueResponse(IssueResponse):
    title: str
    citizen_id: int


class AdminCaseResponse(AdminIssueResponse):
    citizen_count: int
    vote_count: int
    days_open: int
    priority_score: float
    escalated: bool
    sla_days: int
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
    department_name: str
    department_email: str


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread: int


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: IssueStatus | None = None
    resolution_note: str | None = Field(
        default=None, max_length=DESCRIPTION_MAX_LENGTH
    )
