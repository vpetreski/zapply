"""Add check constraint and composite index for interviews

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-04 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add check constraint to enforce valid status values at database level
    op.create_check_constraint(
        'ck_interview_status',
        'interviews',
        "status IN ('active', 'closed')"
    )
    # Add composite index for common query pattern (filter by status, order by updated_at)
    op.create_index(
        'ix_interviews_status_updated',
        'interviews',
        ['status', 'updated_at'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_interviews_status_updated', table_name='interviews')
    op.drop_constraint('ck_interview_status', 'interviews', type_='check')
