"""add_index_on_match_score

Revision ID: 888d2d4282fa
Revises: 79ff1cda179f
Create Date: 2025-11-25 09:05:23.506292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '888d2d4282fa'
down_revision: Union[str, None] = '79ff1cda179f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index on match_score for better query performance when filtering by score
    op.create_index('ix_jobs_match_score', 'jobs', ['match_score'])


def downgrade() -> None:
    # Remove index on match_score
    op.drop_index('ix_jobs_match_score', table_name='jobs')
