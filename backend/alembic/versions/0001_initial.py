"""Initial schema migration

Revision ID: 0001_initial
Revises: 
Create Date: 2026-07-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )

    # Association table user_roles
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    )

    # Create cameras table
    op.create_table(
        'cameras',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False, unique=True),
        sa.Column('rtsp_url', sa.String(length=1024), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('camera_id', sa.Integer(), sa.ForeignKey('cameras.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String(length=128), nullable=False, index=True),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default='low'),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('payload', sa.JSON(), nullable=True),
    )
    # NOTE: 'type' column above is declared with index=True, which already
    # creates ix_events_type -- an explicit op.create_index('ix_events_type', ...)
    # here was a duplicate that broke `alembic upgrade head` against any
    # fresh (empty) database. Only the timestamp index needs to be explicit.
    op.create_index('ix_events_timestamp', 'events', ['timestamp'])

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.String(length=2048), nullable=False),
        sa.Column('events', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_reports_created_at', 'reports', ['created_at'])


def downgrade():
    op.drop_index('ix_reports_created_at', table_name='reports')
    op.drop_table('reports')

    op.drop_index('ix_events_timestamp', table_name='events')
    op.drop_index('ix_events_type', table_name='events')
    op.drop_table('events')

    op.drop_table('cameras')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
