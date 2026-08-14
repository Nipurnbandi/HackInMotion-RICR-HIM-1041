from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.issue_types import IssueCategory, IssueStatus
from app.core.roles import Role


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", native_enum=False),
        default=Role.CITIZEN,
        server_default=Role.CITIZEN.value,
    )

    issues: Mapped[list["Issue"]] = relationship(
        back_populates="reporter", cascade="all, delete-orphan"
    )


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tracking_id: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, default=None
    )
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[IssueCategory] = mapped_column(
        Enum(IssueCategory, name="issue_category", native_enum=False),
        default=IssueCategory.POTHOLE,
        server_default=IssueCategory.POTHOLE.value,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, default="", server_default="")

    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    address: Mapped[str | None] = mapped_column(String(500), default=None)

    photo_url: Mapped[str | None] = mapped_column(String(500), default=None)

    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status", native_enum=False),
        default=IssueStatus.SUBMITTED,
        server_default=IssueStatus.SUBMITTED.value,
        index=True,
    )

    resolution_note: Mapped[str] = mapped_column(Text, default="", server_default="")
    resolution_photo_url: Mapped[str | None] = mapped_column(
        String(500), default=None
    )
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    case_id: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    is_primary: Mapped[bool] = mapped_column(default=True, server_default=true())

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), index=True, default=None
    )

    reporter: Mapped[User] = relationship(back_populates="issues")
    department: Mapped["Department"] = relationship()

    __table_args__ = (
        Index("ix_issues_dup_lookup", "category", "latitude", "longitude"),
    )


class IssueVote(Base, TimestampMixin):
    __tablename__ = "issue_votes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True
    )
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    __table_args__ = (
        UniqueConstraint("issue_id", "citizen_id", name="uq_issue_votes_issue_citizen"),
    )


class StatusHistory(Base, TimestampMixin):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), index=True
    )
    old_status: Mapped[IssueStatus | None] = mapped_column(
        Enum(IssueStatus, name="issue_status", native_enum=False), default=None
    )
    new_status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status", native_enum=False)
    )
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    photo_url: Mapped[str | None] = mapped_column(String(500), default=None)
    changed_by_role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", native_enum=False), default=Role.CITIZEN
    )


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))


class CategoryRoute(Base, TimestampMixin):
    __tablename__ = "category_routes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[IssueCategory] = mapped_column(
        Enum(IssueCategory, name="issue_category", native_enum=False), unique=True
    )
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False, server_default="false")
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
