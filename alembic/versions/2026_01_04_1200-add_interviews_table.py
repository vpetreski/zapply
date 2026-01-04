"""Add interviews table for tracking interview processes

Revision ID: a1b2c3d4e5f6
Revises: 804eb0e6e303
Create Date: 2026-01-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '804eb0e6e303'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('interviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('cv_data', sa.LargeBinary(), nullable=True),
        sa.Column('cv_filename', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_interviews'))
    )
    op.create_index(op.f('ix_interviews_status'), 'interviews', ['status'], unique=False)
    op.create_index(op.f('ix_interviews_created_at'), 'interviews', ['created_at'], unique=False)
    op.create_index(op.f('ix_interviews_updated_at'), 'interviews', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_interviews_updated_at'), table_name='interviews')
    op.drop_index(op.f('ix_interviews_created_at'), table_name='interviews')
    op.drop_index(op.f('ix_interviews_status'), table_name='interviews')
    op.drop_table('interviews')
