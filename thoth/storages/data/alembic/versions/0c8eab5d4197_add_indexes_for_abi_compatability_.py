"""Add indexes for abi_compatability queries

Revision ID: 0c8eab5d4197
Revises: bb26306538f0
Create Date: 2020-02-05 10:54:52.119190+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0c8eab5d4197'
down_revision = 'bb26306538f0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('build_log_analyzer_run',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('build_log_analyzer_name', sa.Text(), nullable=True),
    sa.Column('build_log_analyzer_version', sa.Text(), nullable=True),
    sa.Column('build_log_analysis_document_id', sa.Text(), nullable=False),
    sa.Column('datetime', sa.DateTime(), nullable=False),
    sa.Column('debug', sa.Boolean(), nullable=False),
    sa.Column('build_log_analyzer_error_reason', sa.Text(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('input_python_package_version_entity_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['input_python_package_version_entity_id'], ['python_package_version_entity.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('python_package_version_entity_id_idx', 'python_package_version_entity', ['id'], unique=True)
    op.create_index('requires_symbol_python_artifact_id_idx', 'requires_symbol', ['python_artifact_id'], unique=False)
    op.create_index('versioned_symbol_id_idx', 'versioned_symbol', ['id'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('versioned_symbol_id_idx', table_name='versioned_symbol')
    op.drop_index('requires_symbol_python_artifact_id_idx', table_name='requires_symbol')
    op.drop_index('python_package_version_entity_id_idx', table_name='python_package_version_entity')
    op.drop_table('build_log_analyzer_run')
    # ### end Alembic commands ###
