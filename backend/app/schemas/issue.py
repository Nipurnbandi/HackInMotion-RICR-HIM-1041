from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.issue_types import IssueCategory, IssueStatus

DESCRIPTION_MIN_LENGTH = 10
DESCRIPTION_MAX_LENGTH = 2000


class IssueCreate(BaseModel):
    """Citizen-supplied fields for a new report.

    Deliberately has no ``citizen_id`` or ``status`` field — ownership comes
    from the JWT and new reports always start at SUBMITTED.
    """

    category: IssueCategory
    description: str = Field(min_length=1, max_length=DESCRIPTION_MAX_LENGTH)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = Field(default=None, max_length=500)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < DESCRIPTION_MIN_LENGTH:
            raise ValueError(
                f"Description must be at least {DESCRIPTION_MIN_LENGTH} characters."
            )
        return trimmed

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class IssueResponse(BaseModel):
    id: int
    tracking_id: str | None
    category: IssueCategory
    description: str
    latitude: float | None
    longitude: float | None
    address: str | None
    photo_url: str | None
    status: IssueStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    items: list[IssueResponse]
    total: int
    page: int
    page_size: int


class IssueStats(BaseModel):
    total: int
    submitted: int
    under_review: int
    in_progress: int
    resolved: int
    rejected: int


class CitizenDashboardResponse(BaseModel):
    message: str
    role: str
    email: str
    issue_count: int
    stats: IssueStats
    recent_issues: list[IssueResponse]


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
    """Admin listings additionally expose who filed the report."""

    title: str
    citizen_id: int


class AdminCaseResponse(AdminIssueResponse):
    """One row per case in the city's priority-ordered work queue."""

    citizen_count: int
    days_open: int
    priority_score: float


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: IssueStatus | None = None
