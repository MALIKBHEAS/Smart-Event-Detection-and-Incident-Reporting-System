"""Update cameras table for full camera management

Revision ID: 0003_cameras_management
Revises: 0002_reports_event_fk
Create Date: 2026-08-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_cameras_management"
down_revision = "0002_reports_event_fk"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("cameras") as batch:
        batch.add_column(
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )
        batch.add_column(sa.Column("detector_config", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("tracker_config", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            )
        )

    op.execute("UPDATE cameras SET enabled = is_active")
    op.execute("UPDATE cameras SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE cameras SET updated_at = now() WHERE updated_at IS NULL")

    with op.batch_alter_table("cameras") as batch:
        batch.drop_column("is_active")


def downgrade():
    with op.batch_alter_table("cameras") as batch:
        batch.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )

    op.execute("UPDATE cameras SET is_active = enabled")

    with op.batch_alter_table("cameras") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("tracker_config")
        batch.drop_column("detector_config")
        batch.drop_column("enabled")

