"""Citizen issue reporting business logic.

Routers stay thin: they authenticate, authorize, and delegate here.
"""

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
    SEVERITY_WEIGHTS,
    IssueCategory,
    IssueStatus,
)
from app.core.storage import Storage, get_storage
from app.models import Issue, User
from app.schemas.issue import IssueCreate, IssueResponse

TRACKING_ID_PREFIX = "SMC"
CASE_ID_PREFIX = "CASE"

MAX_PAGE_SIZE = 100

# --- case grouping tuning -------------------------------------------------

#: A closed case is never joined: a problem that reappears after being fixed
#: is a new problem, and must surface as one.
CLOSED_STATUSES = (IssueStatus.RESOLVED, IssueStatus.REJECTED)

#: One degree of latitude, in metres (constant everywhere on Earth).
_METERS_PER_DEGREE = 111_320.0

#: Accepted image types mapped to (magic-byte checker, canonical extension).
ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _sniff_image_type(content: bytes) -> str | None:
    """Return a MIME type inferred from magic bytes, or None if unrecognised.

    The client-supplied filename and Content-Type are never trusted on their own.
    """
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def build_tracking_id(issue_id: int, created_at: datetime | None = None) -> str:
    year = (created_at or datetime.now(timezone.utc)).year
    return f"{TRACKING_ID_PREFIX}-{year}-{issue_id:06d}"


def build_case_id(issue_id: int) -> str:
    """Case label derived from the primary report's id, e.g. CASE-000012."""
    return f"{CASE_ID_PREFIX}-{issue_id:06d}"


def _search_box(latitude: float, radius_meters: float) -> tuple[float, float]:
    """Convert a radius in metres into (lat_delta, lon_delta) degrees.

    Longitude degrees shrink with distance from the equator, hence the cosine.
    """
    lat_delta = radius_meters / _METERS_PER_DEGREE
    meters_per_lon_degree = _METERS_PER_DEGREE * math.cos(math.radians(latitude))
    lon_delta = radius_meters / max(meters_per_lon_degree, 1.0)
    return lat_delta, lon_delta


def find_open_case_id(
    db: Session, *, category: IssueCategory, latitude: float, longitude: float
) -> str | None:
    """The duplicate check: four conditions, all required.

    Same category, inside the category's own search box, reported within the
    category's own time window, and the case is still open. Radius and window
    come from the physics of each problem — a water leak spreads 80 m down a
    street, a pothole is a 25 m point; a pothole sits for 60 days, a garbage
    bin report is stale after 3. Returns the matched case label (never a
    report id, so joiners always attach directly to the case — chains are
    impossible), or None when this is a new problem.
    """
    radius = CATEGORY_RADIUS_METERS[category]
    window_days = CATEGORY_WINDOW_DAYS[category]

    lat_delta, lon_delta = _search_box(latitude, radius)
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


def validate_photo(
    *, content: bytes, max_bytes: int, declared_content_type: str | None
) -> str:
    """Validate an uploaded photo and return its canonical extension."""
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

    sniffed = _sniff_image_type(content)
    if sniffed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file is not a valid JPEG, PNG, or WEBP image.",
        )

    return ALLOWED_IMAGE_TYPES[sniffed]


def create_citizen_issue(
    db: Session,
    user: User,
    data: IssueCreate,
    *,
    photo_bytes: bytes | None = None,
    photo_extension: str | None = None,
    storage: Storage | None = None,
) -> Issue:
    """Persist a new report owned by ``user``.

    Ownership and status are set server-side; nothing in ``data`` can influence
    either. The duplicate check runs here silently: the report is always saved
    and always gets its own tracking ID — the only difference is which case
    label it carries. The citizen is never told.
    """
    # Before the insert, so the query cannot match the report itself.
    matched_case_id = find_open_case_id(
        db,
        category=data.category,
        latitude=data.latitude,
        longitude=data.longitude,
    )

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
    )
    db.add(issue)
    # Flush to obtain the primary key the tracking ID is derived from, so the
    # identifier is unique without a second sequence or a retry loop.
    db.flush()
    issue.tracking_id = build_tracking_id(issue.id)

    if matched_case_id is not None:
        # Same problem already on file: join its case.
        issue.case_id = matched_case_id
        issue.is_primary = False
    else:
        # A new problem: this report opens the case and represents it in lists.
        issue.case_id = build_case_id(issue.id)
        issue.is_primary = True

    db.commit()
    db.refresh(issue)
    return issue


