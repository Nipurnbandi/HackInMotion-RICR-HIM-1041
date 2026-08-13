from sqlalchemy.orm import Session

from app.core.issue_types import IssueCategory
from app.models import CategoryRoute, Department

FALLBACK_DEPARTMENT_CODE = "GENERAL"

DEFAULT_DEPARTMENTS = [
    ("ROADS", "Roads Department", "roads@city.gov"),
    ("ELECTRICAL", "Electrical & Streetlighting", "electrical@city.gov"),
    ("SANITATION", "Sanitation Department", "sanitation@city.gov"),
    ("WATER", "Water & Drainage", "water@city.gov"),
    ("PUBLIC_WORKS", "Public Works", "works@city.gov"),
    ("GENERAL", "General Administration", "admin@city.gov"),
]

DEFAULT_ROUTES = {
    IssueCategory.POTHOLE: "ROADS",
    IssueCategory.STREETLIGHT: "ELECTRICAL",
    IssueCategory.GARBAGE_OVERFLOW: "SANITATION",
    IssueCategory.ILLEGAL_DUMPING: "SANITATION",
    IssueCategory.WATER_LEAKAGE: "WATER",
    IssueCategory.BROKEN_DRAINAGE: "WATER",
    IssueCategory.DAMAGED_PUBLIC_PROPERTY: "PUBLIC_WORKS",
}


def resolve_department(db: Session, category: IssueCategory) -> Department | None:
    route = (
        db.query(CategoryRoute).filter(CategoryRoute.category == category).first()
    )
    if route is not None:
        return db.get(Department, route.department_id)
    return (
        db.query(Department)
        .filter(Department.code == FALLBACK_DEPARTMENT_CODE)
        .first()
    )


def seed_departments(db: Session) -> None:
    for code, name, email in DEFAULT_DEPARTMENTS:
        exists = db.query(Department).filter(Department.code == code).first()
        if exists is None:
            db.add(Department(code=code, name=name, email=email))
    db.commit()

    for category, code in DEFAULT_ROUTES.items():
        exists = (
            db.query(CategoryRoute).filter(CategoryRoute.category == category).first()
        )
        if exists is None:
            department = db.query(Department).filter(Department.code == code).first()
            db.add(CategoryRoute(category=category, department_id=department.id))
    db.commit()
