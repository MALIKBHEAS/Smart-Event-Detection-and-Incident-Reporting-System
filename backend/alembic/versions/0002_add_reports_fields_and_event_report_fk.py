"""Add report fields and link events to reports

Revision ID: 0002_reports_event_fk
Revises: 0001_initial
Create Date: 2026-08-01 05:24:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_reports_event_fk'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to reports table
    op.add_column('reports', sa.Column('details', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('incident_type', sa.String(length=128), nullable=True))
    op.add_column('reports', sa.Column('severity', sa.String(length=32), nullable=False, server_default='low'))
    op.add_column('reports', sa.Column('status', sa.String(length=32), nullable=False, server_default='open'))
    op.add_column('reports', sa.Column('reporter_id', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('assigned_to_id', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('camera_id', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('reports', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('reports', sa.Column('attachments', sa.JSON(), nullable=True))
    op.add_column('reports', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('reports', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    # Indexes for report columns
    op.create_index('ix_reports_incident_type', 'reports', ['incident_type'])
    op.create_index('ix_reports_severity', 'reports', ['severity'])
    op.create_index('ix_reports_status', 'reports', ['status'])
    op.create_index('ix_reports_created_status', 'reports', ['created_at', 'status'])

    # Foreign keys for report references
    op.create_foreign_key('fk_reports_reporter_id_users', 'reports', 'users', ['reporter_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_reports_assigned_to_id_users', 'reports', 'users', ['assigned_to_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_reports_camera_id_cameras', 'reports', 'cameras', ['camera_id'], ['id'], ondelete='SET NULL')

    # Add report_id to events and FK -> reports
    op.add_column('events', sa.Column('report_id', sa.Integer(), nullable=True))
    op.create_index('ix_events_report_id', 'events', ['report_id'])
    op.create_foreign_key('fk_events_report_id_reports', 'events', 'reports', ['report_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Drop FK and column from events
    op.drop_constraint('fk_events_report_id_reports', 'events', type_='foreignkey')
    op.drop_index('ix_events_report_id', table_name='events')
    op.drop_column('events', 'report_id')

    # Drop report foreign keys
    op.drop_constraint('fk_reports_camera_id_cameras', 'reports', type_='foreignkey')
    op.drop_constraint('fk_reports_assigned_to_id_users', 'reports', type_='foreignkey')
    op.drop_constraint('fk_reports_reporter_id_users', 'reports', type_='foreignkey')

    # Drop report indexes
    op.drop_index('ix_reports_created_status', table_name='reports')
    op.drop_index('ix_reports_status', table_name='reports')
    op.drop_index('ix_reports_severity', table_name='reports')
    op.drop_index('ix_reports_incident_type', table_name='reports')

    # Drop added report columns
    op.drop_column('reports', 'updated_at')
    op.drop_column('reports', 'tags')
    op.drop_column('reports', 'attachments')
    op.drop_column('reports', 'resolved_at')
    op.drop_column('reports', 'occurred_at')
    op.drop_column('reports', 'camera_id')
    op.drop_column('reports', 'assigned_to_id')
    op.drop_column('reports', 'reporter_id')
    op.drop_column('reports', 'status')
    op.drop_column('reports', 'severity')
    op.drop_column('reports', 'incident_type')
    op.drop_column('reports', 'details')
