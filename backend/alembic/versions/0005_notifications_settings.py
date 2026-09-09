"""Add notifications and app_settings tables

Revision ID: 0005_notifications_settings
Revises: 0004_add_refresh_tokens
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_notifications_settings"
down_revision = "0004_add_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="low"),
        sa.Column("related_type", sa.String(length=32), nullable=True),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_read", "notifications", ["read"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detection_confidence_threshold", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence_retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("notify_on_new_event", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_on_new_incident", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    settings_table = sa.table(
        "app_settings",
        sa.column("id", sa.Integer),
        sa.column("detection_confidence_threshold", sa.Float),
        sa.column("evidence_retention_days", sa.Integer),
        sa.column("notify_on_new_event", sa.Boolean),
        sa.column("notify_on_new_incident", sa.Boolean),
    )
    op.bulk_insert(
        settings_table,
        [{"id": 1, "detection_confidence_threshold": 0.5, "evidence_retention_days": 30, "notify_on_new_event": True, "notify_on_new_incident": True}],
    )


def downgrade():
    op.drop_table("app_settings")
    op.drop_index("ix_notifications_read", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_table("notifications")
