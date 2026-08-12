from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, func, true
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

    # Derived from the category so admin-facing listings keep a short label.
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

    # Storage-agnostic reference (relative path/URL) produced by app.core.storage.
    photo_url: Mapped[str | None] = mapped_column(String(500), default=None)

    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status", native_enum=False),
        default=IssueStatus.SUBMITTED,
        server_default=IssueStatus.SUBMITTED.value,
        index=True,
    )

    # Case grouping: every report of the same real-world problem carries the
    # same case_id. The first report of a case is its primary — city-facing
    # lists show primaries only, and joined reports read their display status
    # from the primary (status belongs to the case, not the report).
    case_id: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    is_primary: Mapped[bool] = mapped_column(default=True, server_default=true())

    reporter: Mapped[User] = relationship(back_populates="issues")

    __table_args__ = (
        # Serves the duplicate lookup: narrow by category, then walk a small
        # latitude/longitude slice.
        Index("ix_issues_dup_lookup", "category", "latitude", "longitude"),
    )
