"""add index on jobs applied_at

Revision ID: afeaf2c6ef29
Revises: 69db4a40774f
Create Date: 2025-12-08 10:05:52.054574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afeaf2c6ef29'
down_revision: Union[str, None] = '69db4a40774f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_jobs_applied_at', 'jobs', ['applied_at'])


def downgrade() -> None:
    op.drop_index('ix_jobs_applied_at', table_name='jobs')
