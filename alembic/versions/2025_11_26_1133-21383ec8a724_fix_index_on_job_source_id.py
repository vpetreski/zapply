"""fix_index_on_job_source_id

Revision ID: 21383ec8a724
Revises: 2cc51ef424ea
Create Date: 2025-11-26 11:33:25.694763

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21383ec8a724'
down_revision: Union[str, None] = '2cc51ef424ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old single-column index on source_id
    op.drop_index('ix_jobs_source_id', table_name='jobs')

    # Create new composite index on (source, source_id)
    # This optimizes the deduplication query: SELECT source_id FROM jobs WHERE source = 'working_nomads'
    # The composite index allows efficient filtering by source first, then retrieving source_id values
    op.create_index('ix_jobs_source_source_id', 'jobs', ['source', 'source_id'], unique=False)


def downgrade() -> None:
    # Revert back to single-column index
    op.drop_index('ix_jobs_source_source_id', table_name='jobs')
    op.create_index('ix_jobs_source_id', 'jobs', ['source_id'], unique=False)
