"""Audit log details: what changed (e.g. metadata corrections: old and new values, reason).

Revision ID: 0005_audit_details
Revises: 0004_ingestion_workflow
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_audit_details"
down_revision = "0004_ingestion_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("details", postgresql.JSONB(), nullable=True))
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs")
    op.drop_column("audit_logs", "details")
