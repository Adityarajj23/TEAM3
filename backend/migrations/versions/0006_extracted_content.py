"""extracted content table for granular page and section storage

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-07 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'extracted_contents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_section', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('source_location', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('extracted_contents')

