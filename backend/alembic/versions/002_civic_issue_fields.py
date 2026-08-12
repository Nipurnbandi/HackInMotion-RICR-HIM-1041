"""Extend issues with civic reporting fields

Adds tracking_id, category, geolocation, photo reference and a real status
enum to the existing issues table, and renames reporter_id -> citizen_id.
Existing rows are preserved and backfilled.

Revision ID: 002_civic_issue
Revises: 001_initial
Create Date: 2026-08-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_civic_issue"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORY_ENUM = sa.Enum(
    "STREETLIGHT",
    "POTHOLE",
    "GARBAGE_OVERFLOW",
    "WATER_LEAKAGE",
    "DAMAGED_PUBLIC_PROPERTY",
    "ILLEGAL_DUMPING",
    "BROKEN_DRAINAGE",
    name="issue_category",
    native_enum=False,
)

STATUS_ENUM = sa.Enum(
    "SUBMITTED",
    "UNDER_REVIEW",
    "IN_PROGRESS",
    "RESOLVED",
    "REJECTED",
    name="issue_status",
    native_enum=False,
)


def upgrade() -> None:
    op.alter_column("issues", "reporter_id", new_column_name="citizen_id")
    op.create_index(op.f("ix_issues_citizen_id"), "issues", ["citizen_id"])

    op.add_column("issues", sa.Column("tracking_id", sa.String(length=32), nullable=True))
    op.create_index(
        op.f("ix_issues_tracking_id"), "issues", ["tracking_id"], unique=True
    )

    op.add_column(
        "issues",
        sa.Column(
            "category",
            CATEGORY_ENUM,
            server_default="POTHOLE",
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_issues_category"), "issues", ["category"])

    op.add_column("issues", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("issues", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("issues", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("issues", sa.Column("photo_url", sa.String(length=500), nullable=True))

    # Replace the free-text status column with the workflow enum, mapping any
    # pre-existing rows onto the new vocabulary.
    op.execute("UPDATE issues SET status = 'SUBMITTED' WHERE status = 'open'")
    op.execute("UPDATE issues SET status = 'RESOLVED' WHERE status = 'closed'")
    op.execute(
        "UPDATE issues SET status = 'SUBMITTED' "
        "WHERE status NOT IN "
        "('SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'RESOLVED', 'REJECTED')"
    )
    op.alter_column(
        "issues",
        "status",
        existing_type=sa.String(length=50),
        type_=STATUS_ENUM,
        server_default="SUBMITTED",
        existing_nullable=False,
        postgresql_using="status::varchar(50)",
    )
    op.create_index(op.f("ix_issues_status"), "issues", ["status"])

    # Backfill tracking IDs for any report created before this migration.
    op.execute(
        "UPDATE issues "
        "SET tracking_id = 'SMC-' "
        "|| EXTRACT(YEAR FROM created_at)::int::text "
        "|| '-' || LPAD(id::text, 6, '0') "
        "WHERE tracking_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_issues_status"), table_name="issues")
    op.execute("UPDATE issues SET status = 'closed' WHERE status IN ('RESOLVED', 'REJECTED')")
    op.execute("UPDATE issues SET status = 'open' WHERE status NOT IN ('closed')")
    op.alter_column(
        "issues",
        "status",
        existing_type=STATUS_ENUM,
        type_=sa.String(length=50),
        server_default="open",
        existing_nullable=False,
    )

    op.drop_column("issues", "photo_url")
    op.drop_column("issues", "address")
    op.drop_column("issues", "longitude")
    op.drop_column("issues", "latitude")

    op.drop_index(op.f("ix_issues_category"), table_name="issues")
    op.drop_column("issues", "category")

    op.drop_index(op.f("ix_issues_tracking_id"), table_name="issues")
    op.drop_column("issues", "tracking_id")

    op.drop_index(op.f("ix_issues_citizen_id"), table_name="issues")
    op.alter_column("issues", "citizen_id", new_column_name="reporter_id")
