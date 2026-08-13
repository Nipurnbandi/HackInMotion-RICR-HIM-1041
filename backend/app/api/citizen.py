from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.issue_types import IssueStatus
from app.core.roles import Role
from app.models import User
from app.schemas.issue import (
    CitizenDashboardResponse,
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueStats,
)
from app.services.issue import (
    create_citizen_issue,
    get_citizen_dashboard,
    get_citizen_issue,
    get_citizen_stats,
    issue_effective_status,
    issue_response,
    list_citizen_issues,
    validate_photo,
)

router = APIRouter(prefix="/citizen", tags=["citizen"])

citizen_only = require_roles(Role.CITIZEN)


def parse_issue_form(
    category: Annotated[str, Form()],
    description: Annotated[str, Form()],
    latitude: Annotated[float, Form()],
    longitude: Annotated[float, Form()],
    address: Annotated[str | None, Form()] = None,
) -> IssueCreate:
    try:
        return IssueCreate(
            category=category,
            description=description,
            latitude=latitude,
            longitude=longitude,
            address=address,
        )
    except ValidationError as exc:
        raise RequestValidationError(
            [
                {
                    "type": error["type"],
                    "loc": ("body", *error["loc"]),
                    "msg": error["msg"],
                }
                for error in exc.errors()
            ]
        ) from exc


@router.get("/dashboard", response_model=CitizenDashboardResponse)
def citizen_dashboard(
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    return get_citizen_dashboard(db, current_user)


@router.get("/issues/stats", response_model=IssueStats)
def citizen_issue_stats(
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    return get_citizen_stats(db, current_user)


@router.post(
    "/issues", response_model=IssueResponse, status_code=status.HTTP_201_CREATED
)
async def create_issue(
    data: Annotated[IssueCreate, Depends(parse_issue_form)],
    photo: Annotated[UploadFile | None, File()] = None,
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    photo_bytes: bytes | None = None
    photo_extension: str | None = None

    if photo is not None and photo.filename:
        photo_bytes = await photo.read(settings.max_upload_size_bytes + 1)
        photo_extension = validate_photo(
            content=photo_bytes,
            max_bytes=settings.max_upload_size_bytes,
            declared_content_type=photo.content_type,
        )

    return create_citizen_issue(
        db,
        current_user,
        data,
        photo_bytes=photo_bytes,
        photo_extension=photo_extension,
    )


@router.get("/issues", response_model=IssueListResponse)
def get_my_issues(
    status_filter: Annotated[IssueStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    rows, total = list_citizen_issues(
        db,
        current_user,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
    return IssueListResponse(
        items=[issue_response(issue, effective) for issue, effective in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/issues/{issue_id}", response_model=IssueResponse)
def get_my_issue(
    issue_id: int,
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    issue = get_citizen_issue(db, current_user, issue_id)
    return issue_response(issue, issue_effective_status(db, issue))
