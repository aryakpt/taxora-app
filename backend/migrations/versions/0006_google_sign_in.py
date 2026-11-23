"""Sign in with Google: the Google account id and profile picture on users.

Revision ID: 0006_google_sign_in
Revises: 0005_audit_details
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_google_sign_in"
down_revision = "0005_audit_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "google_sub")
