"""Restrict users.role to known roles and add the reviewer role.

Revision ID: 0002_user_roles
Revises: 0001_initial_schema
Create Date: 2026-11-19
"""

from alembic import op

revision = "0002_user_roles"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'reviewer', 'admin')")


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
