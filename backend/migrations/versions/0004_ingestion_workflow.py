"""Ingestion workflow columns, one regulation per type+number, and search indexes.

Revision ID: 0004_ingestion_workflow
Revises: 0003_local_embeddings
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_ingestion_workflow"
down_revision = "0003_local_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fails if duplicate regulations already exist; merge them before upgrading.
    op.create_unique_constraint("uq_regulations_type_number", "regulations", ["regulation_type", "regulation_number"])
    op.add_column("regulation_versions", sa.Column("storage_key", sa.String(64), nullable=True))

    op.add_column("ingestion_jobs", sa.Column("detail", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("storage_key", sa.String(64), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("metadata", postgresql.JSONB(), nullable=False,
                                              server_default=sa.text("'{}'::jsonb")))
    op.add_column("ingestion_jobs", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                                              server_default=sa.text("now()")))
    op.create_foreign_key("fk_ingestion_jobs_version", "ingestion_jobs", "regulation_versions",
                          ["version_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_ingestion_jobs_requested_by", "ingestion_jobs", "users",
                          ["requested_by"], ["id"], ondelete="SET NULL")

    # Keyword search: same expression as app/modules/retrieval/service.py.
    op.execute("CREATE INDEX ix_document_chunks_fts ON document_chunks "
               "USING gin (to_tsvector('simple'::regconfig, chunk_text))")
    # Vector search by cosine distance.
    op.execute("CREATE INDEX ix_document_chunks_embedding ON document_chunks "
               "USING hnsw (embedding vector_cosine_ops)")
    op.create_index("ix_document_chunks_provision_id", "document_chunks", ["provision_id"])
    op.create_index("ix_legal_provisions_version_id", "legal_provisions", ["version_id"])


def downgrade() -> None:
    op.drop_index("ix_legal_provisions_version_id", "legal_provisions")
    op.drop_index("ix_document_chunks_provision_id", "document_chunks")
    op.execute("DROP INDEX ix_document_chunks_embedding")
    op.execute("DROP INDEX ix_document_chunks_fts")
    op.drop_constraint("fk_ingestion_jobs_requested_by", "ingestion_jobs", type_="foreignkey")
    op.drop_constraint("fk_ingestion_jobs_version", "ingestion_jobs", type_="foreignkey")
    for column in ("updated_at", "metadata", "storage_key", "requested_by", "version_id", "detail"):
        op.drop_column("ingestion_jobs", column)
    op.drop_column("regulation_versions", "storage_key")
    op.drop_constraint("uq_regulations_type_number", "regulations", type_="unique")
