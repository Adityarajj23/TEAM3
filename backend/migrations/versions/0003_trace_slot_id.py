"""add slot_id to provider_traces

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('provider_traces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slot_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('provider_traces', schema=None) as batch_op:
        batch_op.drop_column('slot_id')

