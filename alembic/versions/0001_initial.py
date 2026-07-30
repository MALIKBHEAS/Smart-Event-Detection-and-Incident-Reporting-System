"""Alembic initial revision (condensed). Use alembic --autogenerate for full details."""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('roles',
        sa.Column('role_id', sa.Integer(), primary_key=True),
        sa.Column('role_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.UniqueConstraint('role_name')
    )
    op.create_table('users',
        sa.Column('user_id', sa.Integer(), primary_key=True),
        sa.Column('full_name', sa.String(length=200)),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('phone', sa.String(length=40)),
        sa.Column('password_hash', sa.String(length=512), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('email')
    )
    op.create_table('user_roles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id'), primary_key=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.role_id'), primary_key=True),
    )
    # NOTE: For brevity many tables omitted here. Run alembic --autogenerate in your environment to produce full migration.


def downgrade():
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
