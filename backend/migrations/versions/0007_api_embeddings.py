"""Switch chunk embeddings to the API model (Gemini, 768 dimensions).

Vectors from the old local model (384 dimensions) cannot be converted, so they are cleared; run
`make reindex` afterwards. Keyword search keeps working in the meantime.

Revision ID: 0007_api_embeddings
Revises: 0006_google_sign_in
"""

from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0007_api_embeddings"
down_revision = "0006_google_sign_in"
branch_labels = None
depends_on = None


def _resize(old: int, new: int) -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    op.alter_column("document_chunks", "embedding", existing_type=Vector(old), type_=Vector(new),
                    existing_nullable=True, postgresql_using="NULL")
    op.execute("CREATE INDEX ix_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops)")


def upgrade() -> None:
    _resize(384, 768)


def downgrade() -> None:
    _resize(768, 384)
