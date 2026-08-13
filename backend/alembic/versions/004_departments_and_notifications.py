"""Departments, category routing and notifications

Revision ID: 004_departments
Revises: 003_case_grouping
Create Date: 2026-08-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_departments"
down_revision: Union[str, None] = "003_case_grouping"
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

DEPARTMENTS = [
    ("ROADS", "Roads Department", "roads@city.gov"),
    ("ELECTRICAL", "Electrical & Streetlighting", "electrical@city.gov"),
    ("SANITATION", "Sanitation Department", "sanitation@city.gov"),
    ("WATER", "Water & Drainage", "water@city.gov"),
    ("PUBLIC_WORKS", "Public Works", "works@city.gov"),
    ("GENERAL", "General Administration", "admin@city.gov"),
]

ROUTES = [
    ("POTHOLE", "ROADS"),
    ("STREETLIGHT", "ELECTRICAL"),
    ("GARBAGE_OVERFLOW", "SANITATION"),
    ("ILLEGAL_DUMPING", "SANITATION"),
    ("WATER_LEAKAGE", "WATER"),
    ("BROKEN_DRAINAGE", "WATER"),
    ("DAMAGED_PUBLIC_PROPERTY", "PUBLIC_WORKS"),
]


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_departments_code"), "departments", ["code"], unique=True)

    op.create_table(
        "category_routes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", CATEGORY_ENUM, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_department_id"), "notifications", ["department_id"]
    )

    op.add_column("issues", sa.Column("department_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_issues_department_id"), "issues", ["department_id"])
    op.create_foreign_key(
        "fk_issues_department_id", "issues", "departments", ["department_id"], ["id"]
    )

    for code, name, email in DEPARTMENTS:
        op.execute(
            f"INSERT INTO departments (code, name, email) "
            f"VALUES ('{code}', '{name.replace(chr(39), chr(39) * 2)}', '{email}')"
        )

    for category, code in ROUTES:
        op.execute(
            f"INSERT INTO category_routes (category, department_id) "
            f"SELECT '{category}', id FROM departments WHERE code = '{code}'"
        )

    op.execute(
        "UPDATE issues SET department_id = "
        "(SELECT cr.department_id FROM category_routes cr WHERE cr.category = issues.category) "
        "WHERE department_id IS NULL"
    )
    op.execute(
        "UPDATE issues SET department_id = "
        "(SELECT id FROM departments WHERE code = 'GENERAL') "
        "WHERE department_id IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_issues_department_id", "issues", type_="foreignkey")
    op.drop_index(op.f("ix_issues_department_id"), table_name="issues")
    op.drop_column("issues", "department_id")
    op.drop_index(op.f("ix_notifications_department_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("category_routes")
    op.drop_index(op.f("ix_departments_code"), table_name="departments")
    op.drop_table("departments")
