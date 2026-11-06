"""security and provenance: isolation_level, requirement origin and provenance, defect evidence_type

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06 08:25:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('isolation_level', sa.String(length=30), server_default='none', nullable=False))

    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('origin', sa.String(length=30), server_default='manual', nullable=False))
        batch_op.add_column(sa.Column('source_commit_sha', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))

    with op.batch_alter_table('clauses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_paths', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('line_start', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('line_end', sa.Integer(), nullable=True))

    with op.batch_alter_table('defects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('evidence_type', sa.String(length=30), server_default='manual', nullable=False))
        batch_op.add_column(sa.Column('source_commit_sha', sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('defects', schema=None) as batch_op:
        batch_op.drop_column('source_commit_sha')
        batch_op.drop_column('evidence_type')

    with op.batch_alter_table('clauses', schema=None) as batch_op:
        batch_op.drop_column('line_end')
        batch_op.drop_column('line_start')
        batch_op.drop_column('source_paths')

    with op.batch_alter_table('requirements', schema=None) as batch_op:
        batch_op.drop_column('confidence')
        batch_op.drop_column('source_commit_sha')
        batch_op.drop_column('origin')

    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.drop_column('isolation_level')

