from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.roles import Role
from app.models import Department, Notification, User
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminCaseResponse,
    AdminDashboardResponse,
    AdminIssueResponse,
    DepartmentResponse,
    IssueUpdate,
    NotificationListResponse,
    NotificationResponse,
)
from app.schemas.citizen import MapIssueResponse
from app.services.admin import (
    delete_issue,
    get_admin_analytics,
    get_admin_dashboard,
    list_admin_cases,
    list_departments,
    save_resolution_proof,
    update_issue,
)
from app.services.city_map import list_map_issues
from app.services.citizen import sniff_image_type, validate_photo
from app.services.escalation import run_sla_escalations
from app.services.photo_verification import verify_resolution_photo
from app.services.notification import list_notifications, mark_notification_read

router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles(Role.ADMIN)


def case_response(case: dict) -> AdminCaseResponse:
    return AdminCaseResponse.model_validate(
        {
            **AdminIssueResponse.model_validate(case["issue"]).model_dump(),
            "citizen_count": case["citizen_count"],
            "vote_count": case["vote_count"],
            "days_open": case["days_open"],
            "priority_score": case["priority_score"],
            "escalated": case["escalated"],
            "sla_days": case["sla_days"],
            "department_code": case["department_code"],
            "department_name": case["department_name"],
        }
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    run_sla_escalations(db)
    return get_admin_dashboard(db, current_user)


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def admin_analytics(
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    run_sla_escalations(db)
    return get_admin_analytics(db)


@router.get("/map", response_model=list[MapIssueResponse])
def admin_map_issues(
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return list_map_issues(db)


@router.get("/departments", response_model=list[DepartmentResponse])
def admin_list_departments(
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return list_departments(db)


@router.get("/issues", response_model=list[AdminCaseResponse])
def admin_list_issues(
    department: Annotated[str | None, Query(max_length=50)] = None,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    run_sla_escalations(db)
    return [
        case_response(case)
        for case in list_admin_cases(db, department_code=department)
    ]


def notification_response(
    notification: Notification, department: Department
) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        message=notification.message,
        is_read=notification.is_read,
        sent_at=notification.sent_at,
        created_at=notification.created_at,
        department_name=department.name,
        department_email=department.email,
    )


@router.get("/notifications", response_model=NotificationListResponse)
def admin_notifications(
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    rows, unread = list_notifications(db)
    return NotificationListResponse(
        items=[
            notification_response(notification, department)
            for notification, department in rows
        ],
        unread=unread,
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def admin_mark_notification_read(
    notification_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    notification = mark_notification_read(db, notification_id)
    department = db.get(Department, notification.department_id)
    return notification_response(notification, department)


@router.put("/issues/{issue_id}", response_model=AdminIssueResponse)
def admin_update_issue(
    issue_id: int,
    data: IssueUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return update_issue(db, issue_id, data)


@router.post("/issues/{issue_id}/resolution-photo", response_model=AdminIssueResponse)
async def admin_upload_resolution_photo(
    issue_id: int,
    background_tasks: BackgroundTasks,
    photo: Annotated[UploadFile, File()],
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    content = await photo.read(settings.max_upload_size_bytes + 1)
    extension = validate_photo(
        content=content,
        max_bytes=settings.max_upload_size_bytes,
        declared_content_type=photo.content_type,
    )
    issue = save_resolution_proof(db, issue_id, content=content, extension=extension)
    media_type = sniff_image_type(content) or "image/jpeg"
    background_tasks.add_task(verify_resolution_photo, issue.id, content, media_type)
    return issue


@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_issue(
    issue_id: int,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    delete_issue(db, issue_id)