def _effective_status_columns():
    """Aliased self-join giving each report its display status.

    Status belongs to the case: a joined report shows its primary's status,
    a primary shows its own. LEFT JOIN + coalesce, so a report whose primary
    was deleted still displays rather than disappearing.
    """
    primary = aliased(Issue)
    on_primary = and_(primary.case_id == Issue.case_id, primary.is_primary.is_(True))
    effective_status = func.coalesce(primary.status, Issue.status)
    return primary, on_primary, effective_status


def issue_response(issue: Issue, status_override: IssueStatus | None = None) -> IssueResponse:
    """Serialize a report, substituting the case's status when supplied.

    The override is applied at the response layer on purpose: the ORM row is
    never mutated, so a stray flush can't write a citizen-visible status back.
    """
    response = IssueResponse.model_validate(issue)
    if status_override is not None:
        response.status = status_override
    return response


def issue_effective_status(db: Session, issue: Issue) -> IssueStatus:
    """Display status for a single report: its case's status."""
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
    """Return ``([(issue, effective_status)], total)`` for the citizen.

    Deliberately unfiltered by ``is_primary`` — a citizen always sees their own
    reports. The status filter matches the effective (case) status, so a report
    whose case moved on is found under its real state.
    """
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    primary, on_primary, effective_status = _effective_status_columns()

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
            .outerjoin(primary, on_primary)
            .where(*filters)
        )
        or 0
    )
    rows = db.execute(
        select(Issue, effective_status)
        .outerjoin(primary, on_primary)
        .where(*filters)
        .order_by(Issue.created_at.desc(), Issue.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(issue, effective) for issue, effective in rows], total


def get_citizen_issue(db: Session, user: User, issue_id: int) -> Issue:
    """Fetch one issue, refusing anything the citizen does not own.

    Returns 404 rather than 403 for someone else's issue so IDs cannot be
    probed for existence.
    """
    issue = db.get(Issue, issue_id)
    if issue is None or issue.citizen_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


def get_citizen_stats(db: Session, user: User) -> dict[str, int]:
    """Personal counts, bucketed by effective (case) status."""
    primary, on_primary, effective_status = _effective_status_columns()
    rows = db.execute(
        select(effective_status, func.count())
        .select_from(Issue)
        .outerjoin(primary, on_primary)
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


def list_admin_cases(db: Session) -> list[dict]:
    """The city's work queue: one row per case, ordered by priority.

    priority = severity x citizens x (1 + days_open / 7)

    - severity: how dangerous the category is (water leak outranks garbage)
    - citizens: COUNT(DISTINCT citizen_id) across the case — one person
      submitting five reports still counts as one voice, so spamming is useless
    - age: an ignored problem climbs the list by itself, so a lonely street's
      single report cannot starve behind busy-road potholes forever

    Everything derives from columns that already exist; nothing is stored, so
    the score is always correct after merges, splits, or deletions.
    """
    member = aliased(Issue)
    citizens = func.count(func.distinct(member.citizen_id))

    rows = db.execute(
        select(Issue, citizens)
        .join(member, member.case_id == Issue.case_id)
        .where(Issue.is_primary.is_(True))
        .group_by(Issue.id)
    ).all()

    now = datetime.now(timezone.utc)
    cases = []
    for issue, citizen_count in rows:
        created = issue.created_at
        if created.tzinfo is None:  # SQLite stores naive UTC
            created = created.replace(tzinfo=timezone.utc)
        days_open = max((now - created).days, 0)

        priority = round(
            SEVERITY_WEIGHTS[issue.category] * citizen_count * (1 + days_open / 7), 1
        )
        cases.append(
            {
                "issue": issue,
                "citizen_count": citizen_count,
                "days_open": days_open,
                "priority_score": priority,
            }
        )

    cases.sort(key=lambda case: case["priority_score"], reverse=True)
    return cases


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
