"""Users can put conversations in their own groups.

Revision ID: 0009_conversation_groups
Revises: 0008_optional_source_url
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009_conversation_groups"
down_revision = "0008_optional_source_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_conversation_groups_user_name"),
    )
    op.create_index("ix_conversation_groups_user_id", "conversation_groups", ["user_id"])
    op.add_column("conversations", sa.Column(
        "group_id", UUID(as_uuid=True), sa.ForeignKey("conversation_groups.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_conversations_group_id", "conversations", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_group_id", table_name="conversations")
    op.drop_column("conversations", "group_id")
    op.drop_index("ix_conversation_groups_user_id", table_name="conversation_groups")
    op.drop_table("conversation_groups")
