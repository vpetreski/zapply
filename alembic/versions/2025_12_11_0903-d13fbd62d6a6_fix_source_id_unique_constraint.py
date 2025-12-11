"""fix_source_id_unique_constraint

Revision ID: d13fbd62d6a6
Revises: ee39e6cc9d5a
Create Date: 2025-12-11 09:03:01.585751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd13fbd62d6a6'
down_revision: Union[str, None] = 'ee39e6cc9d5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix jobs table: change source_id from unique to composite unique (source, source_id)
    # This is CRITICAL for multi-source architecture - different sources may use same IDs
    op.drop_index('ix_jobs_source_id', table_name='jobs')
    op.create_index('ix_jobs_source_id', 'jobs', ['source_id'], unique=False)
    op.create_unique_constraint('uq_jobs_source_source_id', 'jobs', ['source', 'source_id'])

    # Fix source_runs table: add missing FK and unique constraint
    op.create_unique_constraint('uq_source_runs_run_source', 'source_runs', ['run_id', 'source_name'])
    op.create_foreign_key('fk_source_runs_run_id_runs', 'source_runs', 'runs', ['run_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Reverse source_runs changes
    op.drop_constraint('fk_source_runs_run_id_runs', 'source_runs', type_='foreignkey')
    op.drop_constraint('uq_source_runs_run_source', 'source_runs', type_='unique')

    # Reverse jobs changes
    op.drop_constraint('uq_jobs_source_source_id', 'jobs', type_='unique')
    op.drop_index('ix_jobs_source_id', table_name='jobs')
    op.create_index('ix_jobs_source_id', 'jobs', ['source_id'], unique=True)
