"""Sessions can be ended on the server (users.session_version), and rate limits are counted in the database so
every API instance shares them.

Revision ID: 0010_sessions_rate_limits
Revises: 0009_conversation_groups
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_sessions_rate_limits"
down_revision = "0009_conversation_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("session_version", sa.Integer(), server_default="0", nullable=False))
    op.create_table(
        "rate_limit_hits",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rate_limit_hits_key_at", "rate_limit_hits", ["key", "at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_hits_key_at", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
    op.drop_column("users", "session_version")
