"""Switch chunk embeddings to the local multilingual model (384 dimensions).

Existing vectors come from a different model and cannot be converted, so they are cleared; documents
must be re-indexed afterwards. Keyword search keeps working in the meantime.

Revision ID: 0003_local_embeddings
Revises: 0002_user_roles
Create Date: 2026-11-20
"""

from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0003_local_embeddings"
down_revision = "0002_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "document_chunks", "embedding", existing_type=Vector(1536), type_=Vector(384),
        existing_nullable=True, postgresql_using="NULL",
    )


def downgrade() -> None:
    op.alter_column(
        "document_chunks", "embedding", existing_type=Vector(384), type_=Vector(1536),
        existing_nullable=True, postgresql_using="NULL",
    )
