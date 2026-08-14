from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.issue_types import IssueStatus
from app.core.roles import Role
from app.models import User
from app.schemas.citizen import (
    CitizenDashboardResponse,
    IssueCreate,
    IssueDetailResponse,
    IssueListResponse,
    IssueResponse,
    IssueStats,
    MapIssueResponse,
)
from app.services.citizen import (
    create_citizen_issue,
    get_citizen_dashboard,
    get_citizen_issue,
    get_citizen_stats,
    issue_detail_response,
    issue_effective_status,
    issue_response,
    list_citizen_issues,
    validate_photo,
)
from app.services.city_map import list_map_issues
from app.services.lifecycle import confirm_resolution, reopen_issue
from app.services.notification import notify_new_case, send_pending_notifications

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


@router.get("/map", response_model=list[MapIssueResponse])
def citizen_city_map(
    _: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    return list_map_issues(db)


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
    background_tasks: BackgroundTasks,
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

    issue = create_citizen_issue(
        db,
        current_user,
        data,
        photo_bytes=photo_bytes,
        photo_extension=photo_extension,
    )

    if issue.is_primary:
        notify_new_case(db, issue)
        background_tasks.add_task(send_pending_notifications)

    return issue


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


@router.get("/issues/{issue_id}", response_model=IssueDetailResponse)
def get_my_issue(
    issue_id: int,
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    issue = get_citizen_issue(db, current_user, issue_id)
    return issue_detail_response(db, issue, issue_effective_status(db, issue))


@router.post("/issues/{issue_id}/confirm", response_model=IssueDetailResponse)
def confirm_my_issue(
    issue_id: int,
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    issue = get_citizen_issue(db, current_user, issue_id)
    issue = confirm_resolution(db, issue)
    return issue_detail_response(db, issue, issue_effective_status(db, issue))


@router.post("/issues/{issue_id}/reopen", response_model=IssueDetailResponse)
def reopen_my_issue(
    issue_id: int,
    current_user: User = Depends(citizen_only),
    db: Session = Depends(get_db),
):
    issue = get_citizen_issue(db, current_user, issue_id)
    issue = reopen_issue(db, issue)
    return issue_detail_response(db, issue, issue_effective_status(db, issue))
