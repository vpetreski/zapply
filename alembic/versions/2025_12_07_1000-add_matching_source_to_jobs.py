"""add_matching_source_to_jobs

Revision ID: f1a2b3c4d5e6
Revises: e0b90f8775b5
Create Date: 2025-12-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e0b90f8775b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add matching_source column with default 'auto' for all existing jobs
    op.add_column('jobs', sa.Column('matching_source', sa.String(length=20), nullable=False, server_default='auto'))


def downgrade() -> None:
    op.drop_column('jobs', 'matching_source')
