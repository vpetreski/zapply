"""add_index_on_job_source_id

Revision ID: 2cc51ef424ea
Revises: 04726265c457
Create Date: 2025-11-26 11:22:55.393835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cc51ef424ea'
down_revision: Union[str, None] = '04726265c457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index on source_id column for faster lookups when checking for existing jobs
    # This optimizes the deduplication query: SELECT source_id FROM jobs WHERE source = 'working_nomads'
    op.create_index('ix_jobs_source_id', 'jobs', ['source_id'], unique=False)


def downgrade() -> None:
    # Remove index on source_id column
    op.drop_index('ix_jobs_source_id', table_name='jobs')
