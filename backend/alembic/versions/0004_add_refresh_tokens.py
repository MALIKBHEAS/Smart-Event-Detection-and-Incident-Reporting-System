"""Add refresh_tokens table and seed default roles

Revision ID: 0004_add_refresh_tokens
Revises: 0003_cameras_management
Create Date: 2026-08-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_refresh_tokens"
down_revision = "0003_cameras_management"
branch_labels = None
depends_on = None


ROLE_NAMES = ["Admin", "Security Operator", "Viewer"]


ROLE_DESCRIPTIONS = {
    "Admin": "Full access: manage cameras, users, and system configuration.",
    "Security Operator": "Operate cameras and workers, view analytics and incidents.",
    "Viewer": "Read-only access to dashboards, analytics, and cameras.",
}


def upgrade():
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # Seed the three roles the app expects (Admin / Security Operator /
    # Viewer). This only ever runs once per fresh database.
    roles_table = sa.table("roles", sa.column("name", sa.String), sa.column("description", sa.String))
    op.bulk_insert(
        roles_table,
        [{"name": name, "description": ROLE_DESCRIPTIONS[name]} for name in ROLE_NAMES],
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM roles WHERE name IN ('Admin', 'Security Operator', 'Viewer')"))

    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
