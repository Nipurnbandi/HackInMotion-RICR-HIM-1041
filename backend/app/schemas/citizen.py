from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.issue_types import IssueCategory, IssueStatus
from app.core.roles import Role

DESCRIPTION_MIN_LENGTH = 10
DESCRIPTION_MAX_LENGTH = 2000


class IssueCreate(BaseModel):
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
    resolution_note: str = ""
    resolution_photo_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatusHistoryResponse(BaseModel):
    id: int
    old_status: IssueStatus | None
    new_status: IssueStatus
    note: str
    photo_url: str | None
    changed_by_role: Role
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueDetailResponse(IssueResponse):
    history: list[StatusHistoryResponse] = []


class MapIssueResponse(BaseModel):
    id: int
    tracking_id: str | None
    category: IssueCategory
    status: IssueStatus
    latitude: float
    longitude: float
    address: str | None
    created_at: datetime
    report_count: int
    citizen_count: int
    vote_count: int = 0
    has_voted: bool = False
    escalated: bool = False
    department_name: str | None


class VoteResponse(BaseModel):
    issue_id: int
    vote_count: int
    has_voted: bool


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
