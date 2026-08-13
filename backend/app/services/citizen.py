from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.core.issue_types import (
    CATEGORY_LABELS,
    CATEGORY_RADIUS_METERS,
    CATEGORY_WINDOW_DAYS,
    CLOSED_STATUSES,
    IssueCategory,
    IssueStatus,
)
from app.core.storage import Storage, get_storage
from app.models import Issue, User
from app.schemas.citizen import IssueCreate, IssueResponse
from app.services.routing import resolve_department

TRACKING_ID_PREFIX = "SMC"
CASE_ID_PREFIX = "CASE"
MAX_PAGE_SIZE = 100
METERS_PER_DEGREE = 111_320.0

ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def build_tracking_id(issue_id: int, created_at: datetime | None = None) -> str:
    year = (created_at or datetime.now(timezone.utc)).year
    return f"{TRACKING_ID_PREFIX}-{year}-{issue_id:06d}"


def build_case_id(issue_id: int) -> str:
    return f"{CASE_ID_PREFIX}-{issue_id:06d}"


def sniff_image_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_photo(
    *, content: bytes, max_bytes: int, declared_content_type: str | None
) -> str:
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded photo is empty.",
        )

    if len(content) > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo is too large. Maximum size is {limit_mb:.0f} MB.",
        )

    if declared_content_type and declared_content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Please upload a JPEG, PNG, or WEBP file.",
        )

    detected_type = sniff_image_type(content)
    if detected_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file is not a valid JPEG, PNG, or WEBP image.",
        )

    return ALLOWED_IMAGE_TYPES[detected_type]


def search_box(latitude: float, radius_meters: float) -> tuple[float, float]:
    lat_delta = radius_meters / METERS_PER_DEGREE
    meters_per_lon_degree = METERS_PER_DEGREE * math.cos(math.radians(latitude))
    lon_delta = radius_meters / max(meters_per_lon_degree, 1.0)
    return lat_delta, lon_delta


def find_open_case_id(
    db: Session, *, category: IssueCategory, latitude: float, longitude: float
) -> str | None:
    radius = CATEGORY_RADIUS_METERS[category]
    window_days = CATEGORY_WINDOW_DAYS[category]

    lat_delta, lon_delta = search_box(latitude, radius)
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    return db.scalar(
        select(Issue.case_id)
        .where(
            Issue.category == category,
            Issue.latitude.between(latitude - lat_delta, latitude + lat_delta),
            Issue.longitude.between(longitude - lon_delta, longitude + lon_delta),
            Issue.created_at > cutoff,
            Issue.status.notin_(CLOSED_STATUSES),
            Issue.case_id.isnot(None),
        )
        .order_by(Issue.created_at.asc(), Issue.id.asc())
        .limit(1)
    )


def create_citizen_issue(
    db: Session,
    user: User,
    data: IssueCreate,
    *,
    photo_bytes: bytes | None = None,
    photo_extension: str | None = None,
    storage: Storage | None = None,
) -> Issue:
    matched_case_id = find_open_case_id(
        db,
        category=data.category,
        latitude=data.latitude,
        longitude=data.longitude,
    )
    department = resolve_department(db, data.category)

    photo_url = None
    if photo_bytes is not None and photo_extension is not None:
        storage = storage or get_storage()
        photo_url = storage.save(
            content=photo_bytes, extension=photo_extension, prefix="issues"
        )

    issue = Issue(
        citizen_id=user.id,
        title=CATEGORY_LABELS[data.category],
        category=data.category,
        description=data.description,
        latitude=data.latitude,
        longitude=data.longitude,
        address=data.address,
        photo_url=photo_url,
        status=IssueStatus.SUBMITTED,
        department_id=department.id if department else None,
    )
    db.add(issue)
    db.flush()

    issue.tracking_id = build_tracking_id(issue.id)
    if matched_case_id is not None:
        issue.case_id = matched_case_id
        issue.is_primary = False
    else:
        issue.case_id = build_case_id(issue.id)
        issue.is_primary = True

    db.commit()
    db.refresh(issue)
    return issue


def case_status_join():
    primary = aliased(Issue)
    join_condition = and_(
        primary.case_id == Issue.case_id, primary.is_primary.is_(True)
    )
    effective_status = func.coalesce(primary.status, Issue.status)
    return primary, join_condition, effective_status


def issue_response(
    issue: Issue, status_override: IssueStatus | None = None
) -> IssueResponse:
    response = IssueResponse.model_validate(issue)
    if status_override is not None:
        response.status = status_override
    return response


def issue_effective_status(db: Session, issue: Issue) -> IssueStatus:
    if issue.is_primary or not issue.case_id:
        return issue.status
    primary_status = db.scalar(
        select(Issue.status)
        .where(Issue.case_id == issue.case_id, Issue.is_primary.is_(True))
        .limit(1)
    )
    return primary_status or issue.status


def list_citizen_issues(
    db: Session,
    user: User,
    *,
    status_filter: IssueStatus | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Issue, IssueStatus]], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    primary, join_condition, effective_status = case_status_join()

    filters = [Issue.citizen_id == user.id]
    if status_filter is not None:
        filters.append(effective_status == status_filter)
    if search:
        term = f"%{search.strip().lower()}%"
        filters.append(
            func.lower(Issue.description).like(term)
            | func.lower(func.coalesce(Issue.address, "")).like(term)
            | func.lower(func.coalesce(Issue.tracking_id, "")).like(term)
        )

    total = (
        db.scalar(
            select(func.count())
            .select_from(Issue)
            .outerjoin(primary, join_condition)
            .where(*filters)
        )
        or 0
    )
    rows = db.execute(
        select(Issue, effective_status)
        .outerjoin(primary, join_condition)
        .where(*filters)
        .order_by(Issue.created_at.desc(), Issue.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(issue, effective) for issue, effective in rows], total


def get_citizen_issue(db: Session, user: User, issue_id: int) -> Issue:
    issue = db.get(Issue, issue_id)
    if issue is None or issue.citizen_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


def get_citizen_stats(db: Session, user: User) -> dict[str, int]:
    primary, join_condition, effective_status = case_status_join()
    rows = db.execute(
        select(effective_status, func.count())
        .select_from(Issue)
        .outerjoin(primary, join_condition)
        .where(Issue.citizen_id == user.id)
        .group_by(effective_status)
    ).all()
    counts = {issue_status: count for issue_status, count in rows}

    return {
        "total": sum(counts.values()),
        "submitted": counts.get(IssueStatus.SUBMITTED, 0),
        "under_review": counts.get(IssueStatus.UNDER_REVIEW, 0),
        "in_progress": counts.get(IssueStatus.IN_PROGRESS, 0),
        "resolved": counts.get(IssueStatus.RESOLVED, 0),
        "rejected": counts.get(IssueStatus.REJECTED, 0),
    }


def get_citizen_dashboard(db: Session, user: User, *, recent_limit: int = 5) -> dict:
    stats = get_citizen_stats(db, user)
    recent_rows, _ = list_citizen_issues(db, user, page=1, page_size=recent_limit)

    return {
        "message": "Welcome to the Citizen Dashboard.",
        "role": user.role.value,
        "email": user.email,
        "issue_count": stats["total"],
        "stats": stats,
        "recent_issues": [
            issue_response(issue, effective) for issue, effective in recent_rows
        ],
    }
