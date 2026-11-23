"""The official source link becomes optional (uploaded documents may not have one).

Revision ID: 0008_optional_source_url
Revises: 0007_api_embeddings
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_optional_source_url"
down_revision = "0007_api_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("regulation_versions", "source_url", existing_type=sa.Text(), nullable=True)
    op.alter_column("ingestion_jobs", "source_url", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE regulation_versions SET source_url = '' WHERE source_url IS NULL")
    op.execute("UPDATE ingestion_jobs SET source_url = '' WHERE source_url IS NULL")
    op.alter_column("regulation_versions", "source_url", existing_type=sa.Text(), nullable=False)
    op.alter_column("ingestion_jobs", "source_url", existing_type=sa.Text(), nullable=False)
