from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.roles import Role
from app.models import User
from app.schemas.issue import (
    AdminAnalyticsResponse,
    AdminCaseResponse,
    AdminDashboardResponse,
    AdminIssueResponse,
    IssueUpdate,
)
from app.services.auth import (
    delete_issue,
    get_admin_analytics,
    get_admin_dashboard,
    update_issue,
)
from app.services.issue import list_admin_cases

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_roles(Role.ADMIN)


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    current_user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    return get_admin_dashboard(db, current_user)


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def admin_analytics(
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    return get_admin_analytics(db)


@router.get("/issues", response_model=list[AdminCaseResponse])
def admin_list_issues(
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    """One row per case, highest priority first."""
    return [
        AdminCaseResponse.model_validate(
            {
                **AdminIssueResponse.model_validate(case["issue"]).model_dump(),
                "citizen_count": case["citizen_count"],
                "days_open": case["days_open"],
                "priority_score": case["priority_score"],
            }
        )
        for case in list_admin_cases(db)
    ]


@router.put("/issues/{issue_id}", response_model=AdminIssueResponse)
def admin_update_issue(
    issue_id: int,
    data: IssueUpdate,
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    return update_issue(db, issue_id, data)


@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_issue(
    issue_id: int,
    _: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    delete_issue(db, issue_id)
