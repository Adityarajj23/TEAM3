"""project creation and intake models and columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-07 12:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create project_contexts table
    op.create_table(
        'project_contexts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), index=True, unique=True, nullable=False),
        sa.Column('product_overview', sa.Text(), nullable=False, server_default=''),
        sa.Column('problem_statement', sa.Text(), nullable=False, server_default=''),
        sa.Column('target_users', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('product_modules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('architecture_context', sa.Text(), nullable=False, server_default=''),
        sa.Column('technical_stack', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('external_integrations', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('business_rules', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('security_expectations', sa.Text(), nullable=False, server_default=''),
        sa.Column('privacy_requirements', sa.Text(), nullable=False, server_default=''),
        sa.Column('performance_expectations', sa.Text(), nullable=False, server_default=''),
        sa.Column('availability_expectations', sa.Text(), nullable=False, server_default=''),
        sa.Column('regulatory_standards', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('assumptions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('exclusions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('dependencies', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('additional_context', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 2. Create project_roles table
    op.create_table(
        'project_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('permissions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('responsibilities', sa.Text(), nullable=False, server_default=''),
        sa.Column('restrictions', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 3. Create business_scenarios table
    op.create_table(
        'business_scenarios',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('actor', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('preconditions', sa.Text(), nullable=False, server_default=''),
        sa.Column('expected_outcome', sa.Text(), nullable=False, server_default=''),
        sa.Column('business_rules', sa.Text(), nullable=False, server_default=''),
        sa.Column('module', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 4. Create document_processing_jobs table
    op.create_table(
        'document_processing_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), index=True, nullable=True),
        sa.Column('job_status', sa.String(length=30), nullable=False, server_default='queued'),
        sa.Column('processing_stage', sa.String(length=50), nullable=False, server_default='validation'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extracted_content_reference', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 5. Alter projects table
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('business_goal', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('owner_name', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('team', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('version', sa.String(length=30), nullable=False, server_default='1.0.0'))
        batch_op.add_column(sa.Column('environment_name', sa.String(length=100), nullable=False, server_default=''))

    # 6. Alter documents table
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.alter_column('project_id', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('display_name', sa.String(length=255), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('document_type', sa.String(length=50), nullable=False, server_default='prd'))
        batch_op.add_column(sa.Column('version', sa.String(length=30), nullable=False, server_default='1.0'))
        batch_op.add_column(sa.Column('owner', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('document_date', sa.String(length=50), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('related_module', sa.String(length=100), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'))
        batch_op.add_column(sa.Column('processing_instructions', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('checksum', sa.String(length=64), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('upload_status', sa.String(length=30), nullable=False, server_default='uploaded'))
        batch_op.add_column(sa.Column('extraction_status', sa.String(length=30), nullable=False, server_default='uploaded'))


def downgrade() -> None:
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_column('extraction_status')
        batch_op.drop_column('upload_status')
        batch_op.drop_column('checksum')
        batch_op.drop_column('processing_instructions')
        batch_op.drop_column('priority')
        batch_op.drop_column('related_module')
        batch_op.drop_column('document_date')
        batch_op.drop_column('owner')
        batch_op.drop_column('version')
        batch_op.drop_column('document_type')
        batch_op.drop_column('display_name')

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('environment_name')
        batch_op.drop_column('version')
        batch_op.drop_column('team')
        batch_op.drop_column('owner_name')
        batch_op.drop_column('business_goal')

    op.drop_table('document_processing_jobs')
    op.drop_table('business_scenarios')
    op.drop_table('project_roles')
    op.drop_table('project_contexts')
